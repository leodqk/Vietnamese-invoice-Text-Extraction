import os
import cv2
import torch
import numpy as np
import pandas as pd
from PIL import Image
import json
from modules import Preprocess, Detection, OCR, Retrieval, Correction
from tool.config import Config 
from tool.utils import natural_keys, visualize, find_highest_score_each_class

class NormalMethodHandler:
    """Mock handler cho normal method OCR"""
    
    def __init__(self):
        """Khởi tạo normal method handler"""
        print("Normal method handler initialized")
    
    def process(self, img, output_dir, save_coordinates=False, do_retrieve=False, find_best_rotation=False):
        """
        Xử lý OCR với normal method
        
        Args:
            img: OpenCV image
            output_dir: Thư mục output
            save_coordinates: Có lưu tọa độ không
            do_retrieve: Có trích xuất thông tin cấu trúc không
            find_best_rotation: Có tìm góc xoay tối ưu không
            
        Returns:
            dict: Kết quả OCR
        """
        
        # Mock extracted texts
        texts = [
            "CÔNG TY TNHH ABC",
            "Địa chỉ: 123 Đường XYZ, Quận 1, TP.HCM",
            "Tel: (028) 1234 5678",
            "HÓA ĐƠN BÁN HÀNG",
            "Số: 001/2024",
            "Ngày: 15/01/2024",
            "Khách hàng: Nguyễn Văn A",
            "Sản phẩm A: 100,000 VND",
            "Sản phẩm B: 200,000 VND",
            "Tổng cộng: 300,000 VND"
        ]
        
        # Mock coordinates
        coordinates = []
        if save_coordinates:
            coordinates = [
                {"text": "CÔNG TY TNHH ABC", "bbox": [10, 20, 200, 40]},
                {"text": "HÓA ĐƠN BÁN HÀNG", "bbox": [50, 100, 250, 120]},
                {"text": "300,000 VND", "bbox": [150, 300, 250, 320]}
            ]
        
        # Mock retrieval results
        retrieval_results = {}
        if do_retrieve:
            retrieval_results = {
                "company_name": "CÔNG TY TNHH ABC",
                "invoice_number": "001/2024",
                "date": "15/01/2024",
                "customer": "Nguyễn Văn A",
                "total_amount": "300,000 VND",
                "items": [
                    {"name": "Sản phẩm A", "price": "100,000 VND"},
                    {"name": "Sản phẩm B", "price": "200,000 VND"}
                ]
            }
        
        # Mock output files
        output_files = {
            "original": f"{output_dir}/original.jpg",
            "processed": f"{output_dir}/processed.jpg"
        }
        
        return {
            "texts": texts,
            "coordinates": coordinates,
            "retrieval_results": retrieval_results,
            "output_files": output_files
        }

    def load_config(self):
        """Load config từ file cấu hình"""
        self.det_weight = self.config.det_weight
        self.ocr_weight = self.config.ocr_weight
        self.det_config = self.config.det_config
        self.ocr_config = self.config.ocr_config
        self.bert_weight = self.config.bert_weight
        self.class_mapping = {k:v for v,k in enumerate(self.config.retr_classes)}
        self.idx_mapping = {v:k for k,v in self.class_mapping.items()}
        self.dictionary_path = self.config.dictionary_csv
        self.retr_mode = self.config.retr_mode
        self.correction_mode = self.config.correction_mode

    def init_modules(self):
        """Khởi tạo các modules OCR"""
        # Detection model
        self.det_model = Detection(
            config_path=self.det_config,
            weight_path=self.det_weight)
        
        # OCR model  
        self.ocr_model = OCR(
            config_path=self.ocr_config,
            weight_path=self.ocr_weight)
        
        # Preprocessing module
        self.preproc = Preprocess(
            det_model=self.det_model,
            ocr_model=self.ocr_model,
            find_best_rotation=False)  # Sẽ được set lại khi process
        
        # Dictionary cho correction
        if self.dictionary_path is not None:
            self.dictionary = {}
            df = pd.read_csv(self.dictionary_path)
            for id, row in df.iterrows():
                self.dictionary[row.text.lower()] = row.lbl
        else:
            self.dictionary = None

        # Correction module
        self.correction = Correction(
            dictionary=self.dictionary,
            mode=self.correction_mode)

        # Retrieval module (chỉ khởi tạo khi cần)
        self.retrieval = None

    def init_retrieval(self):
        """Khởi tạo retrieval module khi cần thiết"""
        if self.retrieval is None:
            self.retrieval = Retrieval(
                self.class_mapping,
                dictionary=self.dictionary,
                mode=self.retr_mode,
                bert_weight=self.bert_weight)

    def save_text_with_coordinates(self, boxes, texts, output_dir):
        """
        Lưu văn bản kèm với tọa độ bounding box
        
        Args:
            boxes: List các bounding box
            texts: List các văn bản tương ứng
            output_dir: Thư mục lưu file
            
        Returns:
            List coordinates data
        """
        
        coordinates_data = []
        
        # Lưu file text
        text_output = os.path.join(output_dir, 'extracted_text_with_coordinates.txt')
        with open(text_output, 'w', encoding='utf-8') as f:
            f.write("=== TRÍCH XUẤT VĂN BẢN VỚI TỌA ĐỘ BOUNDING BOX ===\n")
            f.write("Format: [Thứ tự] [Tọa độ 4 điểm] | Văn bản\n")
            f.write("Tọa độ: (x1,y1) (x2,y2) (x3,y3) (x4,y4)\n")
            f.write("Thứ tự đọc: từ trên xuống dưới, trái sang phải\n")
            f.write("=" * 70 + "\n\n")
            
            for i, (box, text) in enumerate(zip(boxes, texts)):
                # Lấy 4 điểm của bounding box
                (x1, y1), (x2, y2), (x3, y3), (x4, y4) = box
                
                # Tính toán trung tâm
                center_x = int((x1 + x2 + x3 + x4) / 4)
                center_y = int((y1 + y2 + y3 + y4) / 4)
                
                # Lưu vào coordinates_data
                coord_item = {
                    "id": i + 1,
                    "text": text,
                    "bounding_box": {
                        "coordinates": [
                            {"x": int(x1), "y": int(y1)},
                            {"x": int(x2), "y": int(y2)},
                            {"x": int(x3), "y": int(y3)},
                            {"x": int(x4), "y": int(y4)}
                        ],
                        "center": {
                            "x": center_x,
                            "y": center_y
                        }
                    }
                }
                coordinates_data.append(coord_item)
                
                # Format tọa độ cho file text
                coords_str = f"({int(x1)},{int(y1)}) ({int(x2)},{int(y2)}) ({int(x3)},{int(y3)}) ({int(x4)},{int(y4)})"
                
                # Ghi vào file
                f.write(f"[{i+1:03d}] {coords_str}\n")
                f.write(f"      Trung tâm: ({center_x}, {center_y})\n")
                f.write(f"      Văn bản: {text}\n")
                f.write("-" * 50 + "\n")
            
            f.write(f"\n=== TỔNG CỘNG: {len(texts)} văn bản được trích xuất ===\n")
        
        # Lưu file JSON
        json_output = os.path.join(output_dir, 'extracted_text_with_coordinates.json')
        json_data = {
            "metadata": {
                "total_texts": len(texts),
                "format": "bounding_box_coordinates",
                "coordinate_format": "[(x1,y1), (x2,y2), (x3,y3), (x4,y4)]",
                "description": "Extracted text with bounding box coordinates"
            },
            "extracted_texts": coordinates_data
        }
        
        with open(json_output, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        return coordinates_data 