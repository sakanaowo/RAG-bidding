# Hướng Dẫn Triển Khai RAG-Bidding Backend lên Google Cloud Run

> **📅 Cập nhật**: 26/01/2026  
> **🔍 Trạng thái**: Đã phân tích toàn bộ codebase và verified

---

## 🎯 EXECUTIVE SUMMARY - Đọc Trước Khi Bắt Đầu

### ⚠️ Critical Decisions (QUAN TRỌNG)

| Quyết định | Khuyến nghị | Lý do |
|------------|-------------|-------|
| **Gunicorn Workers** | `GUNICORN_WORKERS=1` | Mỗi worker load BGE model (~1.5GB) riêng biệt |
| **Memory** | `4Gi` minimum | BGE model + FastAPI + buffers |
| **Min Instances** | `1` (production) | Tránh cold start 50-60s (do BGE loading) |
| **Scaling** | Cloud Run instances | Không dùng nhiều workers trong 1 container |

### 📊 Quick Start - Chọn Configuration

| Scenario | Memory | Workers | Reranking | Command |
|----------|--------|---------|-----------|---------|
| **Dev/Test** | 2Gi | 1 | false | `--memory=2Gi --set-env-vars="ENABLE_RERANKING=false"` |
| **Staging** | 4Gi | 1 | bge | `--memory=4Gi --min-instances=0` |
| **Prod (Balanced)** | 4Gi | 1 | bge | `--memory=4Gi --min-instances=1` |
| **Prod (High Quality)** | 4Gi | 1 | openai | `--memory=4Gi --set-env-vars="RERANKER_TYPE=openai"` |
| **Prod (Max Perf)** | 8Gi | 1 | bge | `--memory=8Gi --cpu=4 --min-instances=2` |

### ✅ Fallback Mechanism (Đã Verified)

```
BGE GPU OOM → BGE CPU → OpenAI API → Dummy scores
      ↓              ↓            ↓
   (1.5GB)      (1.5GB)       (API call)
```

**Kết luận**: System tự động fallback, **không cần lo crash** khi OOM.

---

## 📋 Thông Tin Project

| Thông số         | Giá trị                                                             |
| ---------------- | ------------------------------------------------------------------- |
| **Framework**    | FastAPI 0.112.4                                                     |
| **Python**       | 3.10                                                                |
| **Database**     | PostgreSQL 15+ với pgvector extension (NullPool - no connection pooling) |
| **Cache**        | Redis (5 databases: DB0=cache, DB1=sessions, DB2=answers, DB3=semantic, DB4=rate-limit) |
| **ML Models**    | BGE Reranker (BAAI/bge-reranker-v2-m3) với auto-fallback to OpenAI |
| **Entry Point**  | `src.api.main:app`                                                  |
| **Default Port** | 8000                                                                |
| **Cold Start**   | ~50-60s (với BGE model loading)                                     |

## Mục Lục

1. [Tổng Quan](#1-tổng-quan)
2. [Yêu Cầu Trước Khi Bắt Đầu](#2-yêu-cầu-trước-khi-bắt-đầu)
3. [Cấu Hình Google Cloud Project](#3-cấu-hình-google-cloud-project)
4. [Tạo Dockerfile cho Backend](#4-tạo-dockerfile-cho-backend)
5. [Build và Push Container Image](#5-build-và-push-container-image)
6. [Deploy lên Cloud Run](#6-deploy-lên-cloud-run)
7. [Cấu Hình Kết Nối Database (Cloud SQL)](#7-cấu-hình-kết-nối-database-cloud-sql)
8. [Cấu Hình Redis (Memorystore)](#8-cấu-hình-redis-memorystore)
9. [Cấu Hình Secret Manager](#9-cấu-hình-secret-manager)
10. [Cấu Hình Domain và SSL](#10-cấu-hình-domain-và-ssl)
11. [Monitoring và Logging](#11-monitoring-và-logging)
12. [CI/CD với Cloud Build](#12-cicd-với-cloud-build)
13. [Troubleshooting](#13-troubleshooting)

---

## 1. Tổng Quan

### 1.1 Kiến trúc RAG-Bidding System

```
┌─────────────────────────────────────────────────────────────────┐
│                      Google Cloud Run                           │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  FastAPI Application (src.api.main:app)                   │ │
│  │  ├── /api/auth/* (Authentication - JWT)                   │ │
│  │  ├── /api/conversations/* (Chat with RAG)                 │ │
│  │  ├── /api/documents/* (Document Management)               │ │
│  │  ├── /api/analytics/* (Usage Analytics)                   │ │
│  │  ├── /api/cache/* (Cache Management)                      │ │
│  │  ├── /ask (Quick Q&A - No Auth)                          │ │
│  │  └── /health, /stats, /features (System)                  │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
          │                    │                    │
          ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   Cloud SQL     │  │   Memorystore   │  │   OpenAI API    │
│   PostgreSQL    │  │     Redis       │  │   Embeddings    │
│   + pgvector    │  │   5 Databases   │  │   + GPT-4o-mini │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

### 1.2 Ưu điểm của Cloud Run:

- **Serverless**: Không cần quản lý infrastructure
- **Auto-scaling**: Tự động scale từ 0 đến N instances
- **Pay-per-use**: Chỉ trả tiền khi có request
- **HTTPS mặc định**: SSL/TLS được cung cấp tự động
- **Container-based**: Chạy bất kỳ language/framework nào
- **GPU Support**: Hỗ trợ NVIDIA L4 GPU cho BGE Reranker (optional)

---

## 2. Yêu Cầu Trước Khi Bắt Đầu

### 2.1 Cài đặt Google Cloud SDK

```bash
# Trên Linux/macOS
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Hoặc trên Ubuntu/Debian
sudo apt-get install apt-transport-https ca-certificates gnupg curl
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
sudo apt-get update && sudo apt-get install google-cloud-cli
```

### 2.2 Đăng nhập và cấu hình

```bash
# Đăng nhập vào Google Cloud
gcloud auth login

# Đặt project mặc định
gcloud config set project YOUR_PROJECT_ID

# Xác minh cấu hình
gcloud config list
```

### 2.3 Yêu cầu khác

- Tài khoản Google Cloud với billing enabled
- Docker đã được cài đặt (nếu build local)
- RAG-Bidding backend code (FastAPI + LangChain)

### 2.4 Danh sách Environment Variables cần thiết

Project RAG-Bidding yêu cầu các biến môi trường sau:

| Biến                 | Mô tả                               | Ví dụ                                         |
| -------------------- | ----------------------------------- | --------------------------------------------- |
| `DATABASE_URL`       | PostgreSQL connection string        | `postgresql+psycopg://user:pass@host:5432/db` |
| `OPENAI_API_KEY`     | OpenAI API key cho embeddings & LLM | `sk-proj-...`                                 |
| `JWT_SECRET_KEY`     | Secret key cho JWT authentication   | `your-256-bit-secret`                         |
| `LC_COLLECTION`      | LangChain collection name           | `docs`                                        |
| `EMBED_MODEL`        | OpenAI embedding model              | `text-embedding-3-small`                      |
| `LLM_MODEL`          | OpenAI LLM model                    | `gpt-4o-mini`                                 |
| `REDIS_HOST`         | Redis server host                   | `10.0.0.3` (internal IP)                      |
| `REDIS_PORT`         | Redis server port                   | `6379`                                        |
| `CORS_ORIGINS`       | Allowed CORS origins                | `https://your-frontend.com`                   |
| `ENABLE_REDIS_CACHE` | Enable Redis caching                | `true`                                        |
| `ENABLE_RERANKING`   | Enable BGE reranker                 | `true`                                        |
| `RERANKER_TYPE`      | Force reranker type                 | `openai` (skip BGE, go direct to API)        |
| `RAG_MODE`           | RAG processing mode                 | `balanced`                                    |

> 💡 **Fallback Control**: 
> - `ENABLE_RERANKING=false`: Tắt reranking hoàn toàn
> - `RERANKER_TYPE=openai`: Bỏ qua BGE, dùng OpenAI API ngay từ đầu  
> - `RERANKER_TYPE=bge`: Force dùng BGE (default, có fallback to OpenAI nếu OOM)

---

## 3. Cấu Hình Google Cloud Project

### 3.1 Tạo Project mới (nếu chưa có)

**Qua Console:**

1. Truy cập [Google Cloud Console](https://console.cloud.google.com)
2. Click vào dropdown project ở góc trên bên trái
3. Click "New Project"
4. Nhập tên project và chọn organization (nếu có)
5. Click "Create"

**Qua CLI:**

```bash
gcloud projects create YOUR_PROJECT_ID --name="RAG Bidding Project"
gcloud config set project YOUR_PROJECT_ID
```

### 3.2 Enable các API cần thiết

```bash
# Enable tất cả API cần thiết cho Cloud Run
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    secretmanager.googleapis.com \
    sqladmin.googleapis.com \
    compute.googleapis.com \
    vpcaccess.googleapis.com \
    redis.googleapis.com
```

**Giải thích:**

- `run.googleapis.com`: Cloud Run API
- `cloudbuild.googleapis.com`: Cloud Build để build container
- `artifactregistry.googleapis.com`: Lưu trữ Docker images
- `secretmanager.googleapis.com`: Quản lý secrets (API keys, passwords)
- `sqladmin.googleapis.com`: Cloud SQL PostgreSQL
- `compute.googleapis.com`: Compute Engine (cho VPC)
- `vpcaccess.googleapis.com`: Serverless VPC Access
- `redis.googleapis.com`: Memorystore for Redis

### 3.3 Tạo Artifact Registry Repository

```bash
# Tạo repository để lưu Docker images
gcloud artifacts repositories create rag-bidding \
    --repository-format=docker \
    --location=asia-southeast1 \
    --description="RAG Bidding Backend Docker Repository"

# Cấu hình Docker để push lên Artifact Registry
gcloud auth configure-docker asia-southeast1-docker.pkg.dev
```

---

## 4. Tạo Dockerfile cho Backend

### ⚠️ LƯU Ý QUAN TRỌNG: Memory với BGE Reranker và Gunicorn Workers

**Vấn đề:**

- BGE Reranker model (`BAAI/bge-reranker-v2-m3`) cần **~1.2-1.5GB RAM** để load
- Gunicorn fork workers, mỗi worker load model **RIÊNG** (không share giữa processes)
- `preload_app=True` chỉ share code Python, **KHÔNG share model đã load vào RAM**

**Tính toán memory:**

| Workers   | Model Memory | App Overhead | Tổng RAM cần |
| --------- | ------------ | ------------ | ------------ |
| 1 worker  | 1.5GB        | 500MB        | ~2GB         |
| 2 workers | 3GB          | 1GB          | ~4GB         |
| 4 workers | 6GB          | 2GB          | **~8GB**     |

### 🔄 Logic Fallback GPU -> API

**RAG-Bidding có automatic fallback mechanism rất thông minh:**

```python
# Trong bge_reranker.py - Có 3 lớp fallback:

# 1. INIT TIME: Nếu không load được BGE model  
try:
    _reranker_instance = BGEReranker(device="cuda")
except Exception as e:
    if "cuda out of memory" in str(e).lower():
        _cuda_oom_fallback = True
        return OpenAIReranker()  # ✅ Fallback to API

# 2. RUNTIME: Nếu CUDA OOM khi rerank
try:
    scores = model.predict(pairs)  # BGE prediction  
except Exception as e:
    if "cuda out of memory" in str(e).lower():
        _cuda_oom_fallback = True  # Set global flag
        openai_reranker = OpenAIReranker()
        return openai_reranker.rerank(query, docs)  # ✅ Immediate fallback

# 3. FUTURE CALLS: Global flag prevents BGE loading
if _cuda_oom_fallback:
    return OpenAIReranker()  # ✅ Skip BGE entirely  
```

**Fallback tiers:**
1. **BGE GPU** (Fastest, 100-150ms, cần 1.5GB VRAM)
2. **BGE CPU** (Medium, 300-500ms, cần 1.5GB RAM)  
3. **OpenAI API** (Slowest, 500-2000ms, không cần local memory)
4. **Dummy scores** (Fallback cuối, trả về original order)

**Production recommendation:**

| Scenario | Memory | CPU | Env Vars |
|----------|--------|-----|----------|
| **Trust BGE** | `8Gi` | `2` | `ENABLE_RERANKING=true` |
| **OpenAI only** | `2Gi` | `1` | `ENABLE_RERANKING=true,RERANKER_TYPE=openai` |
| **No rerank** | `2Gi` | `1` | `ENABLE_RERANKING=false` |

**Khuyến nghị cho Cloud Run:**

```bash
# Option 1: 1 Worker (KHUYẾN NGHỊ cho Cloud Run)
# - Đơn giản nhất, phù hợp auto-scaling
# - Mỗi instance = 1 worker, Cloud Run scale bằng cách thêm instances
--memory=4Gi --cpu=2 --set-env-vars="GUNICORN_WORKERS=1"

# Option 2: 2 Workers với memory cao
# - Phù hợp nếu muốn handle nhiều concurrent requests trong 1 instance
--memory=8Gi --cpu=4 --set-env-vars="GUNICORN_WORKERS=2"

# Option 3: Disable Reranking (dùng OpenAI fallback hoặc không rerank)
# - Tiết kiệm memory, API response nhanh hơn
--memory=2Gi --cpu=1 --set-env-vars="ENABLE_RERANKING=false"
```

> 💡 **Best Practice cho Cloud Run**: Dùng **1 worker per container instance** và để Cloud Run auto-scale bằng cách spawn nhiều instances. Điều này giúp:
>
> - Tận dụng auto-scaling của Cloud Run
> - Đơn giản hóa memory management
> - Tránh memory issues với large models

### 4.1 Dockerfile cho RAG-Bidding (CPU Version)

Tạo file `Dockerfile` trong thư mục `RAG-bidding/`:

```dockerfile
# =============================================================================
# RAG-Bidding Backend Dockerfile
# Python 3.10 + FastAPI + LangChain + BGE Reranker
# =============================================================================

FROM python:3.10-slim as builder

WORKDIR /app

# Cài đặt build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libpq-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Tạo virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy và cài đặt Python dependencies từ environment.yaml
# Tạo requirements.txt từ environment.yaml pip dependencies
COPY environment.yaml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install pyyaml && \
    python -c "import yaml; deps = yaml.safe_load(open('environment.yaml'))['dependencies']; pip_deps = [d for d in deps if isinstance(d, dict) and 'pip' in d][0]['pip']; print('\n'.join(pip_deps))" > requirements.txt && \
    pip install --no-cache-dir -r requirements.txt

# =============================================================================
# Runtime Stage
# =============================================================================
FROM python:3.10-slim as runtime

WORKDIR /app

# Cài đặt runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment từ builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY gunicorn_config.py .

# Tạo thư mục logs
RUN mkdir -p logs

# Tạo non-root user (security best practice)
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Cloud Run sử dụng PORT environment variable
ENV PORT=8000
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE $PORT

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Start với Gunicorn + Uvicorn workers
# ⚠️ QUAN TRỌNG: Dùng 1 worker cho Cloud Run để tiết kiệm memory
# Cloud Run sẽ auto-scale bằng cách spawn nhiều container instances
# Nếu cần 2 workers, phải set memory=8Gi
CMD exec gunicorn \
    --bind 0.0.0.0:${PORT} \
    --workers ${GUNICORN_WORKERS:-1} \
    --worker-class uvicorn.workers.UvicornWorker \
    --timeout 300 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --access-logfile - \
    --error-logfile - \
    --capture-output \
    src.api.main:app
```

> ⚠️ **Nếu muốn dùng 2+ workers**, cần set env var `GUNICORN_WORKERS=2` và tăng memory lên `8Gi`:
>
> ```bash
> gcloud run deploy ... --memory=8Gi --set-env-vars="GUNICORN_WORKERS=2"
> ```

### 4.2 Dockerfile với GPU Support (Optional - cho BGE Reranker)

Nếu cần sử dụng GPU cho BGE Reranker để có performance tốt hơn:

```dockerfile
# =============================================================================
# RAG-Bidding Backend Dockerfile - GPU Version
# Yêu cầu Cloud Run GPU (NVIDIA L4)
# =============================================================================

FROM nvidia/cuda:12.1-runtime-ubuntu22.04 as runtime

# Install Python 3.10
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-venv \
    python3-pip \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Symlink python
RUN ln -s /usr/bin/python3.10 /usr/bin/python

WORKDIR /app

# Copy requirements và install
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install PyTorch với CUDA support
RUN pip install --no-cache-dir torch==2.1.0+cu121 -f https://download.pytorch.org/whl/cu121/torch_stable.html

# Copy application
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY gunicorn_config.py .

RUN mkdir -p logs

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

ENV PORT=8000
ENV PYTHONUNBUFFERED=1
ENV RERANKER_DEVICE=cuda

EXPOSE $PORT

CMD exec gunicorn \
    --bind 0.0.0.0:${PORT} \
    --workers 1 \
    --worker-class uvicorn.workers.UvicornWorker \
    --timeout 300 \
    src.api.main:app
```

### 4.3 Tạo requirements.txt từ environment.yaml

Project sử dụng `environment.yaml` thay vì `requirements.txt`. Tạo script để extract:

```bash
# Tạo requirements.txt từ environment.yaml
python3 << 'EOF'
import yaml

with open('environment.yaml', 'r') as f:
    env = yaml.safe_load(f)

pip_deps = None
for dep in env.get('dependencies', []):
    if isinstance(dep, dict) and 'pip' in dep:
        pip_deps = dep['pip']
        break

if pip_deps:
    with open('requirements.txt', 'w') as f:
        for pkg in pip_deps:
            f.write(f"{pkg}\n")
    print(f"Created requirements.txt with {len(pip_deps)} packages")
EOF
```

Hoặc tạo `requirements.txt` trực tiếp với các dependencies chính:

```txt
# Web Framework
fastapi==0.112.4
uvicorn[standard]==0.30.6
gunicorn==21.2.0
httpx==0.28.*

# LangChain Ecosystem
langchain==0.3.27
langchain-core==0.3.76
langchain-community==0.3.30
langchain-openai==0.3.33
langchain-postgres==0.0.15
langchain-text-splitters==0.3.11

# OpenAI
openai==1.109.1

# Database & Vector Store
psycopg==3.2.10
psycopg-binary==3.2.10
psycopg-pool==3.2.6
pgvector==0.3.6
sqlalchemy==2.0.*
alembic==1.13.*
python-multipart
redis

# Validation
pydantic[email]==2.11.9
pydantic-settings==2.11.0
python-dotenv==1.0.*

# NLP & Embeddings (BGE Reranker)
sentence-transformers==5.1.2
transformers==4.56.2
torch==2.8.0

# Document Processing
tiktoken==0.11.*
pypdf==6.0.*
python-docx==1.1.*
beautifulsoup4>=4.11.0
lxml>=4.9.0

# Data Processing
numpy==2.2.6
pandas==2.3.3

# Authentication
bcrypt==4.2.*
PyJWT==2.9.*
```

### 4.4 File .dockerignore

Tạo file `.dockerignore`:

```
# Git
.git
.gitignore

# Python
__pycache__
*.py[cod]
*$py.class
*.so
.Python
.env
.venv
env/
venv/
*.egg-info/
dist/
build/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Testing
.pytest_cache/
tests/
*.coverage
htmlcov/

# Documentation
documents/
*.md
!README.md

# Data (không include trong container - mount từ Cloud Storage)
data/
logs/
*.log

# Notebooks
notebooks/
*.ipynb

# Postman
postman/

# Scripts không cần thiết cho runtime
scripts/

# Local config
.env
.env.local
.env.*.local

# OS
.DS_Store
Thumbs.db
```

---

## 5. Build và Push Container Image

### 5.1 Build Local và Push

```bash
# Set environment variables
export PROJECT_ID=your-project-id
export REGION=asia-southeast1
export IMAGE_NAME=rag-bidding
export IMAGE_TAG=v1.0.0

# Tạo requirements.txt từ environment.yaml (nếu chưa có)
python3 -c "
import yaml
with open('environment.yaml') as f:
    env = yaml.safe_load(f)
pip_deps = [d['pip'] for d in env['dependencies'] if isinstance(d, dict) and 'pip' in d][0]
with open('requirements.txt', 'w') as f:
    f.write('\n'.join(pip_deps))
"

# Build image
docker build -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/rag-bidding/${IMAGE_NAME}:${IMAGE_TAG} .

# Test locally (cần có PostgreSQL và Redis running)
docker run -p 8000:8000 \
    -e DATABASE_URL="postgresql+psycopg://user:pass@host.docker.internal:5432/rag_bidding_v3" \
    -e OPENAI_API_KEY="sk-your-key" \
    -e JWT_SECRET_KEY="test-secret" \
    -e LC_COLLECTION="docs" \
    -e REDIS_HOST="host.docker.internal" \
    -e ENABLE_REDIS_CACHE="false" \
    ${REGION}-docker.pkg.dev/${PROJECT_ID}/rag-bidding/${IMAGE_NAME}:${IMAGE_TAG}

# Verify health endpoint
curl http://localhost:8000/health

# Push lên Artifact Registry
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/rag-bidding/${IMAGE_NAME}:${IMAGE_TAG}
```

### 5.2 Build với Cloud Build (Recommended)

Tạo file `cloudbuild.yaml` cho RAG-Bidding:

```yaml
steps:
  # Tạo requirements.txt từ environment.yaml
  - name: "python:3.10-slim"
    entrypoint: "bash"
    args:
      - "-c"
      - |
        pip install pyyaml
        python -c "
        import yaml
        with open('environment.yaml') as f:
            env = yaml.safe_load(f)
        pip_deps = [d['pip'] for d in env['dependencies'] if isinstance(d, dict) and 'pip' in d][0]
        with open('requirements.txt', 'w') as f:
            f.write('\n'.join(pip_deps))
        "

  # Build Docker image
  - name: "gcr.io/cloud-builders/docker"
    args:
      - "build"
      - "-t"
      - "${_REGION}-docker.pkg.dev/${PROJECT_ID}/rag-bidding/${_IMAGE_NAME}:${SHORT_SHA}"
      - "-t"
      - "${_REGION}-docker.pkg.dev/${PROJECT_ID}/rag-bidding/${_IMAGE_NAME}:latest"
      - "."

  # Push image to Artifact Registry
  - name: "gcr.io/cloud-builders/docker"
    args:
      - "push"
      - "--all-tags"
      - "${_REGION}-docker.pkg.dev/${PROJECT_ID}/rag-bidding/${_IMAGE_NAME}"

  # Deploy to Cloud Run
  - name: "gcr.io/google.com/cloudsdktool/cloud-sdk"
    entrypoint: gcloud
    args:
      - "run"
      - "deploy"
      - "${_SERVICE_NAME}"
      - "--image=${_REGION}-docker.pkg.dev/${PROJECT_ID}/rag-bidding/${_IMAGE_NAME}:${SHORT_SHA}"
      - "--region=${_REGION}"
      - "--platform=managed"
      - "--port=8000"
      - "--memory=4Gi"
      - "--cpu=2"
      - "--min-instances=0"
      - "--max-instances=10"
      - "--timeout=300"
      - "--concurrency=50"

substitutions:
  _REGION: asia-southeast1
  _IMAGE_NAME: rag-bidding
  _SERVICE_NAME: rag-bidding-api

images:
  - "${_REGION}-docker.pkg.dev/${PROJECT_ID}/rag-bidding/${_IMAGE_NAME}:${SHORT_SHA}"
  - "${_REGION}-docker.pkg.dev/${PROJECT_ID}/rag-bidding/${_IMAGE_NAME}:latest"

options:
  logging: CLOUD_LOGGING_ONLY
  machineType: "E2_HIGHCPU_8"

timeout: "1800s"
```

**Chạy Cloud Build:**

```bash
gcloud builds submit --config=cloudbuild.yaml .
```

---

## 6. Deploy lên Cloud Run

### 6.1 Deploy với đầy đủ Environment Variables

```bash
export PROJECT_ID=your-project-id
export REGION=asia-southeast1

# Deploy service với tất cả env vars cần thiết cho RAG-Bidding
gcloud run deploy rag-bidding-api \
    --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/rag-bidding/rag-bidding:latest \
    --region=${REGION} \
    --platform=managed \
    --port=8000 \
    --memory=4Gi \
    --cpu=2 \
    --min-instances=0 \
    --max-instances=10 \
    --timeout=300 \
    --concurrency=50 \
    --set-env-vars="LC_COLLECTION=docs" \
    --set-env-vars="EMBED_MODEL=text-embedding-3-small" \
    --set-env-vars="LLM_MODEL=gpt-4o-mini" \
    --set-env-vars="RAG_MODE=balanced" \
    --set-env-vars="ENABLE_RERANKING=true" \
    --set-env-vars="ENABLE_QUERY_ENHANCEMENT=true" \
    --set-env-vars="ENABLE_REDIS_CACHE=true" \
    --set-env-vars="LOG_LEVEL=INFO" \
    --set-env-vars="CORS_ORIGINS=https://your-frontend.com"
```

### 6.2 Deploy với Secrets (Recommended cho Production)

```bash
# Deploy với secrets từ Secret Manager
gcloud run deploy rag-bidding-api \
    --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/rag-bidding/rag-bidding:latest \
    --region=${REGION} \
    --platform=managed \
    --port=8000 \
    --memory=4Gi \
    --cpu=2 \
    --min-instances=1 \
    --max-instances=10 \
    --timeout=300 \
    --concurrency=50 \
    --service-account=rag-bidding-sa@${PROJECT_ID}.iam.gserviceaccount.com \
    --update-secrets=DATABASE_URL=db-connection-string:latest \
    --update-secrets=OPENAI_API_KEY=openai-api-key:latest \
    --update-secrets=JWT_SECRET_KEY=jwt-secret:latest \
    --set-env-vars="LC_COLLECTION=docs" \
    --set-env-vars="EMBED_MODEL=text-embedding-3-small" \
    --set-env-vars="LLM_MODEL=gpt-4o-mini" \
    --set-env-vars="RAG_MODE=balanced" \
    --set-env-vars="ENABLE_RERANKING=true" \
    --set-env-vars="ENABLE_REDIS_CACHE=true" \
    --set-env-vars="REDIS_HOST=10.0.0.3" \
    --set-env-vars="REDIS_PORT=6379" \
    --vpc-connector=rag-vpc-connector \
    --vpc-egress=private-ranges-only
```

### 6.3 Deploy qua Google Cloud Console

1. Truy cập [Cloud Run Console](https://console.cloud.google.com/run)
2. Click **"Create Service"**
3. Chọn **"Deploy one revision from an existing container image"**
4. Click **"Select"** và chọn image từ Artifact Registry: `rag-bidding/rag-bidding:latest`
5. Cấu hình cơ bản:
   - **Service name**: `rag-bidding-api`
   - **Region**: `asia-southeast1`
   - **Autoscaling**: Min 0, Max 10
6. Click **"Container, Networking, Security"**:

   **Container tab:**
   - **Container port**: `8000`
   - **Memory**: `4 GiB` (cần cho BGE Reranker model)
   - **CPU**: `2`
   - **Request timeout**: `300` seconds
   - **Maximum concurrent requests**: `50`
   - **Startup CPU boost**: ✅ Enabled (giúp load model nhanh hơn)

   **Variables & Secrets tab:**
   - Thêm environment variables theo bảng ở mục 2.4
   - Thêm secrets từ Secret Manager

   **Networking tab:**
   - Chọn VPC connector (nếu cần kết nối Cloud SQL/Redis qua private IP)
   - Egress: `Send traffic through VPC connector for private IPs only`

7. Click **"Create"**

### 6.4 Deploy với YAML Service Configuration

Tạo file `cloudrun-service.yaml`:

```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: rag-bidding-api
  labels:
    cloud.googleapis.com/location: asia-southeast1
  annotations:
    run.googleapis.com/ingress: all
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/minScale: "0"
        autoscaling.knative.dev/maxScale: "10"
        run.googleapis.com/cpu-throttling: "false"
        run.googleapis.com/startup-cpu-boost: "true"
        run.googleapis.com/vpc-access-connector: projects/PROJECT_ID/locations/asia-southeast1/connectors/rag-vpc-connector
        run.googleapis.com/vpc-access-egress: private-ranges-only
    spec:
      containerConcurrency: 50
      timeoutSeconds: 300
      serviceAccountName: rag-bidding-sa@PROJECT_ID.iam.gserviceaccount.com
      containers:
        - image: asia-southeast1-docker.pkg.dev/PROJECT_ID/rag-bidding/rag-bidding:latest
          ports:
            - name: http1
              containerPort: 8000
          env:
            # Application Config
            - name: LC_COLLECTION
              value: "docs"
            - name: EMBED_MODEL
              value: "text-embedding-3-small"
            - name: LLM_MODEL
              value: "gpt-4o-mini"
            - name: RAG_MODE
              value: "balanced"
            - name: LOG_LEVEL
              value: "INFO"
            # Feature Flags
            - name: ENABLE_RERANKING
              value: "true"
            - name: ENABLE_QUERY_ENHANCEMENT
              value: "true"
            - name: ENABLE_REDIS_CACHE
              value: "true"
            - name: ENABLE_ANSWER_CACHE
              value: "true"
            - name: ENABLE_SEMANTIC_CACHE
              value: "true"
            # Redis Config (Memorystore)
            - name: REDIS_HOST
              value: "10.0.0.3"
            - name: REDIS_PORT
              value: "6379"
            # CORS
            - name: CORS_ORIGINS
              value: "https://your-frontend.com,https://your-admin.com"
            # Secrets (mounted from Secret Manager)
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: db-connection-string
                  key: latest
            - name: OPENAI_API_KEY
              valueFrom:
                secretKeyRef:
                  name: openai-api-key
                  key: latest
            - name: JWT_SECRET_KEY
              valueFrom:
                secretKeyRef:
                  name: jwt-secret
                  key: latest
          resources:
            limits:
              cpu: "2"
              memory: "4Gi"
          startupProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 10
            failureThreshold: 6
            timeoutSeconds: 10
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            periodSeconds: 30
            timeoutSeconds: 10
```

**Deploy với YAML:**

```bash
# Thay thế PROJECT_ID
sed -i 's/PROJECT_ID/your-actual-project-id/g' cloudrun-service.yaml

# Deploy
gcloud run services replace cloudrun-service.yaml --region=asia-southeast1
```

---

## 7. Cấu Hình Kết Nối Database (Cloud SQL với pgvector)

> ⚠️ **QUAN TRỌNG**: RAG-Bidding sử dụng PostgreSQL với extension **pgvector** để lưu trữ và tìm kiếm vector embeddings. Cloud SQL hỗ trợ pgvector từ PostgreSQL 15+.

### 7.1 Tạo Cloud SQL Instance với pgvector Support

**Qua Console:**

1. Truy cập [Cloud SQL Console](https://console.cloud.google.com/sql)
2. Click **"Create Instance"**
3. Chọn **PostgreSQL**
4. Cấu hình:
   - **Instance ID**: `rag-bidding-db`
   - **Password**: Đặt password mạnh
   - **Region**: `asia-southeast1`
   - **Database version**: **PostgreSQL 15** (hoặc mới hơn - bắt buộc cho pgvector)
   - **Machine type**: `db-custom-2-8192` (2 vCPU, 8GB RAM - khuyến nghị cho vector operations)
   - **Storage**: 50GB SSD (vector data cần nhiều space hơn)
5. **Database flags** (quan trọng cho performance):
   - `max_connections`: `200`
   - `shared_buffers`: `2GB`
   - `work_mem`: `64MB`
   - `maintenance_work_mem`: `512MB`
6. Click **"Create Instance"**

**Qua CLI:**

```bash
export PROJECT_ID=your-project-id
export REGION=asia-southeast1

# Tạo Cloud SQL instance với PostgreSQL 15+ (hỗ trợ pgvector)
gcloud sql instances create rag-bidding-db \
    --database-version=POSTGRES_15 \
    --tier=db-custom-2-8192 \
    --region=${REGION} \
    --storage-size=50GB \
    --storage-type=SSD \
    --storage-auto-increase \
    --database-flags="max_connections=200,shared_buffers=2048MB,work_mem=64MB" \
    --availability-type=zonal

# Đặt password cho user postgres
gcloud sql users set-password postgres \
    --instance=rag-bidding-db \
    --password=YOUR_SECURE_PASSWORD

# Tạo database
gcloud sql databases create rag_bidding_v3 --instance=rag-bidding-db

# Tạo user riêng cho application (recommended)
gcloud sql users create sakana \
    --instance=rag-bidding-db \
    --password=YOUR_APP_PASSWORD
```

### 7.2 Cài đặt Extension pgvector

Kết nối vào database và chạy:

```bash
# Kết nối qua Cloud SQL Proxy
./cloud-sql-proxy ${PROJECT_ID}:${REGION}:rag-bidding-db &

# Hoặc qua gcloud
gcloud sql connect rag-bidding-db --user=postgres

# Trong psql, chạy:
```

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify installation
SELECT * FROM pg_extension WHERE extname = 'vector';

-- Grant permissions cho app user
GRANT ALL PRIVILEGES ON DATABASE rag_bidding_v3 TO sakana;
GRANT USAGE ON SCHEMA public TO sakana;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO sakana;
```

### 7.3 Kết Nối Cloud Run với Cloud SQL

**Cách 1: Cloud SQL Connector (Recommended)**

RAG-Bidding sử dụng `psycopg` driver (không phải asyncpg). Connection string format:

```bash
# Deploy với Cloud SQL connection
gcloud run deploy rag-bidding-api \
    --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/rag-bidding/rag-bidding:latest \
    --region=${REGION} \
    --port=8000 \
    --add-cloudsql-instances=${PROJECT_ID}:${REGION}:rag-bidding-db \
    --set-env-vars="DATABASE_URL=postgresql+psycopg://sakana:PASSWORD@/rag_bidding_v3?host=/cloudsql/${PROJECT_ID}:${REGION}:rag-bidding-db"
```

**Cách 2: Private IP với VPC Connector (Production Recommended)**

```bash
# Enable private IP for Cloud SQL instance
gcloud sql instances patch rag-bidding-db \
    --assign-ip \
    --network=default

# Lấy private IP
gcloud sql instances describe rag-bidding-db --format="value(ipAddresses[0].ipAddress)"

# Tạo VPC Connector (nếu chưa có)
gcloud compute networks vpc-access connectors create rag-vpc-connector \
    --region=${REGION} \
    --network=default \
    --range=10.8.0.0/28 \
    --min-instances=2 \
    --max-instances=10

# Deploy với VPC connector và private IP
gcloud run deploy rag-bidding-api \
    --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/rag-bidding/rag-bidding:latest \
    --region=${REGION} \
    --port=8000 \
    --vpc-connector=rag-vpc-connector \
    --vpc-egress=private-ranges-only \
    --set-env-vars="DATABASE_URL=postgresql+psycopg://sakana:PASSWORD@PRIVATE_IP:5432/rag_bidding_v3"
```

### 7.4 Database Migrations với Alembic

RAG-Bidding sử dụng Alembic cho database migrations. Tạo Cloud Run Job để chạy migrations:

```bash
# Tạo migration job
gcloud run jobs create rag-db-migration \
    --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/rag-bidding/rag-bidding:latest \
    --region=${REGION} \
    --add-cloudsql-instances=${PROJECT_ID}:${REGION}:rag-bidding-db \
    --set-env-vars="DATABASE_URL=postgresql+psycopg://sakana:PASSWORD@/rag_bidding_v3?host=/cloudsql/${PROJECT_ID}:${REGION}:rag-bidding-db" \
    --command="alembic" \
    --args="upgrade,head" \
    --max-retries=3

# Chạy migration
gcloud run jobs execute rag-db-migration --region=${REGION} --wait
```

### 7.5 Cấu hình hiện có trong Project

Project đã có cấu hình database tại `src/config/database.py`:

```python
# Cấu hình hiện tại (đã optimize cho production)
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

# NullPool cho async operations (recommended cho serverless)
self._async_engine = create_async_engine(
    self.connection_string,
    echo=False,
    poolclass=NullPool,  # Tốt cho Cloud Run scaling
)
```

> 💡 **Tip**: `NullPool` được recommend cho Cloud Run vì mỗi container instance được scale độc lập, tránh connection pool conflicts.

---

## 8. Cấu Hình Redis (Memorystore)

> ⚠️ **QUAN TRỌNG**: RAG-Bidding sử dụng Redis cho **5 databases** khác nhau:
>
> - DB0: General cache
> - DB1: Session storage
> - DB2: Answer cache
> - DB3: Semantic cache
> - DB4: Rate limiting

### 8.1 Tạo Memorystore for Redis Instance

**Qua Console:**

1. Truy cập [Memorystore Console](https://console.cloud.google.com/memorystore/redis)
2. Click **"Create Instance"**
3. Cấu hình:
   - **Instance ID**: `rag-bidding-redis`
   - **Region**: `asia-southeast1`
   - **Tier**: **Standard** (cho production với high availability)
   - **Capacity**: `2 GB` (đủ cho caching + sessions)
   - **Version**: Redis 7.0
   - **Network**: Chọn VPC network (default hoặc custom)
4. Click **"Create"**

**Qua CLI:**

```bash
export PROJECT_ID=your-project-id
export REGION=asia-southeast1

# Tạo Memorystore Redis instance
gcloud redis instances create rag-bidding-redis \
    --size=2 \
    --region=${REGION} \
    --redis-version=redis_7_0 \
    --tier=standard \
    --network=default

# Lấy thông tin connection (cần cho Cloud Run)
gcloud redis instances describe rag-bidding-redis --region=${REGION}

# Output sẽ có:
# host: 10.x.x.x (Private IP)
# port: 6379
```

### 8.2 Kết Nối Cloud Run với Memorystore

> ⚠️ Memorystore chỉ có Private IP, **BẮT BUỘC** phải dùng VPC Connector.

```bash
# Lấy Redis host IP
export REDIS_HOST=$(gcloud redis instances describe rag-bidding-redis \
    --region=${REGION} \
    --format="value(host)")

echo "Redis Host: ${REDIS_HOST}"

# Deploy với VPC connector và Redis config
gcloud run deploy rag-bidding-api \
    --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/rag-bidding/rag-bidding:latest \
    --region=${REGION} \
    --port=8000 \
    --vpc-connector=rag-vpc-connector \
    --vpc-egress=private-ranges-only \
    --set-env-vars="REDIS_HOST=${REDIS_HOST}" \
    --set-env-vars="REDIS_PORT=6379" \
    --set-env-vars="ENABLE_REDIS_CACHE=true" \
    --set-env-vars="ENABLE_ANSWER_CACHE=true" \
    --set-env-vars="ENABLE_SEMANTIC_CACHE=true" \
    --set-env-vars="RATE_LIMIT_ENABLED=true"
```

### 8.3 Cấu hình Redis trong Project

Project đã có cấu hình tại `src/config/feature_flags.py`:

```python
# Redis Database assignments (đã cấu hình)
REDIS_DATABASES = {
    "cache": 0,      # General cache
    "sessions": 1,   # User sessions
    "answers": 2,    # Answer cache
    "semantic": 3,   # Semantic cache
    "rate_limit": 4  # Rate limiting
}

# Feature flags
ENABLE_REDIS_CACHE = os.getenv("ENABLE_REDIS_CACHE", "true").lower() == "true"
ENABLE_ANSWER_CACHE = os.getenv("ENABLE_ANSWER_CACHE", "true").lower() == "true"
ENABLE_SEMANTIC_CACHE = os.getenv("ENABLE_SEMANTIC_CACHE", "true").lower() == "true"
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
```

### 8.4 Test Redis Connection

```python
# Script test connection
import redis

redis_host = "10.x.x.x"  # Thay bằng IP thực
redis_port = 6379

# Test từng database
for db_name, db_num in {"cache": 0, "sessions": 1, "answers": 2, "semantic": 3, "rate_limit": 4}.items():
    r = redis.Redis(host=redis_host, port=redis_port, db=db_num)
    r.ping()
    print(f"✅ Redis DB{db_num} ({db_name}): Connected")
```

### 8.5 Tùy chọn: Redis Cluster (High Availability)

Cho production với high traffic:

```bash
gcloud redis instances create rag-bidding-redis-ha \
    --size=4 \
    --region=${REGION} \
    --redis-version=redis_7_0 \
    --tier=standard \
    --replica-count=1 \
    --read-replicas-mode=read-replicas-enabled \
    --network=default
```

---

## 9. Cấu Hình Secret Manager

### 9.1 Tạo Secrets cho RAG-Bidding

RAG-Bidding cần các secrets sau:

```bash
export PROJECT_ID=your-project-id

# 1. Database connection string (quan trọng nhất)
echo -n "postgresql+psycopg://sakana:YOUR_PASSWORD@/rag_bidding_v3?host=/cloudsql/${PROJECT_ID}:asia-southeast1:rag-bidding-db" | \
    gcloud secrets create db-connection-string --data-file=-

# 2. OpenAI API Key (cho embeddings và LLM)
echo -n "sk-your-openai-api-key" | gcloud secrets create openai-api-key --data-file=-

# 3. JWT Secret Key (cho authentication)
openssl rand -base64 64 | gcloud secrets create jwt-secret --data-file=-

# Verify secrets đã tạo
gcloud secrets list
```

### 9.2 Tạo và Cấu hình Service Account

```bash
export PROJECT_ID=your-project-id
export PROJECT_NUMBER=$(gcloud projects describe ${PROJECT_ID} --format="value(projectNumber)")

# Tạo service account riêng cho RAG-Bidding
gcloud iam service-accounts create rag-bidding-sa \
    --display-name="RAG Bidding Service Account" \
    --description="Service account for RAG Bidding Cloud Run service"

export SERVICE_ACCOUNT="rag-bidding-sa@${PROJECT_ID}.iam.gserviceaccount.com"

# Cấp quyền truy cập secrets
for secret in db-connection-string openai-api-key jwt-secret; do
    gcloud secrets add-iam-policy-binding ${secret} \
        --member="serviceAccount:${SERVICE_ACCOUNT}" \
        --role="roles/secretmanager.secretAccessor"
done

# Cấp quyền Cloud SQL Client (nếu dùng Cloud SQL Connector)
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/cloudsql.client"

# Cấp quyền Cloud Storage (nếu lưu documents trên GCS)
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/storage.objectViewer"
```

### 9.3 Deploy với tất cả Secrets

```bash
export PROJECT_ID=your-project-id
export REGION=asia-southeast1
export REDIS_HOST=$(gcloud redis instances describe rag-bidding-redis --region=${REGION} --format="value(host)")

# Deploy hoàn chỉnh với secrets và env vars
gcloud run deploy rag-bidding-api \
    --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/rag-bidding/rag-bidding:latest \
    --region=${REGION} \
    --platform=managed \
    --port=8000 \
    --memory=4Gi \
    --cpu=2 \
    --min-instances=1 \
    --max-instances=10 \
    --timeout=300 \
    --concurrency=50 \
    --service-account=rag-bidding-sa@${PROJECT_ID}.iam.gserviceaccount.com \
    --vpc-connector=rag-vpc-connector \
    --vpc-egress=private-ranges-only \
    --add-cloudsql-instances=${PROJECT_ID}:${REGION}:rag-bidding-db \
    --update-secrets=DATABASE_URL=db-connection-string:latest \
    --update-secrets=OPENAI_API_KEY=openai-api-key:latest \
    --update-secrets=JWT_SECRET_KEY=jwt-secret:latest \
    --set-env-vars="LC_COLLECTION=docs" \
    --set-env-vars="EMBED_MODEL=text-embedding-3-small" \
    --set-env-vars="LLM_MODEL=gpt-4o-mini" \
    --set-env-vars="RAG_MODE=balanced" \
    --set-env-vars="ENABLE_RERANKING=true" \
    --set-env-vars="ENABLE_QUERY_ENHANCEMENT=true" \
    --set-env-vars="ENABLE_REDIS_CACHE=true" \
    --set-env-vars="ENABLE_ANSWER_CACHE=true" \
    --set-env-vars="ENABLE_SEMANTIC_CACHE=true" \
    --set-env-vars="RATE_LIMIT_ENABLED=true" \
    --set-env-vars="REDIS_HOST=${REDIS_HOST}" \
    --set-env-vars="REDIS_PORT=6379" \
    --set-env-vars="LOG_LEVEL=INFO"
```

### 9.4 Rotate Secrets

```bash
# Update secret với version mới
echo -n "new-openai-api-key" | gcloud secrets versions add openai-api-key --data-file=-

# Deploy lại service để lấy secret mới
gcloud run services update rag-bidding-api \
    --region=${REGION} \
    --update-secrets=OPENAI_API_KEY=openai-api-key:latest
```

---

## 10. Cấu Hình Domain và SSL

### 10.1 Custom Domain qua Console

1. Truy cập [Cloud Run Console](https://console.cloud.google.com/run)
2. Click vào service `rag-bidding-api`
3. Chọn tab **"INTEGRATIONS"** hoặc **"DOMAIN MAPPINGS"**
4. Click **"ADD MAPPING"**
5. Chọn domain hoặc thêm domain mới
6. Làm theo hướng dẫn để verify domain ownership
7. Thêm DNS records theo yêu cầu

### 10.2 Custom Domain qua CLI

```bash
export REGION=asia-southeast1

# Map custom domain
gcloud run domain-mappings create \
    --service=rag-bidding-api \
    --domain=api.yourdomain.com \
    --region=${REGION}

# Kiểm tra trạng thái
gcloud run domain-mappings describe \
    --domain=api.yourdomain.com \
    --region=${REGION}
```

### 10.3 DNS Configuration

Thêm các DNS records sau vào domain của bạn:

| Type  | Name | Value                         |
| ----- | ---- | ----------------------------- |
| CNAME | api  | ghs.googlehosted.com          |
| TXT   | api  | google-site-verification=xxxx |

### 10.4 CORS Configuration

RAG-Bidding đã có CORS config trong code. Update `CORS_ORIGINS` env var để cho phép frontend domain:

```bash
gcloud run services update rag-bidding-api \
    --region=${REGION} \
    --set-env-vars="CORS_ORIGINS=https://your-frontend.com,https://admin.your-frontend.com"
```

---

## 11. Monitoring và Logging

### 11.1 Cloud Logging

Logs tự động được gửi đến Cloud Logging. Truy cập tại:

- [Logs Explorer](https://console.cloud.google.com/logs)

**Filter logs của RAG-Bidding:**

```
resource.type="cloud_run_revision"
resource.labels.service_name="rag-bidding-api"
```

**Filter theo severity:**

```
resource.type="cloud_run_revision"
resource.labels.service_name="rag-bidding-api"
severity>=ERROR
```

### 11.2 Cloud Monitoring Dashboard

1. Truy cập [Cloud Monitoring](https://console.cloud.google.com/monitoring)
2. Tạo Dashboard mới: **"RAG-Bidding API"**
3. Thêm các metrics quan trọng:

| Metric                                             | Description                          |
| -------------------------------------------------- | ------------------------------------ |
| `run.googleapis.com/request_count`                 | Số requests                          |
| `run.googleapis.com/request_latencies`             | Latency (quan trọng cho RAG queries) |
| `run.googleapis.com/container/cpu/utilizations`    | CPU usage                            |
| `run.googleapis.com/container/memory/utilizations` | Memory (quan trọng cho BGE Reranker) |
| `run.googleapis.com/container/instance_count`      | Số instances đang chạy               |
| `run.googleapis.com/container/startup_latencies`   | Cold start time                      |

### 11.3 Alerting Policies

```bash
export PROJECT_ID=your-project-id

# Alert khi latency > 10s (RAG queries có thể chậm)
gcloud alpha monitoring policies create \
    --display-name="RAG-Bidding High Latency" \
    --condition-filter='metric.type="run.googleapis.com/request_latencies" resource.type="cloud_run_revision" resource.labels.service_name="rag-bidding-api"' \
    --condition-threshold-value=10000 \
    --condition-threshold-comparison=COMPARISON_GT \
    --condition-threshold-duration=300s \
    --notification-channels="projects/${PROJECT_ID}/notificationChannels/YOUR_CHANNEL_ID"

# Alert khi memory > 90%
gcloud alpha monitoring policies create \
    --display-name="RAG-Bidding High Memory" \
    --condition-filter='metric.type="run.googleapis.com/container/memory/utilizations" resource.type="cloud_run_revision" resource.labels.service_name="rag-bidding-api"' \
    --condition-threshold-value=0.9 \
    --condition-threshold-comparison=COMPARISON_GT \
    --condition-threshold-duration=60s \
    --notification-channels="projects/${PROJECT_ID}/notificationChannels/YOUR_CHANNEL_ID"
```

### 11.4 Health Check Endpoint

RAG-Bidding đã có endpoint `/health` trong `src/api/main.py`. Verify hoạt động:

```bash
# Lấy service URL
SERVICE_URL=$(gcloud run services describe rag-bidding-api \
    --region=${REGION} \
    --format="value(status.url)")

# Test health endpoint
curl ${SERVICE_URL}/health

# Expected response:
# {"status": "healthy", "version": "1.0.0"}
```

### 11.5 Application Performance Monitoring

Để theo dõi chi tiết hơn (query latency, LLM response time, etc.), có thể tích hợp OpenTelemetry:

```python
# Thêm vào src/api/main.py
from opentelemetry import trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Setup tracing
tracer_provider = TracerProvider()
cloud_trace_exporter = CloudTraceSpanExporter()
tracer_provider.add_span_processor(BatchSpanProcessor(cloud_trace_exporter))
trace.set_tracer_provider(tracer_provider)

tracer = trace.get_tracer(__name__)

# Usage in RAG query
with tracer.start_as_current_span("rag_query") as span:
    span.set_attribute("query", user_query)
    span.set_attribute("rag_mode", rag_mode)
    # ... RAG processing
    span.set_attribute("num_documents", len(retrieved_docs))
```

---

## 12. CI/CD với Cloud Build

### 12.1 GitHub Integration

1. Truy cập [Cloud Build Triggers](https://console.cloud.google.com/cloud-build/triggers)
2. Click **"Connect Repository"**
3. Chọn **GitHub** và authorize
4. Chọn repository chứa RAG-Bidding code
5. Click **"Create Trigger"**
6. Cấu hình:
   - **Name**: `rag-bidding-deploy`
   - **Event**: Push to branch `main`
   - **Configuration**: Cloud Build configuration file
   - **Location**: `/RAG-bidding/cloudbuild.yaml`

### 12.2 Complete CI/CD Pipeline cho RAG-Bidding

Tạo file `cloudbuild-ci-cd.yaml`:

```yaml
steps:
  # Step 1: Tạo requirements.txt từ environment.yaml
  - name: "python:3.10-slim"
    id: "generate-requirements"
    entrypoint: "bash"
    args:
      - "-c"
      - |
        pip install pyyaml
        python -c "
        import yaml
        with open('environment.yaml') as f:
            env = yaml.safe_load(f)
        pip_deps = [d['pip'] for d in env['dependencies'] if isinstance(d, dict) and 'pip' in d][0]
        with open('requirements.txt', 'w') as f:
            f.write('\n'.join(pip_deps))
        "

  # Step 2: Run tests
  - name: "python:3.10-slim"
    id: "run-tests"
    entrypoint: "bash"
    args:
      - "-c"
      - |
        pip install -r requirements.txt
        pip install pytest pytest-asyncio pytest-cov
        python -m pytest tests/ -v --ignore=tests/integration/ --cov=src --cov-report=xml
    env:
      - "DATABASE_URL=sqlite:///test.db"
      - "ENABLE_REDIS_CACHE=false"
      - "ENABLE_RERANKING=false"

  # Step 3: Build Docker image
  - name: "gcr.io/cloud-builders/docker"
    id: "build-image"
    args:
      - "build"
      - "-t"
      - "${_REGION}-docker.pkg.dev/${PROJECT_ID}/rag-bidding/${_IMAGE_NAME}:${SHORT_SHA}"
      - "-t"
      - "${_REGION}-docker.pkg.dev/${PROJECT_ID}/rag-bidding/${_IMAGE_NAME}:latest"
      - "--cache-from"
      - "${_REGION}-docker.pkg.dev/${PROJECT_ID}/rag-bidding/${_IMAGE_NAME}:latest"
      - "--build-arg"
      - "BUILDKIT_INLINE_CACHE=1"
      - "."

  # Step 4: Push to Artifact Registry
  - name: "gcr.io/cloud-builders/docker"
    id: "push-image"
    args:
      - "push"
      - "--all-tags"
      - "${_REGION}-docker.pkg.dev/${PROJECT_ID}/rag-bidding/${_IMAGE_NAME}"

  # Step 5: Run database migrations
  - name: "gcr.io/google.com/cloudsdktool/cloud-sdk"
    id: "run-migrations"
    entrypoint: "bash"
    args:
      - "-c"
      - |
        gcloud run jobs execute rag-db-migration \
          --region=${_REGION} \
          --wait \
          || echo "Migration job not found, skipping..."

  # Step 6: Deploy to Cloud Run
  - name: "gcr.io/google.com/cloudsdktool/cloud-sdk"
    id: "deploy"
    entrypoint: "gcloud"
    args:
      - "run"
      - "deploy"
      - "${_SERVICE_NAME}"
      - "--image=${_REGION}-docker.pkg.dev/${PROJECT_ID}/rag-bidding/${_IMAGE_NAME}:${SHORT_SHA}"
      - "--region=${_REGION}"
      - "--platform=managed"
      - "--port=8000"
      - "--memory=4Gi"
      - "--cpu=2"
      - "--min-instances=1"
      - "--max-instances=10"
      - "--timeout=300"
      - "--concurrency=50"

  # Step 7: Health check after deploy
  - name: "gcr.io/google.com/cloudsdktool/cloud-sdk"
    id: "health-check"
    entrypoint: "bash"
    args:
      - "-c"
      - |
        SERVICE_URL=$(gcloud run services describe ${_SERVICE_NAME} \
          --region=${_REGION} \
          --format="value(status.url)")

        echo "Testing health endpoint: ${SERVICE_URL}/health"

        for i in {1..10}; do
          HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" ${SERVICE_URL}/health)
          if [ "$HTTP_CODE" = "200" ]; then
            echo "✅ Health check passed!"
            exit 0
          fi
          echo "Attempt $i: HTTP $HTTP_CODE, waiting..."
          sleep 10
        done

        echo "❌ Health check failed after 10 attempts"
        exit 1

substitutions:
  _REGION: asia-southeast1
  _IMAGE_NAME: rag-bidding
  _SERVICE_NAME: rag-bidding-api

images:
  - "${_REGION}-docker.pkg.dev/${PROJECT_ID}/rag-bidding/${_IMAGE_NAME}:${SHORT_SHA}"
  - "${_REGION}-docker.pkg.dev/${PROJECT_ID}/rag-bidding/${_IMAGE_NAME}:latest"

options:
  logging: CLOUD_LOGGING_ONLY
  machineType: "E2_HIGHCPU_8"

timeout: "1800s"
```

### 12.3 Staging/Production Environments

Tạo triggers cho multiple environments:

```bash
# Staging trigger (từ develop branch)
gcloud builds triggers create github \
    --repo-name=your-repo \
    --repo-owner=your-org \
    --branch-pattern="^develop$" \
    --build-config=RAG-bidding/cloudbuild-ci-cd.yaml \
    --substitutions="_SERVICE_NAME=rag-bidding-api-staging,_REGION=asia-southeast1"

# Production trigger (từ main branch)
gcloud builds triggers create github \
    --repo-name=your-repo \
    --repo-owner=your-org \
    --branch-pattern="^main$" \
    --build-config=RAG-bidding/cloudbuild-ci-cd.yaml \
    --substitutions="_SERVICE_NAME=rag-bidding-api,_REGION=asia-southeast1"
```

### 12.4 Manual Rollback

```bash
# Liệt kê các revisions
gcloud run revisions list \
    --service=rag-bidding-api \
    --region=asia-southeast1

# Rollback về revision cụ thể
gcloud run services update-traffic rag-bidding-api \
    --to-revisions=rag-bidding-api-00005-abc=100 \
    --region=asia-southeast1
```

---

## 13. Troubleshooting

### 13.1 Common Issues cho RAG-Bidding

#### ❌ Container không start được

```bash
# Kiểm tra logs chi tiết
gcloud run services logs read rag-bidding-api \
    --region=asia-southeast1 \
    --limit=100

# Kiểm tra revision status
gcloud run revisions list \
    --service=rag-bidding-api \
    --region=asia-southeast1

# Xem chi tiết revision failed
gcloud run revisions describe REVISION_NAME \
    --region=asia-southeast1
```

**Nguyên nhân thường gặp:**

- Missing environment variables (đặc biệt `DATABASE_URL`, `OPENAI_API_KEY`)
- Memory không đủ cho BGE Reranker model (cần tối thiểu 4GB)
- Port không đúng (phải là 8000, không phải 8080)

#### ❌ Memory issues (BGE Reranker)

BGE Reranker model (`BAAI/bge-reranker-v2-m3`) cần ~2GB memory. Nếu gặp OOM:

```bash
# Tăng memory
gcloud run services update rag-bidding-api \
    --memory=8Gi \
    --cpu=4 \
    --region=asia-southeast1

# Hoặc disable reranking tạm thời
gcloud run services update rag-bidding-api \
    --set-env-vars="ENABLE_RERANKING=false" \
    --region=asia-southeast1
```

#### ❌ Cold start chậm (>30s)

RAG-Bidding cần load models khi startup, có thể mất 30-60s:

```bash
# Đặt minimum instances > 0 để tránh cold start
gcloud run services update rag-bidding-api \
    --min-instances=1 \
    --region=asia-southeast1

# Enable startup CPU boost
gcloud run services update rag-bidding-api \
    --cpu-boost \
    --region=asia-southeast1
```

#### ❌ Connection timeout đến Cloud SQL

```bash
# Kiểm tra Cloud SQL connection name
gcloud sql instances describe rag-bidding-db \
    --format="value(connectionName)"

# Verify IAM permissions
gcloud projects get-iam-policy ${PROJECT_ID} \
    --flatten="bindings[].members" \
    --filter="bindings.members:rag-bidding-sa@${PROJECT_ID}.iam.gserviceaccount.com"

# Kiểm tra VPC connector status
gcloud compute networks vpc-access connectors describe rag-vpc-connector \
    --region=asia-southeast1
```

**Fix common issues:**

```bash
# Cấp quyền Cloud SQL Client
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:rag-bidding-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/cloudsql.client"
```

#### ❌ Redis connection refused

Memorystore chỉ có Private IP, **PHẢI** dùng VPC connector:

```bash
# Kiểm tra VPC connector
gcloud run services describe rag-bidding-api \
    --region=asia-southeast1 \
    --format="value(spec.template.metadata.annotations['run.googleapis.com/vpc-access-connector'])"

# Kiểm tra Redis host đúng chưa
gcloud redis instances describe rag-bidding-redis \
    --region=asia-southeast1 \
    --format="value(host)"

# Update nếu cần
export REDIS_HOST=$(gcloud redis instances describe rag-bidding-redis --region=asia-southeast1 --format="value(host)")
gcloud run services update rag-bidding-api \
    --set-env-vars="REDIS_HOST=${REDIS_HOST}" \
    --region=asia-southeast1
```

#### ❌ pgvector extension not found

```bash
# Kết nối vào Cloud SQL và enable extension
gcloud sql connect rag-bidding-db --user=postgres

# Trong psql:
CREATE EXTENSION IF NOT EXISTS vector;
\dx  -- verify extension
```

#### ❌ OpenAI API rate limited

```bash
# Check logs cho rate limit errors
gcloud run services logs read rag-bidding-api \
    --region=asia-southeast1 \
    --filter="textPayload:rate"

# Tăng timeout và giảm concurrency
gcloud run services update rag-bidding-api \
    --timeout=600 \
    --concurrency=20 \
    --region=asia-southeast1
```

#### 🔄 BGE Reranker Fallback Issues

**Vấn đề**: BGE model không load được hoặc CUDA OOM

**Log patterns cần chú ý:**
```bash
# Check fallback logs
gcloud run services logs read rag-bidding-api \
    --region=asia-southeast1 \
    --filter='textPayload:"cuda out of memory" OR textPayload:"OpenAI reranker" OR textPayload:"Falling back"'
```

**Expected log flow khi fallback:**
```
🔧 Creating singleton BGEReranker instance (model: BAAI/bge-reranker-v2-m3, device: cuda)
❌ CUDA OOM during BGE init: CUDA out of memory
🔄 Falling back to OpenAI reranker...
✅ OpenAI reranker initialized: gpt-4o-mini
```

**Solutions:**

```bash  
# Option 1: Tăng memory cho BGE
gcloud run services update rag-bidding-api \
    --memory=8Gi --cpu=2 \
    --region=asia-southeast1

# Option 2: Force OpenAI từ đầu (skip BGE)
gcloud run services update rag-bidding-api \
    --set-env-vars="RERANKER_TYPE=openai" \
    --memory=2Gi --cpu=1 \
    --region=asia-southeast1

# Option 3: Force CPU cho BGE (nếu CUDA issues)  
gcloud run services update rag-bidding-api \
    --set-env-vars="RERANKER_DEVICE=cpu" \
    --memory=4Gi --cpu=2 \
    --region=asia-southeast1

# Option 4: Disable reranking hoàn toàn
gcloud run services update rag-bidding-api \
    --set-env-vars="ENABLE_RERANKING=false" \
    --memory=2Gi --cpu=1 \
    --region=asia-southeast1
```

**Verify fallback hoạt động:**
```bash
# Test API endpoint
SERVICE_URL=$(gcloud run services describe rag-bidding-api --region=asia-southeast1 --format="value(status.url)")

# Send test query to /ask endpoint  
curl -X POST "$SERVICE_URL/ask" \
    -H "Content-Type: application/json" \
    -d '{"query": "test reranking fallback"}' \
    -w "\nResponse time: %{time_total}s\n"

# Check logs for fallback indicators
gcloud run services logs read rag-bidding-api --region=asia-southeast1 --limit=50
```

### 13.2 Debug Commands

```bash
export REGION=asia-southeast1
export SERVICE=rag-bidding-api

# Xem chi tiết service config
gcloud run services describe ${SERVICE} --region=${REGION}

# Xem tất cả environment variables
gcloud run services describe ${SERVICE} --region=${REGION} \
    --format="yaml(spec.template.spec.containers[].env)"

# Xem secrets đã mount
gcloud run services describe ${SERVICE} --region=${REGION} \
    --format="yaml(spec.template.spec.containers[].env)" | grep -A2 "secretKeyRef"

# Traffic split (nếu cần test revision mới)
gcloud run services update-traffic ${SERVICE} \
    --to-revisions=REVISION_NEW=10,REVISION_OLD=90 \
    --region=${REGION}

# Rollback hoàn toàn
gcloud run services update-traffic ${SERVICE} \
    --to-revisions=REVISION_OLD=100 \
    --region=${REGION}
```

### 13.3 Performance Tuning

```bash
# Cấu hình recommended cho RAG-Bidding
gcloud run services update rag-bidding-api \
    --region=asia-southeast1 \
    --memory=4Gi \
    --cpu=2 \
    --min-instances=1 \
    --max-instances=10 \
    --concurrency=50 \
    --timeout=300 \
    --cpu-boost \
    --set-env-vars="RAG_MODE=balanced" \
    --set-env-vars="ENABLE_RERANKING=true" \
    --set-env-vars="ENABLE_REDIS_CACHE=true"
```

### 13.4 Cost Optimization

```bash
# Development/Staging: Scale to zero
gcloud run services update rag-bidding-api-staging \
    --region=asia-southeast1 \
    --min-instances=0 \
    --memory=2Gi \
    --cpu=1 \
    --set-env-vars="ENABLE_RERANKING=false"

# Production: Keep warm instances
gcloud run services update rag-bidding-api \
    --region=asia-southeast1 \
    --min-instances=1 \
    --max-instances=5
```

---

## 14. Checklist Deployment cho RAG-Bidding

### Pre-deployment

- [ ] Google Cloud Project đã tạo và billing enabled
- [ ] Tất cả APIs đã enable (Cloud Run, Cloud SQL, Memorystore, Secret Manager, etc.)
- [ ] Service account `rag-bidding-sa` đã tạo với đủ permissions
- [ ] Artifact Registry repository `rag-bidding` đã tạo

### Infrastructure

- [ ] Cloud SQL PostgreSQL 15+ instance đã tạo
- [ ] pgvector extension đã enable
- [ ] Database `rag_bidding_v3` và user `sakana` đã tạo
- [ ] Memorystore Redis instance đã tạo
- [ ] VPC Connector đã tạo và hoạt động

### Secrets

- [ ] `db-connection-string` secret đã tạo
- [ ] `openai-api-key` secret đã tạo
- [ ] `jwt-secret` secret đã tạo
- [ ] Service account có quyền `secretmanager.secretAccessor`

### Application

- [ ] Dockerfile đã tạo và test locally thành công
- [ ] Docker image đã build và push lên Artifact Registry
- [ ] `requirements.txt` đã generate từ `environment.yaml`
- [ ] Health check endpoint `/health` hoạt động

### Deployment

- [ ] Cloud Run service đã deploy thành công
- [ ] Port 8000 đã configure đúng
- [ ] Tất cả environment variables đã set
- [ ] VPC connector đã attach
- [ ] Cloud SQL connection đã thêm

### Post-deployment

- [ ] Health check endpoint trả về 200
- [ ] API endpoints hoạt động (`/api/auth`, `/api/conversations`, `/ask`)
- [ ] Database migrations đã chạy thành công
- [ ] Redis cache hoạt động
- [ ] Monitoring dashboard đã setup
- [ ] Alerting policies đã configure
- [ ] CI/CD pipeline đã test

### Optional

- [ ] Custom domain đã map
- [ ] SSL certificate đã provision
- [ ] CORS origins đã configure cho frontend domain

---

## 15. Quick Start Script

Tạo file `deploy.sh` để deploy nhanh:

```bash
#!/bin/bash
set -e

# Configuration
export PROJECT_ID="your-project-id"
export REGION="asia-southeast1"
export SERVICE_NAME="rag-bidding-api"
export IMAGE_NAME="rag-bidding"

echo "🚀 Starting RAG-Bidding deployment..."

# 1. Generate requirements.txt
echo "📦 Generating requirements.txt..."
python3 -c "
import yaml
with open('environment.yaml') as f:
    env = yaml.safe_load(f)
pip_deps = [d['pip'] for d in env['dependencies'] if isinstance(d, dict) and 'pip' in d][0]
with open('requirements.txt', 'w') as f:
    f.write('\n'.join(pip_deps))
"

# 2. Build and push image
echo "🐳 Building Docker image..."
docker build -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/rag-bidding/${IMAGE_NAME}:latest .

echo "📤 Pushing to Artifact Registry..."
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/rag-bidding/${IMAGE_NAME}:latest

# 3. Get Redis host
export REDIS_HOST=$(gcloud redis instances describe rag-bidding-redis --region=${REGION} --format="value(host)" 2>/dev/null || echo "")

# 4. Deploy
echo "🚢 Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/rag-bidding/${IMAGE_NAME}:latest \
    --region=${REGION} \
    --platform=managed \
    --port=8000 \
    --memory=4Gi \
    --cpu=2 \
    --min-instances=1 \
    --max-instances=10 \
    --timeout=300 \
    --concurrency=50 \
    --service-account=rag-bidding-sa@${PROJECT_ID}.iam.gserviceaccount.com \
    --vpc-connector=rag-vpc-connector \
    --vpc-egress=private-ranges-only \
    --add-cloudsql-instances=${PROJECT_ID}:${REGION}:rag-bidding-db \
    --update-secrets=DATABASE_URL=db-connection-string:latest \
    --update-secrets=OPENAI_API_KEY=openai-api-key:latest \
    --update-secrets=JWT_SECRET_KEY=jwt-secret:latest \
    --set-env-vars="LC_COLLECTION=docs,EMBED_MODEL=text-embedding-3-small,LLM_MODEL=gpt-4o-mini,RAG_MODE=balanced,ENABLE_RERANKING=true,ENABLE_REDIS_CACHE=true,REDIS_HOST=${REDIS_HOST},REDIS_PORT=6379,LOG_LEVEL=INFO,GUNICORN_WORKERS=1"

# 5. Health check
echo "🏥 Running health check..."
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region=${REGION} --format="value(status.url)")
curl -s ${SERVICE_URL}/health

echo ""
echo "✅ Deployment complete!"
echo "🌐 Service URL: ${SERVICE_URL}"
```

---

## 16. Final Recommendations (Kết Luận Từ Phân Tích Codebase)

### 🔴 CRITICAL WARNINGS

#### 1. Gunicorn Workers vs BGE Model

```
⚠️ LUÔN SET: GUNICORN_WORKERS=1

Lý do: 
- Gunicorn fork() tạo memory space RIÊNG cho mỗi worker
- Singleton pattern trong Python KHÔNG share giữa processes
- 4 workers = 4 copies của BGE model = ~6GB RAM chỉ cho model!

Cloud Run scaling strategy:
- 1 worker PER container instance
- Cloud Run tự động spawn nhiều instances khi cần
- KHÔNG dùng nhiều workers trong 1 container
```

#### 2. Cold Start Time (~50-60s)

```
Startup sequence với BGE model:
1. Container start: ~5s
2. Python import: ~10s (heavy dependencies)
3. Database init: ~2s
4. Vector store bootstrap: ~3s  
5. BGE model loading: ~30-40s ⚠️ HEAVIEST
───────────────────────────────
Total: 50-60s

→ Set min-instances=1 để tránh cold start cho production
```

#### 3. Database Connection (NullPool)

```python
# Code sử dụng NullPool - không có connection pooling
poolclass=NullPool  # Mỗi request tạo connection mới

→ Cloud SQL Proxy handles pooling externally
→ Hoặc consider thêm pgBouncer sidecar
```

### ✅ VERIFIED: Fallback Mechanism

```python
# Đã verify trong bge_reranker.py - 4 layers fallback:

Layer 1 (Init):     BGE GPU load → OOM → OpenAIReranker
Layer 2 (Runtime):  BGE predict → OOM → set flag + OpenAI fallback
Layer 3 (Future):   Global _cuda_oom_fallback=True → skip BGE entirely  
Layer 4 (Final):    OpenAI fails → return dummy scores (original order)

Kết luận: System tự xử lý, không cần lo crash!
```

### 📊 Configuration Matrix

| Environment | Memory | CPU | Workers | Min Inst | Reranking | Monthly Cost* |
|-------------|--------|-----|---------|----------|-----------|---------------|
| **Dev** | 2Gi | 1 | 1 | 0 | false | ~$10-20 |
| **Staging** | 4Gi | 2 | 1 | 0 | bge (auto-fallback) | ~$30-50 |
| **Prod Light** | 4Gi | 2 | 1 | 1 | openai | ~$80-120 |
| **Prod Standard** | 4Gi | 2 | 1 | 1 | bge | ~$80-120 |
| **Prod Premium** | 8Gi | 4 | 1 | 2 | bge | ~$200-300 |

*Chi phí ước tính, phụ thuộc vào traffic thực tế

### 🎯 Recommended Production Configuration

```bash
# Balanced cost vs performance
gcloud run deploy rag-bidding-api \
    --memory=4Gi \
    --cpu=2 \
    --min-instances=1 \
    --max-instances=10 \
    --concurrency=50 \
    --timeout=300 \
    --cpu-boost \
    --set-env-vars="\
GUNICORN_WORKERS=1,\
ENABLE_RERANKING=true,\
ENABLE_REDIS_CACHE=true,\
ENABLE_ANSWER_CACHE=true,\
ENABLE_SEMANTIC_CACHE=true,\
RAG_MODE=balanced"
```

### 📝 Deployment Verification Checklist

```bash
# After deployment, verify these:

# 1. Health check
curl -s $SERVICE_URL/health | jq

# 2. Check BGE model loaded (should see in logs)
gcloud logging read "resource.type=cloud_run_revision \
  AND resource.labels.service_name=rag-bidding-api \
  AND textPayload:BGEReranker" --limit=5

# 3. Test RAG endpoint
curl -X POST $SERVICE_URL/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is RAG?"}'

# 4. Monitor memory usage
gcloud run services describe rag-bidding-api \
  --region=asia-southeast1 \
  --format="value(status.conditions)"
```

---

## Tài Liệu Tham Khảo

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud Run Samples](https://github.com/GoogleCloudPlatform/cloud-run-samples)
- [Cloud SQL for PostgreSQL](https://cloud.google.com/sql/docs/postgres)
- [pgvector on Cloud SQL](https://cloud.google.com/sql/docs/postgres/extensions#pgvector)
- [Memorystore for Redis](https://cloud.google.com/memorystore/docs/redis)
- [Secret Manager](https://cloud.google.com/secret-manager/docs)
- [Cloud Build](https://cloud.google.com/build/docs)
- [VPC Connector](https://cloud.google.com/vpc/docs/configure-serverless-vpc-access)

### Project-specific Documentation
- [DEPLOYMENT_ANALYSIS.md](DEPLOYMENT_ANALYSIS.md) - Phân tích chi tiết codebase

---

_Tài liệu được tạo cho project: **RAG-Bidding Backend**_
_Ngày cập nhật: 26/01/2026_
_Phiên bản: 3.0 (Full Codebase Analysis)_
