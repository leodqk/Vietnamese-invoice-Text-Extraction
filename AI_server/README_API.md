# Vietnamese OCR Toolbox API

FastAPI server cho trích xuất văn bản tiếng Việt từ hình ảnh với 2 phương pháp:

- **Normal Method**: Sử dụng pipeline truyền thống (Detection + OCR + Correction)
- **Advance Method**: Sử dụng model AI tiên tiến (Vintern-1B-v3_5)

## Cài đặt

1. Cài đặt dependencies:

```bash
pip install -r requirements.txt
```

2. Đảm bảo các module và config files cần thiết đã có sẵn:

- `modules/` (Detection, OCR, Retrieval, Correction)
- `tool/config/configs.yaml`
- Model weights tương ứng

## Chạy server

```bash
python main.py
```

Server sẽ chạy tại: `http://localhost:8000`

## API Documentation

### 1. Upload Image API

**Endpoint:** `POST /upload-image`

**Description:** Upload ảnh và nhận file_id để sử dụng cho việc trích xuất văn bản

**Request:**

- Form data với file ảnh (jpg, jpeg, png, bmp, tiff)

**Response:**

```json
{
  "status": "success",
  "message": "Upload ảnh thành công",
  "file_id": "uuid-string",
  "original_filename": "example.jpg",
  "file_size": 12345,
  "image_dimensions": {
    "width": 1920,
    "height": 1080
  }
}
```

**curl Example:**

```bash
curl -X POST "http://localhost:8000/upload-image" \
     -F "file=@path/to/your/image.jpg"
```

### 2. Extract Text API

**Endpoint:** `POST /extract-text`

**Description:** Trích xuất văn bản từ ảnh đã upload

**Request Parameters:**

- `file_id` (required): ID của file ảnh đã upload
- `method` (required): Phương pháp trích xuất ("normal" hoặc "advance")
- `save_coordinates` (optional): Lưu tọa độ bounding box (chỉ cho normal method)
- `do_retrieve` (optional): Thực hiện trích xuất thông tin cấu trúc (chỉ cho normal method)
- `find_best_rotation` (optional): Tìm góc xoay tối ưu (chỉ cho normal method)
- `custom_prompt` (optional): Prompt tùy chỉnh cho advance method

**Response for Normal Method:**

```json
{
  "status": "success",
  "method": "normal",
  "extracted_texts": ["text1", "text2", "..."],
  "coordinates": [
    {
      "id": 1,
      "text": "sample text",
      "bounding_box": {
        "coordinates": [
          { "x": 100, "y": 50 },
          { "x": 200, "y": 50 },
          { "x": 200, "y": 80 },
          { "x": 100, "y": 80 }
        ],
        "center": { "x": 150, "y": 65 }
      }
    }
  ],
  "retrieval_results": {
    "name": "extracted_name",
    "address": "extracted_address"
  },
  "output_files": {
    "visualization": "path/to/result.jpg",
    "coordinates_txt": "path/to/coordinates.txt",
    "coordinates_json": "path/to/coordinates.json"
  },
  "processing_info": {
    "method": "normal",
    "processing_time": 2.35,
    "file_info": {
      "original_filename": "example.jpg",
      "file_size": 12345
    }
  }
}
```

**Response for Advance Method:**

```json
{
  "status": "success",
  "method": "advance",
  "extracted_text": "# Document Title\n\nExtracted content in markdown format...",
  "confidence": null,
  "processing_info": {
    "method": "advance",
    "processing_time": 5.67,
    "file_info": {
      "original_filename": "example.jpg",
      "file_size": 12345
    }
  }
}
```

**curl Examples:**

Normal method với tất cả tùy chọn:

```bash
curl -X POST "http://localhost:8000/extract-text" \
     -F "file_id=your-file-id" \
     -F "method=normal" \
     -F "save_coordinates=true" \
     -F "do_retrieve=true" \
     -F "find_best_rotation=true"
```

Advance method:

```bash
curl -X POST "http://localhost:8000/extract-text" \
     -F "file_id=your-file-id" \
     -F "method=advance"
```

Advance method với custom prompt:

```bash
curl -X POST "http://localhost:8000/extract-text" \
     -F "file_id=your-file-id" \
     -F "method=advance" \
     -F "custom_prompt=Trích xuất thông tin quan trọng và định dạng thành bảng"
```

### 3. Cleanup API

**Endpoint:** `DELETE /cleanup/{file_id}`

**Description:** Dọn dẹp files tạm thời sau khi sử dụng xong

**curl Example:**

```bash
curl -X DELETE "http://localhost:8000/cleanup/your-file-id"
```

### 4. Health Check API

**Endpoint:** `GET /health`

**Description:** Kiểm tra trạng thái server và các handlers

**Response:**

```json
{
  "status": "healthy",
  "handlers": {
    "normal_method": true,
    "advance_method": true
  },
  "gpu_available": true,
  "uploaded_files_count": 5
}
```

## Sử dụng hoàn chỉnh

### Example với Python requests:

```python
import requests
import json

# 1. Upload image
with open('your_image.jpg', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/upload-image',
        files={'file': f}
    )
    result = response.json()
    file_id = result['file_id']

# 2. Extract text với normal method
response = requests.post(
    'http://localhost:8000/extract-text',
    data={
        'file_id': file_id,
        'method': 'normal',
        'save_coordinates': True,
        'do_retrieve': True
    }
)
normal_result = response.json()

# 3. Extract text với advance method
response = requests.post(
    'http://localhost:8000/extract-text',
    data={
        'file_id': file_id,
        'method': 'advance'
    }
)
advance_result = response.json()

# 4. Cleanup
requests.delete(f'http://localhost:8000/cleanup/{file_id}')

print("Normal method:", normal_result['extracted_texts'])
print("Advance method:", advance_result['extracted_text'])
```

### Example với JavaScript/Node.js:

```javascript
const FormData = require("form-data");
const fs = require("fs");
const axios = require("axios");

async function processImage() {
  // 1. Upload image
  const form = new FormData();
  form.append("file", fs.createReadStream("your_image.jpg"));

  const uploadResponse = await axios.post(
    "http://localhost:8000/upload-image",
    form,
    { headers: form.getHeaders() }
  );

  const fileId = uploadResponse.data.file_id;

  // 2. Extract text
  const extractForm = new FormData();
  extractForm.append("file_id", fileId);
  extractForm.append("method", "normal");
  extractForm.append("save_coordinates", "true");

  const extractResponse = await axios.post(
    "http://localhost:8000/extract-text",
    extractForm,
    { headers: extractForm.getHeaders() }
  );

  console.log("Extracted texts:", extractResponse.data.extracted_texts);

  // 3. Cleanup
  await axios.delete(`http://localhost:8000/cleanup/${fileId}`);
}

processImage().catch(console.error);
```

## Interactive API Documentation

Sau khi chạy server, bạn có thể truy cập:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Lưu ý

1. **GPU Support**: Server sẽ tự động sử dụng GPU nếu có sẵn
2. **File Management**: Files upload sẽ được lưu tạm thời và nên được cleanup sau khi sử dụng
3. **Model Loading**: Advance method cần download model Vintern-1B-v3_5 lần đầu chạy
4. **Error Handling**: API có xử lý lỗi chi tiết với HTTP status codes phù hợp

## Troubleshooting

- **Model loading errors**: Đảm bảo có kết nối internet để download models
- **GPU errors**: Kiểm tra CUDA installation nếu muốn sử dụng GPU
- **Config errors**: Đảm bảo file `tool/config/configs.yaml` và model weights có sẵn
- **Import errors**: Đảm bảo các module trong thư mục `modules/` có sẵn và đúng cấu trúc
