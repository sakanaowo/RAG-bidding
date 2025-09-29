# 📄 MD-Preprocess Module

Module tiền xử lý văn bản pháp luật từ file `.md` với YAML frontmatter thành chunks tối ưu cho hệ thống RAG.

## 🎯 Tính năng chính

- **Parsing YAML frontmatter**: Tự động trích xuất metadata từ header
- **Optimal chunking**: Kết hợp by_dieu và hierarchical smart chunking  
- **Token validation**: Kiểm tra compatibility với embedding models
- **Quality scoring**: Tự động đánh giá chất lượng chunks
- **Export ready**: JSONL format cho vector databases

## 🚀 Cách sử dụng

### 1. Xử lý một file đơn lẻ

```python
from md_processor import MarkdownDocumentProcessor

# Khởi tạo processor
processor = MarkdownDocumentProcessor(
    max_chunk_size=2000,
    min_chunk_size=300,
    token_limit=6500
)

# Xử lý file
chunks, report, output_path = processor.process_single_file(
    "path/to/document.md", 
    "output/directory"
)

print(f"Created {len(chunks)} chunks")
print(f"Quality score: {report['summary']['avg_quality_score']:.2f}")
```

### 2. Xử lý batch nhiều files

```python
from utils import process_md_documents_pipeline

chunks, report = process_md_documents_pipeline(
    input_dir="data/processed/",
    output_dir="data/chunks/"
)
```

### 3. Phân tích document trước khi chunking

```python
# Parse và analyze
document = processor.parse_md_file("document.md")
stats = processor.get_document_stats(document)

print(f"Điều count: {stats['dieu_count']}")
print(f"Estimated tokens: {stats['estimated_tokens']}")
```

## 📊 Kết quả Demo

**Document Analysis:**
- Content: 170,414 chars, 2,215 lines
- Structure: 2 Chương, 95 Điều, 420 Khoản, 531 Điểm  
- Estimated tokens: 60,862

**Chunking Results:**
- Total chunks: 272 (66 dieu + 206 khoan level)
- Average quality score: 0.84/1.0
- Size range: Optimized cho embedding models
- Token efficiency: ~75% utilization

## 🔧 Configuration

### Chunker Parameters

```python
OptimalLegalChunker(
    max_chunk_size=2000,    # Max chars per chunk
    min_chunk_size=300,     # Min chars per chunk  
    token_limit=6500,       # 80% của model limit
    overlap_size=150        # Context overlap
)
```

### Token Models Supported

- `text-embedding-3-small` (8191 tokens) 
- `text-embedding-3-large` (8191 tokens)
- `text-embedding-ada-002` (8191 tokens)
- Custom models via TokenChecker

## 📁 Cấu trúc Output

### JSONL Format
```json
{
  "id": "optimal_dieu_1",
  "text": "[Phần: QUY ĐỊNH CHUNG]\\n\\nĐiều 1. Phạm vi điều chỉnh\\n\\n...",
  "metadata": {
    "title": "Luật Đấu thầu 2023",
    "source": "thuvienphapluat.vn",
    "dieu": "1",
    "chuong": "CHƯƠNG I", 
    "chunk_level": "dieu",
    "hierarchy": "QUY ĐỊNH CHUNG → CHƯƠNG I → Điều 1",
    "char_count": 360,
    "token_count": 205,
    "semantic_tags": ["management"],
    "quality_flags": {
      "good_size": true,
      "good_tokens": true, 
      "good_structure": true
    }
  }
}
```

### Quality Metrics

- **High quality** (≥0.8): Structured, proper size, good tokens
- **Medium quality** (0.5-0.8): Minor issues but usable  
- **Low quality** (<0.5): May need manual review

## 🎯 Integration với RAG System

### 1. Replace existing chunker trong vectorstore.py

```python
from app.data.core.md_preprocess import MarkdownDocumentProcessor

processor = MarkdownDocumentProcessor()
chunks, _ = processor.process_single_file("document.md")
```

### 2. Vector database integration

```python
# Chunks đã ready cho embedding
for chunk in chunks:
    vector_db.add(
        text=chunk['text'],
        metadata=chunk['metadata'],
        id=chunk['id']
    )
```

## 📈 Performance

- **Processing speed**: ~1 second cho document 170K chars
- **Memory efficiency**: Stream processing cho large files
- **Token optimization**: ~75% utilization rate
- **Quality consistency**: 84% average quality score

## 🔍 Semantic Features

### Auto-tagging
- `registration`: đăng ký, hệ thống mạng
- `timeline`: thời gian, thời hạn
- `procedures`: thủ tục, quy trình  
- `documentation`: hồ sơ, tài liệu
- `management`: quản lý, giám sát
- `penalties`: xử phạt, vi phạm
- `requirements`: yêu cầu, điều kiện

### Context Enhancement  
- Hierarchical headers: `[Phần: QUY ĐỊNH CHUNG] [CHƯƠNG I]`
- Breadcrumb navigation: `"hierarchy": "Section → Chapter → Article"`
- Parent-child relationships: Điều → Khoản → Điểm

## 🚀 Roadmap

- **Phase 1**: ✅ Core chunking implementation  
- **Phase 2**: 🔄 Integration với RAG system
- **Phase 3**: ⏳ ML-enhanced semantic chunking
- **Phase 4**: ⏳ Performance optimization
- **Phase 5**: ⏳ Multi-document processing

---

📞 **Support**: Module được thiết kế đặc biệt cho văn bản pháp luật Việt Nam với cấu trúc hierarchical rõ ràng.