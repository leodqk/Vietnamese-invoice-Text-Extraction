import numpy as np
import torch
import torchvision.transforms as T
from PIL import Image
from torchvision.transforms.functional import InterpolationMode
from transformers import AutoModel, AutoTokenizer

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)

class AdvanceMethodHandler:
    """Mock handler cho advance method OCR"""
    
    def __init__(self):
        """Khởi tạo advance method handler"""
        print("Advance method handler initialized")
    
    def process(self, image_path):
        """
        Xử lý OCR với advance method
        
        Args:
            image_path: Đường dẫn đến file ảnh
            
        Returns:
            dict: Kết quả OCR
        """
        
        # Mock extracted text
        text = """CÔNG TY TNHH ABC COMPANY
Địa chỉ: 123 Đường Nguyễn Huệ, Quận 1, TP.HCM
Điện thoại: (028) 1234 5678
Email: contact@abc.com

HÓA ĐƠN BÁN HÀNG
Số hóa đơn: HĐ-001/2024
Ngày: 15/01/2024
Khách hàng: Nguyễn Văn A
Địa chỉ: 456 Đường Lê Lợi, Quận 3, TP.HCM

Chi tiết:
1. Sản phẩm A - SL: 2 - Đơn giá: 100,000 VND - Thành tiền: 200,000 VND
2. Sản phẩm B - SL: 1 - Đơn giá: 150,000 VND - Thành tiền: 150,000 VND

Tổng tiền hàng: 350,000 VND
VAT (10%): 35,000 VND
Tổng thanh toán: 385,000 VND

Cảm ơn quý khách!"""
        
        return {
            "text": text,
            "confidence": 0.95
        }
    
    def process_with_custom_prompt(self, image_path, custom_prompt):
        """
        Xử lý OCR với advance method và custom prompt
        
        Args:
            image_path: Đường dẫn đến file ảnh
            custom_prompt: Prompt tùy chỉnh
            
        Returns:
            dict: Kết quả OCR
        """
        
        # Mock response dựa trên custom prompt
        if "invoice" in custom_prompt.lower() or "hóa đơn" in custom_prompt.lower():
            text = """Thông tin hóa đơn được trích xuất:
- Số hóa đơn: HĐ-001/2024
- Ngày phát hành: 15/01/2024
- Tên khách hàng: Nguyễn Văn A
- Tổng tiền: 385,000 VND
- Công ty: CÔNG TY TNHH ABC"""
        elif "product" in custom_prompt.lower() or "sản phẩm" in custom_prompt.lower():
            text = """Danh sách sản phẩm:
1. Sản phẩm A - 200,000 VND
2. Sản phẩm B - 150,000 VND"""
        else:
            text = self.process(image_path)["text"]
        
        return {
            "text": text,
            "confidence": 0.92,
            "prompt": custom_prompt
        }

    def build_transform(self, input_size):
        """Tạo transform cho ảnh"""
        MEAN, STD = IMAGENET_MEAN, IMAGENET_STD
        transform = T.Compose([
            T.Lambda(lambda img: img.convert('RGB') if img.mode != 'RGB' else img),
            T.Resize((input_size, input_size), interpolation=InterpolationMode.BICUBIC),
            T.ToTensor(),
            T.Normalize(mean=MEAN, std=STD)
        ])
        return transform

    def find_closest_aspect_ratio(self, aspect_ratio, target_ratios, width, height, image_size):
        """Tìm tỷ lệ khung hình gần nhất"""
        best_ratio_diff = float('inf')
        best_ratio = (1, 1)
        area = width * height
        
        for ratio in target_ratios:
            target_aspect_ratio = ratio[0] / ratio[1]
            ratio_diff = abs(aspect_ratio - target_aspect_ratio)
            if ratio_diff < best_ratio_diff:
                best_ratio_diff = ratio_diff
                best_ratio = ratio
            elif ratio_diff == best_ratio_diff:
                if area > 0.5 * image_size * image_size * ratio[0] * ratio[1]:
                    best_ratio = ratio
        return best_ratio

    def dynamic_preprocess(self, image, min_num=1, max_num=12, image_size=448, use_thumbnail=False):
        """Tiền xử lý ảnh động"""
        orig_width, orig_height = image.size
        aspect_ratio = orig_width / orig_height

        # Tính tỷ lệ khung hình hiện tại
        target_ratios = set(
            (i, j) for n in range(min_num, max_num + 1) for i in range(1, n + 1) for j in range(1, n + 1) if
            i * j <= max_num and i * j >= min_num)
        target_ratios = sorted(target_ratios, key=lambda x: x[0] * x[1])

        # Tìm tỷ lệ khung hình gần nhất
        target_aspect_ratio = self.find_closest_aspect_ratio(
            aspect_ratio, target_ratios, orig_width, orig_height, image_size)

        # Tính kích thước đích
        target_width = image_size * target_aspect_ratio[0]
        target_height = image_size * target_aspect_ratio[1]
        blocks = target_aspect_ratio[0] * target_aspect_ratio[1]

        # Resize ảnh
        resized_img = image.resize((target_width, target_height))
        processed_images = []
        
        for i in range(blocks):
            box = (
                (i % (target_width // image_size)) * image_size,
                (i // (target_width // image_size)) * image_size,
                ((i % (target_width // image_size)) + 1) * image_size,
                ((i // (target_width // image_size)) + 1) * image_size
            )
            # Chia ảnh
            split_img = resized_img.crop(box)
            processed_images.append(split_img)
            
        assert len(processed_images) == blocks
        
        if use_thumbnail and len(processed_images) != 1:
            thumbnail_img = image.resize((image_size, image_size))
            processed_images.append(thumbnail_img)
            
        return processed_images

    def load_image(self, image_file, input_size=448, max_num=6):
        """Load và preprocess ảnh với giới hạn sequence length"""
        if isinstance(image_file, str):
            image = Image.open(image_file).convert('RGB')
        else:
            # Nếu là PIL Image
            image = image_file.convert('RGB')
            
        transform = self.build_transform(input_size=input_size)
        images = self.dynamic_preprocess(image, image_size=input_size, use_thumbnail=True, max_num=max_num)
        pixel_values = [transform(image) for image in images]
        pixel_values = torch.stack(pixel_values)
        return pixel_values 