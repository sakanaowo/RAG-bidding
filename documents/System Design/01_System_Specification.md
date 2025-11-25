# Đặc Tả Hệ Thống RAG Bidding

**Ngày tạo:** 24/11/2025  
**Phiên bản:** 2.0  
**Tác giả:** System Architecture Team

---

## 1. Tổng Quan Hệ Thống

### 1.1. Giới Thiệu

RAG Bidding System là hệ thống hỏi đáp dựa trên Retrieval-Augmented Generation (RAG) chuyên biệt cho lĩnh vực pháp lý và đấu thầu Việt Nam. Hệ thống kết hợp semantic search, document reranking, và multi-tier caching để cung cấp câu trả lời chính xác, nhanh chóng từ kho tài liệu pháp luật.

### 1.2. Mục Tiêu

- **Độ chính xác cao:** Cung cấp câu trả lời chính xác từ văn bản pháp luật và tài liệu đấu thầu
- **Hiệu suất tối ưu:** Phản hồi nhanh (1-3s) cho truy vấn thường gặp
- **Khả năng mở rộng:** Hỗ trợ 100+ concurrent users với connection pooling
- **Quản lý tài liệu:** Upload, xử lý, và phân loại tự động các loại văn bản pháp lý
- **Trải nghiệm người dùng:** Hỗ trợ chat sessions, lịch sử truy vấn, và context awareness

### 1.3. Phạm Vi

**Trong phạm vi:**

- Hỏi đáp về luật, nghị định, thông tư, quyết định
- Tìm kiếm ngữ nghĩa trong tài liệu đấu thầu
- Upload và xử lý văn bản DOCX/PDF
- Quản lý metadata và phân loại tài liệu
- Chat sessions với context preservation

**Ngoài phạm vi (v2.0):**

- Xử lý ảnh/video trong tài liệu
- Real-time collaboration
- Multi-language support (chỉ Tiếng Việt)
- OCR cho tài liệu scan

---

## 2. Kiến Trúc Tổng Quan

### 2.1. Tech Stack

**Backend:**

- **Framework:** FastAPI (Python 3.10+)
- **Database:** PostgreSQL 18 + pgvector 0.8.1
- **Cache:** Redis 7+ (multi-tier: L1 In-Memory LRU + L2 Redis)
- **Vector Search:** LangChain + PGVector
- **Embedding:** OpenAI text-embedding-3-large (3072-dim)
- **Reranking:** BAAI/bge-reranker-v2-m3 (cross-encoder)
- **LLM:** OpenAI GPT-4o-mini

**Infrastructure:**

- **Deployment:** Uvicorn ASGI server
- **Connection Pool:** pgBouncer (planned)
- **Monitoring:** Custom metrics endpoint
- **Logging:** Structured logging với rotation

### 2.2. Core Components

```
┌─────────────────────────────────────────────────────────────────┐
│                      CLIENT LAYER                                │
│  Web Browser / API Client / cURL / Postman                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   API LAYER (FastAPI)                            │
│  Endpoints: /ask, /upload, /chat, /health, /stats              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   RAG PIPELINE                                   │
│  Query Enhancement → Vector Search → Reranking → LLM Answer    │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   STORAGE LAYER                                  │
│  PostgreSQL + pgvector | Redis Cache | In-Memory LRU           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Yêu Cầu Phi Chức Năng

### 3.1. Performance

| Metric                         | Target    | Current            |
| ------------------------------ | --------- | ------------------ |
| Query Response (balanced mode) | < 3s      | ~2-3s ✅           |
| Query Response (fast mode)     | < 1.5s    | ~1s ✅             |
| Document Processing            | < 1s/file | ~0.35s ✅          |
| Vector Search (no cache)       | < 100ms   | ~50ms ✅           |
| Cache Hit Rate (L1)            | > 40%     | 40-60% ✅          |
| Concurrent Users               | 100+      | ~10 (need pooling) |

### 3.2. Scalability

- **Horizontal:** Stateless API design cho load balancing
- **Vertical:** Optimized queries, connection pooling
- **Storage:** 1M+ documents (estimated 200GB)
- **Cache:** Redis cluster cho distributed caching

### 3.3. Availability

- **Uptime:** 99.5% (planned)
- **Backup:** Daily automated backups
- **Recovery:** < 1 hour RPO, < 4 hours RTO

### 3.4. Security

- **Authentication:** JWT/OAuth2 (planned)
- **Authorization:** Role-based access control (RBAC)
- **Data Encryption:** TLS 1.3 in transit, AES-256 at rest
- **API Rate Limiting:** 100 requests/minute per IP
- **Input Validation:** Sanitize all user inputs
- **Secrets Management:** Environment variables only

### 3.5. Maintainability

- **Code Quality:** Type hints, docstrings, unit tests
- **Documentation:** Comprehensive docs trong `/documents`
- **Logging:** Structured logs với correlation IDs
- **Monitoring:** Metrics endpoint cho Prometheus/Grafana

---

## 4. Data Flow

### 4.1. Query Processing Flow

```
1. User Query → API Layer
2. Query Enhancement (Multi-Query/HyDE/Step-Back)
3. Cache Check (L1 → L2 → L3)
4. Vector Search (PGVector cosine similarity)
5. Reranking (BGE cross-encoder)
6. Context Preparation
7. LLM Generation (GPT-4o-mini)
8. Cache Update
9. Response to User
```

### 4.2. Document Upload Flow

```
1. File Upload → API Layer
2. File Validation (type, size)
3. Document Classification (auto-detect type)
4. Background Processing (async)
   - Parse structure (hierarchical)
   - Extract metadata (NER, keywords)
   - Semantic enrichment
   - Chunking (hierarchical, 1000 chars)
5. Embedding Generation (OpenAI)
6. Storage (PostgreSQL + pgvector)
7. Index Creation (vector + metadata)
8. Status Update (processing → active)
```

---

## 5. RAG Pipeline Modes

### 5.1. Mode Configuration

| Mode            | Enhancement             | Reranking | Latency | Use Case                   |
| --------------- | ----------------------- | --------- | ------- | -------------------------- |
| **fast**        | None                    | No        | ~1s     | Quick lookups, high volume |
| **balanced** ⭐ | Multi-Query + Step-Back | BGE       | ~2-3s   | Production default         |
| **quality**     | All 4 strategies        | BGE       | ~3-5s   | Complex queries            |
| **adaptive**    | Dynamic K               | BGE       | ~2-4s   | Auto-adjust                |

### 5.2. Enhancement Strategies

1. **Multi-Query:** Generate 3 variations of query
2. **HyDE:** Generate hypothetical ideal answer
3. **Step-Back:** Generate broader context query
4. **Original:** Keep original query
5. **Fusion:** RRF (Reciprocal Rank Fusion)

---

## 6. Caching Strategy

### 6.1. Three-Tier Cache Architecture

**L1 Cache (In-Memory LRU):**

- Technology: `functools.lru_cache`
- Max Size: 500 queries
- Hit Rate: 40-60%
- Latency: <1ms
- Persistence: No

**L2 Cache (Redis):**

- DB 0: Retrieval cache
- DB 1: Chat sessions (deprecated)
- TTL: 3600s (1 hour)
- Hit Rate: 20-30%
- Latency: 5-10ms
- Persistence: Optional

**L3 Cache (PostgreSQL):**

- Native database storage
- No TTL (permanent)
- Latency: ~50ms
- Always available

### 6.2. Cache Invalidation

- **Automatic:** TTL expiration
- **Manual:** `/clear_cache` API endpoint
- **Triggers:** Document status change, metadata update

---

## 7. Monitoring & Observability

### 7.1. Metrics

- **Query Metrics:** Latency, throughput, error rate
- **Cache Metrics:** Hit rate, miss rate, eviction rate
- **Database Metrics:** Connection pool usage, query time
- **Resource Metrics:** CPU, memory, disk I/O

### 7.2. Logging

- **Format:** Structured JSON logs
- **Level:** INFO (production), DEBUG (development)
- **Rotation:** Daily, keep 30 days
- **Location:** `logs/server-log.txt`

### 7.3. Alerting

- High error rate (>5%)
- High latency (>5s p95)
- Connection pool exhaustion
- Redis memory threshold (>80%)

---

## 8. Deployment Strategy

### 8.1. Development

```bash
conda activate venv
./start_server.sh  # Uvicorn on port 8000
```

### 8.2. Production Checklist

- [ ] Enable pgBouncer connection pooling
- [ ] Configure Redis persistence
- [ ] Set up SSL/TLS certificates
- [ ] Enable rate limiting
- [ ] Configure log rotation
- [ ] Set up monitoring dashboard
- [ ] Enable automated backups
- [ ] Load testing với 100+ users

---

## 9. Future Enhancements

### 9.1. Short-term (Q1 2026)

- [ ] User authentication (JWT/OAuth2)
- [ ] Chat session persistence migration
- [ ] Advanced analytics dashboard
- [ ] Export query results (PDF/Excel)

### 9.2. Long-term (Q2-Q4 2026)

- [ ] Multi-language support
- [ ] OCR for scanned documents
- [ ] Real-time collaboration
- [ ] Mobile app
- [ ] Fine-tuned domain-specific LLM
- [ ] Feedback loop cho model improvement

---

## 10. Tài Liệu Liên Quan

- `02_Use_Cases.md` - Chi tiết các use case
- `03_Database_Schema.md` - Thiết kế database
- `04_System_Architecture.md` - Kiến trúc chi tiết
- `05_API_Specification.md` - API documentation
- `/temp/database_schema_explained.txt` - Database reference
- `/temp/system_architecture.txt` - Architecture reference
