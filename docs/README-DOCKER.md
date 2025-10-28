# 🚀 RAG-Bidding Production Deployment

A comprehensive guide for deploying the RAG-bidding application to production using Docker.

## 📋 Quick Start

### 1. Prerequisites
- Docker & Docker Compose
- OpenAI API key
- (Optional) NVIDIA Docker for GPU acceleration

### 2. Basic Setup

```bash
# Clone and configure
git clone <your-repo>
cd RAG-bidding
cp .env.example .env

# Edit .env with your OpenAI API key
# OPENAI_API_KEY=your_key_here

# Deploy (CPU version)
docker-compose up -d
```

### 3. GPU-Accelerated Setup (Recommended)

```bash
# Deploy with GPU support
docker-compose -f docker-compose.cuda.yml up -d
```

## 🐳 Docker Files Overview

| File | Purpose |
|------|---------|
| `Dockerfile` | CPU-only production build |
| `Dockerfile.cuda` | GPU-accelerated build with CUDA support |
| `docker-compose.yml` | Standard deployment configuration |
| `docker-compose.cuda.yml` | GPU-enabled deployment |
| `init-db.sql` | PostgreSQL initialization script |

## ⚙️ Configuration

### Environment Variables (`.env`)

```bash
# Required
OPENAI_API_KEY=your_openai_api_key_here

# Performance Mode
RAG_MODE=balanced  # fast | balanced | quality | adaptive

# GPU Settings (for CUDA deployment)
RERANKER_DEVICE=cuda  # cpu | cuda

# Optional Advanced Settings
ENABLE_RERANKING=true
ENABLE_QUERY_ENHANCEMENT=true
CHUNK_SIZE=1000
```

### Performance Modes

- **🏃 Fast Mode**: Minimal processing (~500ms response)
- **⚖️ Balanced Mode**: Good quality + speed (~1-2s response)  
- **🎯 Quality Mode**: Best results with full reranking (~2-5s)
- **🤖 Adaptive Mode**: Dynamic optimization based on query

## 🛠️ Deployment Methods

### Method 1: Automated Scripts

**Linux/macOS:**
```bash
# CPU deployment
./deploy.sh

# GPU deployment  
./deploy.sh --gpu

# With logs
./deploy.sh --gpu --logs
```

**Windows PowerShell:**
```powershell
# CPU deployment
.\deploy.ps1

# GPU deployment
.\deploy.ps1 -UseGPU

# With logs
.\deploy.ps1 -UseGPU -ShowLogs
```

### Method 2: Manual Docker Compose

**CPU Version:**
```bash
docker-compose up -d
```

**GPU Version:**
```bash
docker-compose -f docker-compose.cuda.yml up -d
```

### Method 3: Individual Container Build

```bash
# Build
docker build -t rag-bidding .

# Run with external database
docker run -d \
  -p 8000:8000 \
  -e DATABASE_URL="postgresql+psycopg://user:pass@host:5432/db" \
  -e OPENAI_API_KEY="your-key" \
  rag-bidding
```

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │────│   PostgreSQL    │────│   pgvector      │
│   (Port 8000)   │    │   (Port 5432)   │    │   Extension     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────┐
│   OpenAI API    │
│ (Embeddings/LLM)│
└─────────────────┘
```

## 🔍 Health Checks & Monitoring

### Health Check Endpoints

```bash
# Basic health
curl http://localhost:8000/health

# System statistics
curl http://localhost:8000/stats

# API documentation
open http://localhost:8000/docs
```

### Container Monitoring

```bash
# Check running containers
docker-compose ps

# View logs
docker-compose logs -f app

# Resource usage
docker stats
```

## 🚨 Troubleshooting

### Common Issues

**1. Database Connection Failed**
```bash
# Check PostgreSQL container
docker-compose logs postgres

# Test connection
docker-compose exec app python -c "
from config.models import settings
import psycopg
conn = psycopg.connect(settings.database_url.replace('postgresql+psycopg', 'postgresql'))
print('✅ Database OK')
"
```

**2. GPU Not Available**
```bash
# Check NVIDIA runtime
docker run --rm --gpus all nvidia/cuda:12.1-base nvidia-smi

# Verify GPU access in container
docker-compose exec app python -c "
import torch
print(f'CUDA available: {torch.cuda.is_available()}')
print(f'GPU count: {torch.cuda.device_count()}')
"
```

**3. High Memory Usage**
```bash
# Optimize for limited memory
export RERANKER_BATCH_SIZE=16
export CHUNK_SIZE=500
docker-compose up -d
```

### Performance Tuning

**High Performance Configuration:**
```bash
# .env settings for maximum performance
RAG_MODE=quality
ENABLE_RERANKING=true
RERANKER_DEVICE=cuda
PARALLEL_PROCESSING=true
CACHE_EMBEDDINGS=true
RERANKER_BATCH_SIZE=64
```

**Resource Constrained Configuration:**
```bash
# .env settings for limited resources
RAG_MODE=fast
ENABLE_RERANKING=false
RERANKER_DEVICE=cpu
CHUNK_SIZE=500
RETRIEVAL_K=3
```

## 🌐 Production Deployment

### Cloud Platforms

#### AWS ECS/Fargate
```bash
# Build and push to ECR
aws ecr get-login-password | docker login --username AWS --password-stdin 123456789012.dkr.ecr.region.amazonaws.com
docker build -t rag-bidding .
docker tag rag-bidding:latest 123456789012.dkr.ecr.region.amazonaws.com/rag-bidding:latest
docker push 123456789012.dkr.ecr.region.amazonaws.com/rag-bidding:latest
```

#### Google Cloud Run
```bash
gcloud builds submit --tag gcr.io/PROJECT-ID/rag-bidding
gcloud run deploy --image gcr.io/PROJECT-ID/rag-bidding --platform managed
```

#### Azure Container Instances
```bash
az acr build --registry myregistry --image rag-bidding .
az container create --resource-group myResourceGroup --name rag-app --image myregistry.azurecr.io/rag-bidding
```

### Kubernetes Deployment

See `DEPLOYMENT.md` for complete Kubernetes manifests and advanced deployment options.

## 📊 API Usage Examples

### Basic Query
```bash
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is RAG?", "mode": "balanced"}'
```

### Quality Mode Query
```bash
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Explain bidding strategies", "mode": "quality"}'
```

### Response Format
```json
{
  "answer": "RAG (Retrieval-Augmented Generation) combines...",
  "sources": ["doc1.pdf", "doc2.pdf"],
  "adaptive_retrieval": {"strategy": "semantic", "k": 5},
  "enhanced_features": ["query_expansion", "reranking"],
  "processing_time_ms": 1250
}
```

## 🔒 Security

### Environment Security
- Store `OPENAI_API_KEY` in secure secret management
- Use least-privilege database credentials
- Enable TLS for all external connections

### Container Security
- Containers run as non-root user
- Minimal base images with security updates
- Network isolation between services

## 📈 Scaling

### Horizontal Scaling
```yaml
# docker-compose.yml
services:
  app:
    deploy:
      replicas: 3
  nginx:
    image: nginx
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
```

### Performance Optimization
- Use GPU acceleration for reranking
- Enable connection pooling
- Implement response caching
- Optimize vector index settings

## 📚 Further Reading

- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Comprehensive deployment guide
- **[API Documentation](http://localhost:8000/docs)** - Interactive API docs
- **[Performance Tuning](docs/PERFORMANCE.md)** - Optimization strategies

## 🤝 Support

- **Issues**: Create GitHub issue
- **Performance**: Check system stats endpoint
- **Logs**: Use `docker-compose logs -f app`

---

**🎯 Quick Commands Summary:**

```bash
# Standard deployment
docker-compose up -d

# GPU deployment  
docker-compose -f docker-compose.cuda.yml up -d

# Check health
curl http://localhost:8000/health

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```