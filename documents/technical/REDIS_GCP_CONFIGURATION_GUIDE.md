# Hướng Dẫn Cấu Hình Redis trên Google Cloud cho RAG-Bidding

> **Ngày tạo:** 2026-01-31  
> **Dự án:** RAG-Bidding System  
> **Mục đích:** Hướng dẫn chi tiết deploy Redis (Memorystore) trên Google Cloud Platform

---

## Mục Lục

1. [Tổng Quan Kiến Trúc Redis Hiện Tại](#1-tổng-quan-kiến-trúc-redis-hiện-tại)
2. [Yêu Cầu Trước Khi Bắt Đầu](#2-yêu-cầu-trước-khi-bắt-đầu)
3. [Bước 1: Tạo Memorystore Redis Instance](#3-bước-1-tạo-memorystore-redis-instance)
4. [Bước 2: Cấu Hình VPC Network](#4-bước-2-cấu-hình-vpc-network)
5. [Bước 3: Deploy Cloud Run với Direct VPC Egress](#5-bước-3-deploy-cloud-run-với-direct-vpc-egress)
6. [Bước 4: Cấu Hình Environment Variables](#6-bước-4-cấu-hình-environment-variables)
7. [Bước 5: Cập Nhật Code Hỗ Trợ AUTH (Tùy chọn)](#7-bước-5-cập-nhật-code-hỗ-trợ-auth-tùy-chọn)
8. [Bước 6: Kiểm Tra Kết Nối](#8-bước-6-kiểm-tra-kết-nối)
9. [Troubleshooting](#9-troubleshooting)
10. [Tài Liệu Tham Khảo](#10-tài-liệu-tham-khảo)

---

## 1. Tổng Quan Kiến Trúc Redis Hiện Tại

### 1.1 Các Module Sử Dụng Redis

Project RAG-Bidding sử dụng Redis cho **5 mục đích chính**, với **5 Redis databases riêng biệt**:

| Redis DB | Mục Đích | Environment Variable | TTL Mặc Định | File Source |
|----------|----------|---------------------|--------------|-------------|
| **DB 0** | Retrieval Cache (L2) | `REDIS_DB_CACHE` | 3600s (1 giờ) | `src/retrieval/cached_retrieval.py` |
| **DB 1** | Chat Sessions | `REDIS_DB_SESSIONS` | 3600s (1 giờ) | `src/retrieval/context_cache.py` |
| **DB 2** | Answer Cache | `ANSWER_CACHE_DB` | 86400s (24 giờ) | `src/retrieval/answer_cache.py` |
| **DB 3** | Semantic Cache (Embeddings) | `SEMANTIC_CACHE_DB` | Không giới hạn | `src/retrieval/semantic_cache_v2.py` |
| **DB 4** | Rate Limiting | `RATE_LIMIT_REDIS_DB` | 86400s (24 giờ) | `src/api/services/rate_limit_service.py` |

### 1.2 Kiến Trúc Cache Multi-Layer

```
┌─────────────────────────────────────────────────────────────────┐
│                        RAG Query Flow                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Query ──► L1 Cache (Memory) ──► L2 Cache (Redis) ──► L3 (PostgreSQL)
│              │                      │                      │    │
│              ▼                      ▼                      ▼    │
│           ~1ms                   ~5-10ms               ~50-100ms│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 Cấu Hình Hiện Tại (Development - localhost)

```env
# File: .env (hiện tại)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB_CACHE=0
REDIS_DB_SESSIONS=1
ANSWER_CACHE_DB=2
SEMANTIC_CACHE_DB=3
RATE_LIMIT_REDIS_DB=4
ENABLE_REDIS_CACHE=true
```

---

## 2. Yêu Cầu Trước Khi Bắt Đầu

### 2.1 Công Cụ Cần Thiết

- [ ] **Google Cloud SDK (gcloud CLI)** - Đã cài đặt và đăng nhập
- [ ] **Quyền IAM** trên GCP Project:
  - `roles/redis.admin` - Quản lý Memorystore
  - `roles/run.admin` - Quản lý Cloud Run
  - `roles/compute.networkAdmin` - Quản lý VPC

### 2.2 Kiểm Tra Cài Đặt

```bash
# Kiểm tra gcloud đã cài đặt
gcloud --version

# Đăng nhập (nếu chưa)
gcloud auth login

# Set project
gcloud config set project YOUR_PROJECT_ID

# Kiểm tra project hiện tại
gcloud config get-value project
```

### 2.3 Enable APIs Cần Thiết

```bash
# Enable các API cần thiết
gcloud services enable redis.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable vpcaccess.googleapis.com
gcloud services enable compute.googleapis.com
```

---

## 3. Bước 1: Tạo Memorystore Redis Instance

### 3.1 Thiết Lập Biến Môi Trường

```bash
# ============================================
# THIẾT LẬP BIẾN - CHỈNH SỬA THEO NHU CẦU
# ============================================

export PROJECT_ID="your-gcp-project-id"        # ← Thay đổi
export REGION="asia-southeast1"                 # Singapore (gần Việt Nam)
export REDIS_INSTANCE_ID="rag-bidding-redis"
export REDIS_TIER="BASIC"                       # BASIC hoặc STANDARD_HA
export REDIS_SIZE_GB="1"                        # Dung lượng (GB)
export REDIS_VERSION="redis_7_0"                # Redis version

# Xác nhận các biến
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Redis Instance: $REDIS_INSTANCE_ID"
```

### 3.2 Chọn Redis Tier

| Tier | Mô Tả | Use Case | Giá (ước tính) |
|------|-------|----------|----------------|
| **BASIC** | Single node, không HA | Development, staging | ~$0.049/GB/hour |
| **STANDARD_HA** | Replica tự động, failover | Production | ~$0.098/GB/hour |

### 3.3 Tạo Redis Instance

```bash
# Tạo Redis instance
gcloud redis instances create $REDIS_INSTANCE_ID \
  --size=$REDIS_SIZE_GB \
  --region=$REGION \
  --tier=$REDIS_TIER \
  --redis-version=$REDIS_VERSION \
  --redis-config maxmemory-policy=allkeys-lru \
  --display-name="RAG Bidding Redis Cache"

# Đợi instance được tạo (khoảng 5-10 phút)
echo "⏳ Đang tạo Redis instance... (5-10 phút)"
```

### 3.4 Lấy Thông Tin Redis Instance

```bash
# Xem chi tiết instance
gcloud redis instances describe $REDIS_INSTANCE_ID \
  --region=$REGION

# Lấy IP address của Redis
export REDIS_IP=$(gcloud redis instances describe $REDIS_INSTANCE_ID \
  --region=$REGION \
  --format="value(host)")

echo "✅ Redis IP: $REDIS_IP"

# Lấy tên authorized network
export AUTHORIZED_NETWORK=$(gcloud redis instances describe $REDIS_INSTANCE_ID \
  --region=$REGION \
  --format="value(authorizedNetwork)")

echo "✅ Authorized Network: $AUTHORIZED_NETWORK"

# Lấy port (mặc định 6379)
export REDIS_PORT=$(gcloud redis instances describe $REDIS_INSTANCE_ID \
  --region=$REGION \
  --format="value(port)")

echo "✅ Redis Port: $REDIS_PORT"
```

### 3.5 Lưu Thông Tin Quan Trọng

```bash
# Ghi lại thông tin vào file
cat > redis_connection_info.txt << EOF
# ==========================================
# REDIS MEMORYSTORE CONNECTION INFO
# Created: $(date)
# ==========================================

PROJECT_ID=$PROJECT_ID
REGION=$REGION
REDIS_INSTANCE_ID=$REDIS_INSTANCE_ID
REDIS_IP=$REDIS_IP
REDIS_PORT=$REDIS_PORT
AUTHORIZED_NETWORK=$AUTHORIZED_NETWORK

# Connection string (for reference)
# redis://$REDIS_IP:$REDIS_PORT
EOF

echo "📝 Thông tin đã lưu vào: redis_connection_info.txt"
cat redis_connection_info.txt
```

---

## 4. Bước 2: Cấu Hình VPC Network

### 4.1 Kiểm Tra VPC Network Hiện Có

```bash
# Liệt kê các VPC networks
gcloud compute networks list

# Xem chi tiết network mặc định
gcloud compute networks describe default
```

### 4.2 Kiểm Tra Subnets

```bash
# Liệt kê subnets trong region
gcloud compute networks subnets list \
  --network=default \
  --filter="region:$REGION"

# Lấy tên subnet
export SUBNET_NAME=$(gcloud compute networks subnets list \
  --network=default \
  --filter="region:$REGION" \
  --format="value(name)" \
  --limit=1)

echo "✅ Subnet: $SUBNET_NAME"
```

### 4.3 Tạo Subnet Mới (Nếu Cần)

> **Lưu ý:** Direct VPC Egress yêu cầu subnet có CIDR `/26` hoặc lớn hơn.

```bash
# Chỉ chạy nếu cần tạo subnet mới
gcloud compute networks subnets create rag-bidding-subnet \
  --network=default \
  --region=$REGION \
  --range=10.10.0.0/24

export SUBNET_NAME="rag-bidding-subnet"
```

---

## 5. Bước 3: Deploy Cloud Run với Direct VPC Egress

### 5.1 Tại Sao Chọn Direct VPC Egress?

| Tiêu Chí | Direct VPC Egress ✅ | VPC Connector |
|----------|---------------------|---------------|
| **Latency** | Thấp hơn | Cao hơn |
| **Throughput** | Cao hơn | Thấp hơn |
| **Chi phí** | Chỉ network traffic | + VM charges |
| **Setup** | Đơn giản | Phức tạp hơn |

> 📌 **Google khuyến nghị:** "Use Direct VPC egress because it offers lower latency, higher throughput, and lower costs."

### 5.2 Build Docker Image

```bash
# Di chuyển đến thư mục project
cd /path/to/RAG-bidding

# Build image
gcloud builds submit --tag gcr.io/$PROJECT_ID/rag-bidding-api

# Hoặc sử dụng Artifact Registry (khuyến nghị)
gcloud builds submit --tag $REGION-docker.pkg.dev/$PROJECT_ID/rag-repo/rag-bidding-api
```

### 5.3 Deploy Cloud Run Service

```bash
# Deploy với Direct VPC Egress
gcloud run deploy rag-bidding-api \
  --image gcr.io/$PROJECT_ID/rag-bidding-api \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --network default \
  --subnet $SUBNET_NAME \
  --vpc-egress all-traffic \
  --set-env-vars "\
REDIS_HOST=$REDIS_IP,\
REDIS_PORT=$REDIS_PORT,\
REDIS_DB_CACHE=0,\
REDIS_DB_SESSIONS=1,\
ANSWER_CACHE_DB=2,\
SEMANTIC_CACHE_DB=3,\
RATE_LIMIT_REDIS_DB=4,\
ENABLE_REDIS_CACHE=true,\
ENABLE_REDIS_SESSIONS=true,\
ENABLE_ANSWER_CACHE=true,\
ENABLE_SEMANTIC_CACHE=true,\
RATE_LIMIT_ENABLED=true" \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --concurrency 80 \
  --min-instances 0 \
  --max-instances 10
```

### 5.4 Xác Nhận Deployment

```bash
# Xem thông tin service
gcloud run services describe rag-bidding-api --region $REGION

# Lấy URL
SERVICE_URL=$(gcloud run services describe rag-bidding-api \
  --region $REGION \
  --format="value(status.url)")

echo "✅ Service URL: $SERVICE_URL"
```

---

## 6. Bước 4: Cấu Hình Environment Variables

### 6.1 File `.env.production` Hoàn Chỉnh

Tạo file `.env.production` trong thư mục project:

```env
# ================================================================
# RAG-BIDDING PRODUCTION ENVIRONMENT
# Google Cloud Platform Configuration
# ================================================================

# ==========================================
# REDIS MEMORYSTORE CONFIGURATION
# ==========================================

# Memorystore Redis Instance IP (từ Bước 3.4)
REDIS_HOST=10.x.x.x                    # ← Thay bằng REDIS_IP thực tế
REDIS_PORT=6379

# Redis Database Allocation
REDIS_DB_CACHE=0                       # Retrieval cache
REDIS_DB_SESSIONS=1                    # Chat sessions
ANSWER_CACHE_DB=2                      # Answer cache
SEMANTIC_CACHE_DB=3                    # Semantic embeddings cache
RATE_LIMIT_REDIS_DB=4                  # Rate limiting

# Redis AUTH (nếu đã enable)
# REDIS_PASSWORD=your-auth-string      # Bỏ comment nếu dùng AUTH

# ==========================================
# FEATURE FLAGS - REDIS
# ==========================================

ENABLE_REDIS_CACHE=true
ENABLE_REDIS_SESSIONS=true
ENABLE_ANSWER_CACHE=true
ENABLE_SEMANTIC_CACHE=true
RATE_LIMIT_ENABLED=true

# ==========================================
# CACHE TTL SETTINGS
# ==========================================

CACHE_TTL=3600                         # Retrieval cache: 1 hour
ANSWER_CACHE_TTL=86400                 # Answer cache: 24 hours
SEMANTIC_CACHE_THRESHOLD=0.95          # Similarity threshold
MAX_SEMANTIC_SEARCH=100                # Max queries to scan

# ==========================================
# RATE LIMITING
# ==========================================

RATE_LIMIT_DAILY_QUERIES=200           # Queries per user per day

# ==========================================
# DATABASE (Cloud SQL)
# ==========================================

DATABASE_URL=postgresql://user:password@/rag_bidding_v3?host=/cloudsql/project:region:instance

# ==========================================
# API CONFIGURATION
# ==========================================

API_HOST=0.0.0.0
API_PORT=8080
LOG_LEVEL=INFO
```

### 6.2 Cập Nhật Environment Variables trên Cloud Run

```bash
# Cập nhật env vars từ file
gcloud run services update rag-bidding-api \
  --region $REGION \
  --update-env-vars "$(cat .env.production | grep -v '^#' | grep -v '^$' | tr '\n' ',')"
```

Hoặc cập nhật từng biến:

```bash
gcloud run services update rag-bidding-api \
  --region $REGION \
  --set-env-vars "REDIS_HOST=$REDIS_IP"
```

---

## 7. Bước 5: Cập Nhật Code Hỗ Trợ AUTH (Tùy chọn)

> ⚠️ **Lưu ý:** Bước này chỉ cần thiết nếu bạn enable AUTH trên Memorystore Redis.

### 7.1 Enable AUTH trên Memorystore

```bash
# Enable AUTH feature
gcloud redis instances update $REDIS_INSTANCE_ID \
  --region=$REGION \
  --enable-auth

# Lấy AUTH string
REDIS_AUTH_STRING=$(gcloud redis instances get-auth-string $REDIS_INSTANCE_ID \
  --region=$REGION \
  --format="value(authString)")

echo "🔐 Redis AUTH String: $REDIS_AUTH_STRING"
```

### 7.2 Cập Nhật `feature_flags.py`

Thêm cấu hình REDIS_PASSWORD vào file `src/config/feature_flags.py`:

```python
# ========================================
# CACHE CONFIGURATION
# ========================================

# Redis cache settings
ENABLE_REDIS_CACHE = os.getenv("ENABLE_REDIS_CACHE", "false").lower() == "true"
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)  # ← THÊM DÒNG NÀY
REDIS_DB_CACHE = int(os.getenv("REDIS_DB_CACHE", "0"))
REDIS_DB_SESSIONS = int(os.getenv("REDIS_DB_SESSIONS", "1"))
```

### 7.3 Cập Nhật Các Redis Connection Files

Cần cập nhật 5 files để hỗ trợ AUTH:

#### File 1: `src/retrieval/cached_retrieval.py`

```python
# Tìm đoạn code này (khoảng dòng 50):
self.redis = redis.Redis(
    host=redis_host,
    port=redis_port,
    db=redis_db,
    decode_responses=False,
)

# Thay thế bằng:
self.redis = redis.Redis(
    host=redis_host,
    port=redis_port,
    db=redis_db,
    password=redis_password,  # Thêm parameter này
    decode_responses=False,
)
```

#### File 2: `src/retrieval/answer_cache.py`

```python
# Tìm đoạn code này (khoảng dòng 134):
self._redis = redis.Redis(
    host=redis_host,
    port=redis_port,
    db=redis_db,
    decode_responses=False,
    socket_connect_timeout=5,
)

# Thay thế bằng:
from src.config.feature_flags import REDIS_PASSWORD

self._redis = redis.Redis(
    host=redis_host,
    port=redis_port,
    db=redis_db,
    password=REDIS_PASSWORD,  # Thêm parameter này
    decode_responses=False,
    socket_connect_timeout=5,
)
```

#### File 3: `src/retrieval/context_cache.py`

```python
# Tìm đoạn code này (khoảng dòng 84):
self.redis = redis.Redis(
    host=redis_host,
    port=redis_port,
    db=redis_db,
    decode_responses=True,
)

# Thay thế bằng:
from src.config.feature_flags import REDIS_PASSWORD

self.redis = redis.Redis(
    host=redis_host,
    port=redis_port,
    db=redis_db,
    password=REDIS_PASSWORD,  # Thêm parameter này
    decode_responses=True,
)
```

#### File 4: `src/retrieval/semantic_cache_v2.py`

```python
# Tìm đoạn code này (khoảng dòng 160):
self._redis = redis.Redis(
    host=redis_host,
    port=redis_port,
    db=redis_db,
    decode_responses=False,
    socket_connect_timeout=5,
)

# Thay thế bằng:
from src.config.feature_flags import REDIS_PASSWORD

self._redis = redis.Redis(
    host=redis_host,
    port=redis_port,
    db=redis_db,
    password=REDIS_PASSWORD,  # Thêm parameter này
    decode_responses=False,
    socket_connect_timeout=5,
)
```

#### File 5: `src/api/services/rate_limit_service.py`

```python
# Tìm đoạn code này (khoảng dòng 88):
_redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=RATE_LIMIT_REDIS_DB,
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
)

# Thay thế bằng:
from src.config.feature_flags import REDIS_PASSWORD

_redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=RATE_LIMIT_REDIS_DB,
    password=REDIS_PASSWORD,  # Thêm parameter này
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
)
```

---

## 8. Bước 6: Kiểm Tra Kết Nối

### 8.1 Test Connection từ Cloud Run

```bash
# Gọi API health check
curl -X GET "$SERVICE_URL/health"

# Gọi API cache stats
curl -X GET "$SERVICE_URL/api/v1/cache/stats"
```

### 8.2 Kết Quả Mong Đợi

```json
{
  "retrieval_cache": {
    "l1_hits": 0,
    "l2_hits": 0,
    "total_queries": 0
  },
  "answer_cache": {
    "enabled": true,
    "l1_size": 0,
    "l2_connected": true
  },
  "semantic_cache": {
    "enabled": true,
    "total_searches": 0,
    "semantic_hits": 0
  },
  "configuration": {
    "redis_enabled": true,
    "l1_enabled": true,
    "retrieval_ttl_seconds": 3600
  }
}
```

### 8.3 Test Redis Connection Trực Tiếp (từ Compute Engine VM)

```bash
# Tạo VM trong cùng VPC network
gcloud compute instances create redis-test-vm \
  --zone=${REGION}-a \
  --machine-type=e2-micro \
  --network=default

# SSH vào VM
gcloud compute ssh redis-test-vm --zone=${REGION}-a

# Cài đặt redis-cli
sudo apt-get update && sudo apt-get install -y redis-tools

# Test connection
redis-cli -h $REDIS_IP ping
# Expected: PONG

# Test với AUTH (nếu đã enable)
redis-cli -h $REDIS_IP -a $REDIS_AUTH_STRING ping
```

### 8.4 Monitoring Redis

```bash
# Xem metrics của Redis instance
gcloud redis instances describe $REDIS_INSTANCE_ID \
  --region=$REGION

# Hoặc xem trên Cloud Console:
# https://console.cloud.google.com/memorystore/redis/instances
```

---

## 9. Troubleshooting

### 9.1 Lỗi "Connection Refused"

**Nguyên nhân:** Cloud Run không thể kết nối đến Redis.

**Giải pháp:**
```bash
# Kiểm tra VPC network
gcloud run services describe rag-bidding-api --region $REGION | grep -A5 "vpcAccess"

# Đảm bảo Redis và Cloud Run cùng VPC
gcloud redis instances describe $REDIS_INSTANCE_ID --region $REGION | grep authorizedNetwork
```

### 9.2 Lỗi "NOAUTH Authentication Required"

**Nguyên nhân:** Redis yêu cầu AUTH nhưng code chưa gửi password.

**Giải pháp:**
1. Kiểm tra AUTH đã enable chưa: `gcloud redis instances describe $REDIS_INSTANCE_ID --region $REGION | grep authEnabled`
2. Nếu đã enable, cập nhật code theo [Bước 7](#7-bước-5-cập-nhật-code-hỗ-trợ-auth-tùy-chọn)

### 9.3 Lỗi "Timeout"

**Nguyên nhân:** Network latency hoặc firewall rules.

**Giải pháp:**
```bash
# Kiểm tra firewall rules
gcloud compute firewall-rules list --filter="network:default"

# Tạo firewall rule cho Redis (nếu cần)
gcloud compute firewall-rules create allow-redis \
  --network=default \
  --allow=tcp:6379 \
  --source-ranges=10.0.0.0/8
```

### 9.4 Lỗi "OOM (Out of Memory)"

**Nguyên nhân:** Redis hết bộ nhớ.

**Giải pháp:**
```bash
# Tăng kích thước instance
gcloud redis instances update $REDIS_INSTANCE_ID \
  --region=$REGION \
  --size=2
```

---

## 10. Tài Liệu Tham Khảo

### Google Cloud Official Documentation

| Tài liệu | Link |
|----------|------|
| Memorystore for Redis Overview | https://cloud.google.com/memorystore/docs/redis/memorystore-for-redis-overview |
| Connect Redis from Cloud Run | https://cloud.google.com/memorystore/docs/redis/connect-redis-instance-cloud-run |
| Direct VPC Egress Configuration | https://cloud.google.com/run/docs/configuring/vpc-direct-vpc |
| Redis AUTH | https://cloud.google.com/memorystore/docs/redis/auth-overview |
| Memorystore Best Practices | https://cloud.google.com/memorystore/docs/redis/general-best-practices |
| Memory Management | https://cloud.google.com/memorystore/docs/redis/memory-management-best-practices |
| Troubleshooting | https://cloud.google.com/memorystore/docs/redis/troubleshoot-issues |

### Project Files Reference

| File | Mô tả |
|------|-------|
| `src/config/feature_flags.py` | Cấu hình Redis và feature flags |
| `src/retrieval/cached_retrieval.py` | CachedVectorStore với Redis L2 |
| `src/retrieval/answer_cache.py` | Answer-level cache |
| `src/retrieval/semantic_cache_v2.py` | Semantic similarity cache |
| `src/retrieval/context_cache.py` | Conversation context cache |
| `src/api/services/rate_limit_service.py` | Rate limiting service |
| `src/api/routers/cache.py` | Cache management API endpoints |

---

## Checklist Hoàn Thành

- [ ] Enable Google Cloud APIs (redis, run, vpcaccess, compute)
- [ ] Tạo Memorystore Redis instance
- [ ] Ghi lại Redis IP và authorized network
- [ ] Kiểm tra/tạo subnet phù hợp
- [ ] Build và push Docker image
- [ ] Deploy Cloud Run với Direct VPC egress
- [ ] Cấu hình environment variables
- [ ] (Optional) Enable AUTH và cập nhật code
- [ ] Test connection qua `/api/v1/cache/stats`
- [ ] Verify cache hoạt động với test queries

---

> 📝 **Ghi chú:** Document này được tạo dựa trên phân tích code thực tế của project RAG-Bidding và tài liệu chính thức của Google Cloud (cập nhật 2026-01-22).
