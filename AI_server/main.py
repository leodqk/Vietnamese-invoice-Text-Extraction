from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import cv2
import numpy as np
from PIL import Image
import io
import os
import uuid
import json
import time
from typing import Optional, Dict, Any
import torch

# Import modules từ 2 method
from normal_method_handler import NormalMethodHandler
from advance_method_handler import AdvanceMethodHandler

app = FastAPI(
    title="Vietnamese OCR Toolbox API",
    description="API cho trích xuất văn bản tiếng Việt từ hình ảnh",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tạo thư mục lưu trữ tạm thời
UPLOAD_DIR = "temp_uploads"
RESULTS_DIR = "temp_results"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

# Dictionary lưu trữ tạm thời các file đã upload
uploaded_files = {}

# Khởi tạo handlers
normal_handler = None
advance_handler = None

@app.on_event("startup")
async def startup_event():
    """Khởi tạo các models khi server start"""
    global normal_handler, advance_handler
    
    print("Initializing OCR handlers...")
    
    # Khởi tạo normal method handler
    try:
        normal_handler = NormalMethodHandler()
        print("✓ Normal method handler initialized")
    except Exception as e:
        print(f"✗ Failed to initialize normal method handler: {e}")
        normal_handler = None
    
    # Khởi tạo advance method handler
    try:
        advance_handler = AdvanceMethodHandler()
        print("✓ Advance method handler initialized")
    except Exception as e:
        print(f"✗ Failed to initialize advance method handler: {e}")
        advance_handler = None

@app.get("/")
async def root():
    """API info endpoint"""
    return {
        "message": "Vietnamese OCR Toolbox API",
        "version": "1.0.0",
        "endpoints": {
            "upload_image": "/upload-image",
            "extract_text": "/extract-text"
        }
    }

@app.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    """
    API 1: Upload image và trả về file_id để sử dụng cho việc trích xuất văn bản
    
    Args:
        file: File ảnh upload (jpg, jpeg, png)
    
    Returns:
        file_id: ID để sử dụng cho API extract-text
    """
    
    # Kiểm tra định dạng file
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File phải là hình ảnh")
    
    allowed_extensions = ['jpg', 'jpeg', 'png', 'bmp', 'tiff']
    file_extension = file.filename.split('.')[-1].lower()
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Định dạng file không được hỗ trợ. Các định dạng được hỗ trợ: {', '.join(allowed_extensions)}"
        )
    
    try:
        # Đọc file content
        file_content = await file.read()
        
        # Tạo unique file ID
        file_id = str(uuid.uuid4())
        
        # Lưu file tạm thời
        file_path = os.path.join(UPLOAD_DIR, f"{file_id}.{file_extension}")
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # Lưu thông tin file
        uploaded_files[file_id] = {
            "original_filename": file.filename,
            "file_path": file_path,
            "file_extension": file_extension,
            "upload_time": time.time(),
            "file_size": len(file_content)
        }
        
        # Kiểm tra xem có thể đọc được ảnh không
        try:
            image = cv2.imread(file_path)
            if image is None:
                raise Exception("Không thể đọc file ảnh")
            height, width = image.shape[:2]
        except Exception as e:
            # Cleanup file if invalid
            if os.path.exists(file_path):
                os.remove(file_path)
            del uploaded_files[file_id]
            raise HTTPException(status_code=400, detail=f"File ảnh không hợp lệ: {str(e)}")
        
        return {
            "status": "success",
            "message": "Upload ảnh thành công",
            "file_id": file_id,
            "original_filename": file.filename,
            "file_size": len(file_content),
            "image_dimensions": {
                "width": width,
                "height": height
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi upload file: {str(e)}")

@app.post("/extract-text")
async def extract_text(
    file_id: str = Form(...),
    method: str = Form(...),
    save_coordinates: Optional[bool] = Form(False),
    do_retrieve: Optional[bool] = Form(False),
    find_best_rotation: Optional[bool] = Form(False),
    custom_prompt: Optional[str] = Form(None)
):
    """
    API 2: Trích xuất văn bản từ ảnh đã upload
    
    Args:
        file_id: ID của file ảnh đã upload
        method: Phương pháp trích xuất ("normal" hoặc "advance")
        save_coordinates: Có lưu tọa độ bounding box không (chỉ cho normal method)
        do_retrieve: Có thực hiện trích xuất thông tin cấu trúc không (chỉ cho normal method)
        find_best_rotation: Có tìm góc xoay tối ưu không (chỉ cho normal method)
        custom_prompt: Prompt tùy chỉnh cho advance method (optional)
    
    Returns:
        Kết quả trích xuất văn bản
    """
    
    # Kiểm tra file_id có tồn tại không
    if file_id not in uploaded_files:
        raise HTTPException(status_code=404, detail="File ID không tồn tại hoặc đã hết hạn")
    
    # Kiểm tra method
    if method not in ["normal", "advance"]:
        raise HTTPException(status_code=400, detail="Method phải là 'normal' hoặc 'advance'")
    
    file_info = uploaded_files[file_id]
    file_path = file_info["file_path"]
    
    # Kiểm tra file vẫn tồn tại
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File ảnh không tồn tại")
    
    try:
        start_time = time.time()
        
        if method == "normal":
            if normal_handler is None:
                raise HTTPException(status_code=503, detail="Normal method handler chưa được khởi tạo")
            
            result = await extract_text_normal(
                file_path, file_id, save_coordinates, do_retrieve, find_best_rotation
            )
        
        elif method == "advance":
            if advance_handler is None:
                raise HTTPException(status_code=503, detail="Advance method handler chưa được khởi tạo")
            
            result = await extract_text_advance(file_path, file_id, custom_prompt)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        result["processing_info"] = {
            "method": method,
            "processing_time": round(processing_time, 2),
            "file_info": {
                "original_filename": file_info["original_filename"],
                "file_size": file_info["file_size"]
            }
        }
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi trích xuất văn bản: {str(e)}")

async def extract_text_normal(file_path: str, file_id: str, save_coordinates: bool, do_retrieve: bool, find_best_rotation: bool):
    """Trích xuất văn bản bằng normal method"""
    
    try:
        # Đọc ảnh
        img = cv2.imread(file_path)
        if img is None:
            raise Exception("Không thể đọc file ảnh")
        
        # Tạo thư mục output riêng cho file này
        output_dir = os.path.join(RESULTS_DIR, file_id)
        os.makedirs(output_dir, exist_ok=True)
        
        # Chạy normal method
        result = normal_handler.process(
            img, output_dir, save_coordinates, do_retrieve, find_best_rotation
        )
        
        return {
            "status": "success",
            "method": "normal",
            "extracted_texts": result["texts"],
            "coordinates": result.get("coordinates", []),
            "retrieval_results": result.get("retrieval_results", {}),
            "output_files": result.get("output_files", {})
        }
        
    except Exception as e:
        raise Exception(f"Normal method error: {str(e)}")

async def extract_text_advance(file_path: str, file_id: str, custom_prompt: str = None):
    """Trích xuất văn bản bằng advance method"""
    
    try:
        # Chạy advance method
        if custom_prompt:
            result = advance_handler.process_with_custom_prompt(file_path, custom_prompt)
        else:
            result = advance_handler.process(file_path)
        
        return {
            "status": "success",
            "method": "advance",
            "extracted_text": result["text"],
            "confidence": result.get("confidence", None),
            "custom_prompt": result.get("prompt", None)
        }
        
    except Exception as e:
        raise Exception(f"Advance method error: {str(e)}")

@app.delete("/cleanup/{file_id}")
async def cleanup_file(file_id: str):
    """
    Dọn dẹp file tạm thời sau khi sử dụng xong
    """
    if file_id not in uploaded_files:
        raise HTTPException(status_code=404, detail="File ID không tồn tại")
    
    try:
        file_info = uploaded_files[file_id]
        
        # Xóa file gốc
        if os.path.exists(file_info["file_path"]):
            os.remove(file_info["file_path"])
        
        # Xóa thư mục kết quả
        result_dir = os.path.join(RESULTS_DIR, file_id)
        if os.path.exists(result_dir):
            import shutil
            shutil.rmtree(result_dir)
        
        # Xóa khỏi dictionary
        del uploaded_files[file_id]
        
        return {"status": "success", "message": "Đã dọn dẹp file thành công"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi dọn dẹp file: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "handlers": {
            "normal_method": normal_handler is not None,
            "advance_method": advance_handler is not None
        },
        "gpu_available": torch.cuda.is_available(),
        "uploaded_files_count": len(uploaded_files)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
