import os
import cv2
import argparse
import torch
import numpy as np
import pandas as pd
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib
from modules import Preprocess, Detection, OCR, Retrieval, Correction
from tool.config import Config 
from tool.utils import natural_keys, visualize, find_highest_score_each_class
import time

"""
Vietnamese OCR Toolbox - Text Extraction with Coordinate Support

Sử dụng:
    python run.py --input path/to/image.jpg --save_coordinates

Các tùy chọn:
    --input: Đường dẫn đến file ảnh cần xử lý
    --output: Thư mục lưu kết quả (mặc định: ./results)
    --save_coordinates: Lưu văn bản kèm tọa độ bounding box
    --do_retrieve: Thực hiện trích xuất thông tin cấu trúc
    --find_best_rotation: Tìm góc xoay tối ưu cho tài liệu
    --debug: Lưu các bước trung gian để debug

Ví dụ:
    # Trích xuất văn bản cơ bản
    python run.py --input document.jpg
    
    # Trích xuất văn bản kèm tọa độ
    python run.py --input document.jpg --save_coordinates
    
    # Trích xuất với đầy đủ tính năng
    python run.py --input document.jpg --save_coordinates --do_retrieve --find_best_rotation

Kết quả:
    - result.jpg: Ảnh với bounding box và văn bản
    - extracted_text_with_coordinates.txt: Văn bản kèm tọa độ (nếu có --save_coordinates)
    - extracted_text_with_coordinates.json: Định dạng JSON (nếu có --save_coordinates)
    - result.txt: Kết quả trích xuất thông tin (nếu có --do_retrieve)
"""

parser = argparse.ArgumentParser("Document Extraction")
parser.add_argument("--input", help="Path to single image to be scanned")
parser.add_argument("--output", default="./results", help="Path to output folder")
parser.add_argument("--debug", action="store_true", help="Save every steps for debugging")
parser.add_argument("--do_retrieve", action="store_true", help="Whether to retrive information")
parser.add_argument("--find_best_rotation", action="store_true", help="Whether to find rotation of document in the image")
parser.add_argument("--save_coordinates", action="store_true", help="Whether to save extracted text with bounding box coordinates")
args = parser.parse_args()


class Pipeline:
    def __init__(self, args, config):
        self.output = args.output
        self.debug = args.debug
        self.do_retrieve = args.do_retrieve
        self.find_best_rotation = args.find_best_rotation
        self.save_coordinates = args.save_coordinates
        self.load_config(config)
        self.make_cache_folder()
        self.init_modules()
        

    def load_config(self, config):
        self.det_weight = config.det_weight
        self.ocr_weight = config.ocr_weight
        self.det_config = config.det_config
        self.ocr_config = config.ocr_config
        self.bert_weight = config.bert_weight
        self.class_mapping = {k:v for v,k in enumerate(config.retr_classes)}
        self.idx_mapping = {v:k for k,v in self.class_mapping.items()}
        self.dictionary_path = config.dictionary_csv
        self.retr_mode = config.retr_mode
        self.correction_mode = config.correction_mode

    def make_cache_folder(self):
        self.cache_folder = os.path.join(args.output, 'cache')
        os.makedirs(self.cache_folder,exist_ok=True)
        self.preprocess_cache = os.path.join(self.cache_folder, "preprocessed.jpg")
        self.detection_cache = os.path.join(self.cache_folder, "detected.jpg")
        self.crop_cache = os.path.join(self.cache_folder, 'crops')
        self.final_output = os.path.join(self.output, 'result.jpg')
        self.retr_output = os.path.join(self.output, 'result.txt')
        self.text_with_coords_output = os.path.join(self.output, 'extracted_text_with_coordinates.txt')

    def init_modules(self):
        self.det_model = Detection(
            config_path=self.det_config,
            weight_path=self.det_weight)
        self.ocr_model = OCR(
            config_path=self.ocr_config,
            weight_path=self.ocr_weight)
        self.preproc = Preprocess(
            det_model=self.det_model,
            ocr_model=self.ocr_model,
            find_best_rotation=self.find_best_rotation)
  
        if self.dictionary_path is not None:
            self.dictionary = {}
            df = pd.read_csv(self.dictionary_path)
            for id, row in df.iterrows():
                self.dictionary[row.text.lower()] = row.lbl
        else:
            self.dictionary=None

        self.correction = Correction(
            dictionary=self.dictionary,
            mode=self.correction_mode)

        if self.do_retrieve:
            self.retrieval = Retrieval(
                self.class_mapping,
                dictionary=self.dictionary,
                mode = self.retr_mode,
                bert_weight=self.bert_weight)

    def start(self, img):
        # Document extraction
        img1 = self.preproc(img)

        if self.debug:
            saved_img = cv2.cvtColor(img1, cv2.COLOR_RGB2BGR)
            cv2.imwrite(self.preprocess_cache, saved_img)

            boxes, img2  = self.det_model(
                img1,
                crop_region=True,
                return_result=True,
                output_path=self.cache_folder)
            saved_img = cv2.cvtColor(img2, cv2.COLOR_RGB2BGR)
            cv2.imwrite(self.detection_cache, saved_img)
        else:
            boxes = self.det_model(
                img1,
                crop_region=True,
                return_result=False,
                output_path=self.cache_folder)

        img_paths=os.listdir(self.crop_cache)
        img_paths.sort(key=natural_keys)
        img_paths = [os.path.join(self.crop_cache, i) for i in img_paths]
        
        texts = self.ocr_model.predict_folder(img_paths, return_probs=False)
        texts = self.correction(texts, return_score=False)
        
        if self.do_retrieve:
            preds, probs = self.retrieval(texts)
        else:
            preds, probs = None, None

        visualize(
          img1, boxes, texts, 
          img_name = self.final_output, 
          class_mapping = self.class_mapping,
          labels = preds, probs = probs, 
          visualize_best=self.do_retrieve)

        if self.do_retrieve:
            best_score_idx = find_highest_score_each_class(preds, probs, self.class_mapping)
            with open(self.retr_output, 'w') as f:
                for cls, idx in enumerate(best_score_idx):
                    f.write(f"{self.idx_mapping[cls]} : {texts[idx]}\n")
        
        # Xuất văn bản kèm tọa độ bounding box (nếu được yêu cầu)
        if self.save_coordinates:
            self.save_text_with_coordinates(boxes, texts)
        
        # Trả về văn bản đã trích xuất
        return texts

    def save_text_with_coordinates(self, boxes, texts):
        """
        Lưu văn bản kèm với tọa độ bounding box vào file text
        
        Args:
            boxes: List các bounding box với format [(x1,y1),(x2,y2),(x3,y3),(x4,y4)]
            texts: List các văn bản tương ứng
        """
        with open(self.text_with_coords_output, 'w', encoding='utf-8') as f:
            f.write("=== TRÍCH XUẤT VĂN BẢN VỚI TỌA ĐỘ BOUNDING BOX ===\n")
            f.write("Format: [Thứ tự] [Tọa độ 4 điểm] | Văn bản\n")
            f.write("Tọa độ: (x1,y1) (x2,y2) (x3,y3) (x4,y4)\n")
            f.write("Thứ tự đọc: từ trên xuống dưới, trái sang phải\n")
            f.write("=" * 70 + "\n\n")
            
            for i, (box, text) in enumerate(zip(boxes, texts)):
                # Lấy 4 điểm của bounding box
                (x1, y1), (x2, y2), (x3, y3), (x4, y4) = box
                
                # Tính toán trung tâm và kích thước để dễ hiểu
                center_x = int((x1 + x2 + x3 + x4) / 4)
                center_y = int((y1 + y2 + y3 + y4) / 4)
                
                # Format tọa độ
                coords_str = f"({int(x1)},{int(y1)}) ({int(x2)},{int(y2)}) ({int(x3)},{int(y3)}) ({int(x4)},{int(y4)})"
                
                # Ghi vào file với thông tin chi tiết
                f.write(f"[{i+1:03d}] {coords_str}\n")
                f.write(f"      Trung tâm: ({center_x}, {center_y})\n")
                f.write(f"      Văn bản: {text}\n")
                f.write("-" * 50 + "\n")
            
            f.write(f"\n=== TỔNG CỘNG: {len(texts)} văn bản được trích xuất ===\n")
            
            # Thêm section với format CSV cho dễ xử lý
            f.write(f"\n=== ĐỊNH DẠNG CSV (cho việc xử lý tự động) ===\n")
            f.write("STT,X1,Y1,X2,Y2,X3,Y3,X4,Y4,CENTER_X,CENTER_Y,TEXT\n")
            
            for i, (box, text) in enumerate(zip(boxes, texts)):
                (x1, y1), (x2, y2), (x3, y3), (x4, y4) = box
                center_x = int((x1 + x2 + x3 + x4) / 4)
                center_y = int((y1 + y2 + y3 + y4) / 4)
                # Escape commas trong text để tương thích CSV
                csv_text = text.replace(',', ';').replace('\n', ' ').replace('\r', ' ')
                f.write(f"{i+1},{int(x1)},{int(y1)},{int(x2)},{int(y2)},{int(x3)},{int(y3)},{int(x4)},{int(y4)},{center_x},{center_y},\"{csv_text}\"\n")
        
        print(f"Đã lưu kết quả với tọa độ vào: {self.text_with_coords_output}")
        
        # Tạo thêm file JSON cho các ứng dụng hiện đại
        json_output = self.text_with_coords_output.replace('.txt', '.json')
        self.save_text_with_coordinates_json(boxes, texts, json_output)
    
    def save_text_with_coordinates_json(self, boxes, texts, output_path):
        """
        Lưu kết quả dưới dạng JSON để dễ xử lý bằng các ngôn ngữ lập trình khác
        """
        import json
        
        results = {
            "metadata": {
                "total_texts": len(texts),
                "format": "bounding_box_coordinates",
                "coordinate_format": "[(x1,y1), (x2,y2), (x3,y3), (x4,y4)]",
                "description": "Extracted text with bounding box coordinates"
            },
            "extracted_texts": []
        }
        
        for i, (box, text) in enumerate(zip(boxes, texts)):
            (x1, y1), (x2, y2), (x3, y3), (x4, y4) = box
            
            text_data = {
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
                        "x": int((x1 + x2 + x3 + x4) / 4),
                        "y": int((y1 + y2 + y3 + y4) / 4)
                    }
                }
            }
            results["extracted_texts"].append(text_data)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"Đã lưu kết quả JSON vào: {output_path}")


if __name__ == '__main__':
    config = Config('./tool/config/configs.yaml')
    pipeline = Pipeline(args, config)
    img = cv2.imread(args.input)
    start_time = time.time()
    texts = pipeline.start(img)
    end_time = time.time()

    print(f"Executed in {end_time - start_time} s")
    
    # Hiển thị văn bản đã trích xuất
    print("\n=== EXTRACTED TEXTS ===")
    for text in texts:
        print(text)

    # Thông báo về các file kết quả đã được tạo
    print(f"\n=== FILES CREATED ===")
    print(f"- Visualization image: {pipeline.final_output}")
    
    if args.do_retrieve:
        print(f"- Retrieval results: {pipeline.retr_output}")
    
    if args.save_coordinates:
        print(f"- Text with coordinates: {pipeline.text_with_coords_output}")
        print(f"- JSON format: {pipeline.text_with_coords_output.replace('.txt', '.json')}")
        print("\nFile với tọa độ bao gồm:")
        print("  + Định dạng dễ đọc cho con người")
        print("  + Định dạng CSV cho xử lý tự động")  
        print("  + Định dạng JSON cho các ứng dụng hiện đại")
    else:
        print("\nGợi ý: Sử dụng --save_coordinates để lưu văn bản kèm tọa độ bounding box")

