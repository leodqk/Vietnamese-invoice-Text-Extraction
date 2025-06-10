# Vietnamese OCR Toolbox - Frontend

Giao diện web đơn giản để sử dụng các API của Vietnamese OCR Toolbox.

## Tính năng

### 1. Upload Ảnh

- Hỗ trợ drag & drop hoặc click để chọn file
- Các định dạng được hỗ trợ: JPG, JPEG, PNG, BMP, TIFF
- Giới hạn kích thước file: 10MB
- Preview ảnh sau khi upload
- Hiển thị thông tin file: tên, kích thước, kích thước ảnh, File ID

### 2. Phương Pháp Trích Xuất

#### Normal Method

- Phương pháp OCR truyền thống với khả năng tùy chỉnh cao
- **Tùy chọn:**
  - **Lưu tọa độ bounding box**: Lưu vị trí của từng văn bản được phát hiện
  - **Trích xuất thông tin cấu trúc**: Phân tích và trích xuất thông tin theo cấu trúc (như hóa đơn)
  - **Tìm góc xoay tối ưu**: Tự động xoay ảnh để có độ chính xác cao nhất

#### Advance Method

- Phương pháp AI tiên tiến với độ chính xác cao
- **Tùy chọn:**
  - **Custom Prompt**: Nhập prompt tùy chỉnh để hướng dẫn AI trích xuất thông tin cụ thể

### 3. Hiển thị Kết Quả

#### Tab Văn Bản

- Hiển thị toàn bộ văn bản được trích xuất
- Có nút Copy để sao chép nội dung

#### Tab Tọa Độ (chỉ với Normal Method + tùy chọn)

- Hiển thị dữ liệu JSON chứa tọa độ bounding box của từng văn bản
- Format: `[{id, text, bounding_box: {coordinates, center}}]`

#### Tab Thông Tin Cấu Trúc (chỉ với Normal Method + tùy chọn)

- Hiển thị thông tin đã được phân tích và trích xuất theo cấu trúc
- Ví dụ: thông tin hóa đơn, thông tin khách hàng, v.v.

### 4. Quản Lý File

- **Dọn dẹp file**: Xóa file tạm thời trên server sau khi sử dụng xong
- **Xử lý ảnh mới**: Reset form để xử lý ảnh mới

## Cách Sử dụng

### 1. Khởi động Server

Trước tiên, cần khởi động server API:

```bash
cd AI_server
python main.py
```

Server sẽ chạy tại `http://localhost:8000`

### 2. Mở Giao diện Web

Mở file `index.html` trong trình duyệt web hoặc chạy local server:

```bash
# Option 1: Mở trực tiếp file
# Mở index.html trong trình duyệt

# Option 2: Dùng Python HTTP server
cd frontend
python -m http.server 8080
# Truy cập: http://localhost:8080

# Option 3: Dùng Node.js
npx serve .
```

### 3. Quy trình Sử dụng

1. **Kiểm tra trạng thái server**: Giao diện sẽ tự động kiểm tra và hiển thị trạng thái server
2. **Upload ảnh**: Kéo thả hoặc click để chọn ảnh
3. **Chọn phương pháp**: Normal hoặc Advance
4. **Cấu hình tùy chọn**: Tùy theo phương pháp đã chọn
5. **Trích xuất văn bản**: Click nút "Trích Xuất Văn Bản"
6. **Xem kết quả**: Chuyển đổi giữa các tab để xem các loại kết quả khác nhau
7. **Dọn dẹp**: Click "Dọn Dẹp File" để xóa file tạm thời

## API Endpoints Sử Dụng

### GET /health

Kiểm tra trạng thái server và các handlers

### POST /upload-image

Upload ảnh và nhận file_id

**Body**: FormData với file ảnh

**Response**:

```json
{
  "status": "success",
  "file_id": "uuid",
  "original_filename": "image.jpg",
  "file_size": 123456,
  "image_dimensions": { "width": 800, "height": 600 }
}
```

### POST /extract-text

Trích xuất văn bản từ ảnh đã upload

**Body**: FormData với các tham số:

- `file_id`: ID của file đã upload
- `method`: "normal" hoặc "advance"
- `save_coordinates`: boolean (chỉ normal method)
- `do_retrieve`: boolean (chỉ normal method)
- `find_best_rotation`: boolean (chỉ normal method)
- `custom_prompt`: string (chỉ advance method)

### DELETE /cleanup/{file_id}

Dọn dẹp file tạm thời

## Cấu trúc File

```
frontend/
├── index.html          # Giao diện chính
├── style.css           # CSS styling
├── script.js           # JavaScript logic
└── README.md           # Hướng dẫn này
```

## Lưu ý

- Đảm bảo server API đang chạy trước khi sử dụng giao diện
- File upload có giới hạn 10MB
- Server sẽ tự động dọn dẹp file cũ theo thời gian
- Giao diện hỗ trợ responsive design cho mobile
- Có hỗ trợ dark mode tự động theo thiết lập hệ thống

## Troubleshooting

### Lỗi "Không thể kết nối đến server"

- Kiểm tra server API có đang chạy không
- Kiểm tra URL API (mặc định: `http://localhost:8000`)
- Kiểm tra CORS settings trong server

### Upload file thất bại

- Kiểm tra định dạng file có được hỗ trợ không
- Kiểm tra kích thước file (max 10MB)
- Kiểm tra kết nối mạng

### Kết quả trích xuất không chính xác

- Thử các tùy chọn khác nhau (góc xoay, method)
- Kiểm tra chất lượng ảnh đầu vào
- Với Advance Method, thử custom prompt cụ thể hơn
