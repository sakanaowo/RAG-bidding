# 📖 Thuvienphapluat Crawler Module

Module Python để crawl và trích xuất nội dung từ website thuvienphapluat.vn, chuyển đổi sang định dạng Markdown.

## 🚀 Cài đặt

### 1. Cài đặt dependencies:
```bash
pip install -r requirements.txt
```

### 2. Import module:
```python
from thuvienphapluat_crawler import ThuvienphapluatCrawler, crawl_and_export_to_markdown, batch_crawl_urls
```

## 🎯 Tính năng chính

- ✅ **Crawl nội dung** từ thuvienphapluat.vn
- ✅ **Trích xuất nội dung sạch** từ div có class 'content1'
- ✅ **Chuyển đổi sang Markdown** với headers, paragraphs, lists
- ✅ **Export ra file .md** với metadata và timestamp
- ✅ **Hỗ trợ crawl hàng loạt** nhiều URL
- ✅ **Error handling** và logging chi tiết
- ✅ **Rate limiting** để tránh bị block

## 📚 Cách sử dụng

### 1. Sử dụng convenience functions (đơn giản)

```python
from thuvienphapluat_crawler import crawl_and_export_to_markdown, batch_crawl_urls

# Crawl một URL
url = 'https://thuvienphapluat.vn/van-ban/Dau-tu/Nghi-dinh-214-2025-ND-CP-huong-dan-Luat-Dau-thau-ve-lua-chon-nha-thau-668157.aspx'
output_file = crawl_and_export_to_markdown(url, output_dir="./data/")

# Crawl nhiều URL
urls = [
    'https://thuvienphapluat.vn/van-ban/url1',
    'https://thuvienphapluat.vn/van-ban/url2',
]
results = batch_crawl_urls(urls, output_dir="./data/", delay=3)
```

### 2. Sử dụng class (nâng cao)

```python
from thuvienphapluat_crawler import ThuvienphapluatCrawler

# Khởi tạo crawler với cấu hình tùy chỉnh
crawler = ThuvienphapluatCrawler(
    user_agent='Custom User Agent',
    timeout=60,
    default_output_dir='./custom_data/'
)

# Crawl một URL
result = crawler.crawl_single_url('https://thuvienphapluat.vn/van-ban/...')

# Crawl nhiều URL với delay tùy chỉnh
urls = ['url1', 'url2', 'url3']
results = crawler.crawl_multiple_urls(urls, delay=5)

# Chỉ trích xuất nội dung không export
soup = BeautifulSoup(html_content, 'html.parser')
content_div = soup.find('div', class_='content1')
clean_content = crawler.extract_clean_content(content_div)
```

## 📁 Cấu trúc Output

File markdown được tạo có cấu trúc:

```markdown
---
title: "Nội dung từ thuvienphapluat.vn"
url: https://thuvienphapluat.vn/van-ban/...
crawled_at: 2025-09-29 12:09:57
source: thuvienphapluat.vn
---

# Nội dung chính ở đây...
```

Tên file: `{original_name}_{timestamp}.md`

## 🔧 API Reference

### Class: ThuvienphapluatCrawler

#### Constructor
```python
ThuvienphapluatCrawler(
    user_agent: str = 'Mozilla/5.0...',
    timeout: int = 30,
    default_output_dir: str = "../processed/"
)
```

#### Methods

**crawl_single_url(url, output_dir=None)**
- Crawl một URL và export sang markdown
- Returns: Đường dẫn file đã tạo hoặc None

**crawl_multiple_urls(urls, output_dir=None, delay=2)**
- Crawl nhiều URL với delay
- Returns: List các kết quả crawling

**extract_clean_content(content_div)**
- Trích xuất nội dung sạch từ BeautifulSoup element
- Returns: String markdown

**export_to_markdown(content, url, output_dir=None)**
- Export nội dung ra file markdown
- Returns: Đường dẫn file đã tạo hoặc None

### Convenience Functions

**crawl_and_export_to_markdown(url, output_dir="../processed/")**
- Function đơn giản để crawl một URL

**batch_crawl_urls(urls, output_dir="../processed/", delay=2)**  
- Function đơn giản để crawl nhiều URL

## ⚠️ Lưu ý quan trọng

1. **Respect robots.txt** - Luôn tuân thủ robots.txt của website
2. **Rate limiting** - Sử dụng delay hợp lý (2-5 giây) giữa các request
3. **Error handling** - Kiểm tra return value trước khi sử dụng
4. **Content validation** - Verify nội dung trước khi process tiếp

## 📊 Examples với kết quả thực tế

```python
# Test với URL thực tế
url = 'https://thuvienphapluat.vn/van-ban/Dau-tu/Nghi-dinh-214-2025-ND-CP-huong-dan-Luat-Dau-thau-ve-lua-chon-nha-thau-668157.aspx'

result = crawl_and_export_to_markdown(url)
# Output: 
# 🔄 Bắt đầu crawl: https://thuvienphapluat.vn/van-ban/...
# 📡 Status code: 200
# ✅ Tìm thấy nội dung
# 📝 Đã trích xuất 423621 ký tự
# ✅ Đã export thành công vào file: ../processed/Nghi-dinh-214-2025-ND-CP-huong-dan-Luat-Dau-thau-ve-lua-chon-nha-thau-668157_20250929_120957.md
# 📄 Kích thước file: 573,613 bytes
```

## 🛠️ Troubleshooting

**Lỗi HTTP 403/429:**
- Tăng delay giữa các request
- Thay đổi User-Agent
- Kiểm tra robots.txt

**Không tìm thấy nội dung:**
- Website có thể đã thay đổi cấu trúc HTML
- Kiểm tra CSS selector 'div.content1'

**Lỗi encoding:**
- File được lưu với encoding UTF-8
- Đảm bảo hệ thống hỗ trợ UTF-8

## 🔄 Phát triển và mở rộng

Module có thể được mở rộng để:
- Hỗ trợ thêm website khác
- Thêm format output (JSON, XML, etc.)  
- Cải thiện parsing logic
- Thêm tính năng cache
- Tích hợp database storage

## 📝 License

MIT License - Có thể sử dụng tự do cho dự án cá nhân và thương mại.