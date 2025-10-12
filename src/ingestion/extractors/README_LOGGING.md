# Hệ thống OCR Logging và Quality Control

Hệ thống này giúp theo dõi, ghi lại và phân tích chất lượng xử lý OCR, tự động phát hiện các trang có vấn đề.

## Các tính năng chính

### 1. Tự động validation OCR output
- **Nội dung trống**: Phát hiện trang không có text hoặc chỉ có khoảng trắng
- **Nội dung quá ngắn**: Text ít hơn 10 ký tự
- **Thiếu tiếng Việt**: Không đủ ký tự tiếng Việt hoặc từ ngữ
- **Chỉ có số**: Trang chỉ chứa số trang, không có nội dung thực
- **Lỗi runtime**: GPU out of memory, model errors, etc.

### 2. Logging chi tiết
- **JSON log**: Lưu chi tiết từng lỗi với timestamp, file path, error type
- **Statistics**: Thống kê tổng quan số trang thành công/lỗi
- **Error categorization**: Phân loại lỗi theo type để dễ phân tích

### 3. Báo cáo phân tích
- **Markdown report**: Báo cáo dễ đọc với bảng thống kê
- **Analysis tool**: Script phân tích lại folder đã xử lý
- **Quality metrics**: Tỷ lệ thành công, phân bố lỗi

## Cách sử dụng

### 1. Xử lý OCR mới (với logging tự động)
```bash
python3 app/data/ocr-process/vintern_batch_ocr.py app/data/processed/image-process/your-images-folder
```

**Output sẽ bao gồm:**
- `page_001.txt`, `page_002.txt`, ... (từng trang OCR)
- `merged_ocr.md` (tất cả trang gộp lại)
- `ocr_processing_log.json` (log chi tiết các lỗi)

### 2. Phân tích folder đã xử lý trước đó
```bash
python3 app/data/ocr-process/analyze_processed_ocr.py app/data/processed/your-processed-folder
```

**Output sẽ bao gồm:**
- `analysis_log.json` (log phân tích)
- `ocr_analysis_report.md` (báo cáo tóm tắt)

### 3. Test hệ thống logging
```bash
python3 app/data/ocr-process/test_logging.py
```

## Cấu trúc Log File (JSON)

```json
{
  "summary": {
    "total_processed": 165,
    "successful": 162,
    "errors": 3,
    "empty_content": 0,
    "low_quality": 1,
    "runtime_errors": 2
  },
  "processing_date": "2025-09-28T14:44:14.123456",
  "errors": [
    {
      "page_number": 42,
      "image_path": "/path/to/image.jpg",
      "error_type": "insufficient_vietnamese_content",
      "error_message": "OCR validation failed: insufficient_vietnamese_content",
      "ocr_output": "Văn bản thuần",
      "timestamp": "2025-09-28T14:44:10.123456",
      "file_size_mb": 2.5
    }
  ]
}
```

## Các loại lỗi được theo dõi

| Error Type | Mô tả | Nguyên nhân thường gặp |
|------------|-------|------------------------|
| `empty_output` | Không có text hoặc chỉ khoảng trắng | Ảnh trống, không có text |
| `too_short` | Text quá ngắn (< 10 ký tự) | Ảnh chất lượng kém, OCR thất bại |
| `insufficient_vietnamese_content` | Quá ít ký tự tiếng Việt | Ảnh không phải tiếng Việt, OCR sai |
| `too_few_words` | Quá ít từ (< 3 từ) | Ảnh đơn giản, chỉ có vài từ |
| `mostly_numbers` | Chủ yếu là số (>80%) | Trang chỉ có số trang |
| `error_pattern_match` | Khớp pattern lỗi | Chỉ có số trang, text rác |
| `runtime_error` | Lỗi khi xử lý OCR | GPU OOM, model crash |

## Ví dụ thực tế

### Kết quả phân tích folder Decree-24
```
📊 Tóm tắt phân tích:
   📁 Folder: Decreee-24-27-02-2024-processed
   📄 Tổng số trang: 165
   ✅ Thành công: 162 (98.2%)
   ⚠  Có vấn đề: 3 (1.8%)

🚨 Chi tiết các trang có vấn đề:
   page_042.txt: insufficient_vietnamese_content - Văn bản thuần
   page_055.txt: error_pattern_match - 55
   page_098.txt: error_pattern_match - 98
```

## Tùy chỉnh validation

Bạn có thể điều chỉnh các ngưỡng trong file `vintern_batch_ocr.py`:

```python
# OCR quality validation thresholds
MIN_TEXT_LENGTH = 10  # Minimum characters for valid content
MIN_VIETNAMESE_WORDS = 3  # Minimum Vietnamese words
ERROR_PATTERNS = [
    r'\\[OCR_ERROR:.*?\\]',  # Custom error markers
    r'^\\s*$',  # Empty or whitespace only  
    r'^\\d+\\s*$',  # Only page numbers
    # ... thêm pattern khác
]
```

## Best Practices

1. **Luôn kiểm tra log** sau khi xử lý OCR
2. **Phân tích lại** các folder cũ để đảm bảo chất lượng
3. **Xử lý lại** các trang có lỗi nếu cần thiết
4. **Backup log files** để tracking lâu dài
5. **Monitor success rate** để đánh giá hiệu suất OCR

## Troubleshooting

### Q: Tại sao có trang chỉ có số?
A: Có thể do ảnh chỉ chứa số trang, không có content thực. Cần kiểm tra ảnh gốc.

### Q: Làm sao biết trang nào cần xử lý lại?
A: Check file `ocr_analysis_report.md` hoặc log JSON để xem chi tiết các trang lỗi.

### Q: Có thể tùy chỉnh ngưỡng validation không?
A: Có, điều chỉnh các constants trong file `vintern_batch_ocr.py`.