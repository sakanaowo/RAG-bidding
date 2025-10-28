# 🐳 Docker Deployment for RAG-Bidding

This folder contains all Docker-related files and configurations for deploying the RAG-bidding application to production.

## 📁 Folder Structure

```
docker/
├── compose/                    # Docker Compose configurations
│   ├── docker-compose.yml     # CPU-only deployment
│   └── docker-compose.cuda.yml # GPU-accelerated deployment
├── config/                     # Configuration files
│   ├── .env.example           # Environment variables template
│   └── init-db.sql            # PostgreSQL initialization
├── scripts/                    # Deployment automation
│   ├── deploy.sh              # Linux/macOS deployment script
│   └── deploy.ps1             # Windows PowerShell script
├── Dockerfile                  # CPU-only production build
├── Dockerfile.cuda            # GPU-accelerated build
├── .dockerignore              # Docker build optimization
└── README.md                  # This file
```

## 🚀 Quick Start

### 1. Prerequisites
- Docker & Docker Compose installed
- OpenAI API key
- (Optional) NVIDIA Docker for GPU support

### 2. Configuration

```bash
# Copy environment template
cp docker/config/.env.example .env

# Edit with your OpenAI API key
# OPENAI_API_KEY=your_key_here
```

### 3. Deploy

**Option A: Using Scripts (Recommended)**

```bash
# Linux/macOS
./docker/scripts/deploy.sh --gpu --logs

# Windows PowerShell
.\docker\scripts\deploy.ps1 -UseGPU -ShowLogs
```

**Option B: Manual Docker Compose**

```bash
# CPU deployment
docker-compose -f docker/compose/docker-compose.yml up -d

# GPU deployment
docker-compose -f docker/compose/docker-compose.cuda.yml up -d
```

## ⚙️ Configuration Options

### Environment Variables (.env)

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | *required* | OpenAI API key |
| `RAG_MODE` | `balanced` | Performance mode: `fast`, `balanced`, `quality`, `adaptive` |
| `RERANKER_DEVICE` | `cpu` | Device for reranking: `cpu` or `cuda` |
| `ENABLE_RERANKING` | `true` | Enable document reranking |
| `CHUNK_SIZE` | `1000` | Text chunk size for processing |

### Performance Modes

- **🏃 Fast**: ~500ms response, minimal processing
- **⚖️ Balanced**: ~1-2s response, good quality/speed balance
- **🎯 Quality**: ~2-5s response, full reranking enabled
- **🤖 Adaptive**: Dynamic optimization based on query

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

### Endpoints

```bash
# Basic health check
curl http://localhost:8000/health

# System statistics
curl http://localhost:8000/stats

# API documentation
open http://localhost:8000/docs
```

### Container Management

```bash
# Check running containers
docker-compose -f docker/compose/docker-compose.yml ps

# View logs
docker-compose -f docker/compose/docker-compose.yml logs -f app

# Stop services
docker-compose -f docker/compose/docker-compose.yml down
```

## 🚨 Troubleshooting

### Common Issues

**1. Database Connection Failed**
```bash
# Check PostgreSQL logs
docker-compose -f docker/compose/docker-compose.yml logs postgres

# Test database connection
docker-compose -f docker/compose/docker-compose.yml exec app python -c "
from config.models import settings
import psycopg
conn = psycopg.connect(settings.database_url.replace('postgresql+psycopg', 'postgresql'))
print('✅ Database OK')
"
```

**2. GPU Not Available (CUDA deployment)**
```bash
# Check NVIDIA runtime
docker run --rm --gpus all nvidia/cuda:12.1-base nvidia-smi

# Verify GPU in container
docker-compose -f docker/compose/docker-compose.cuda.yml exec app python -c "
import torch
print(f'CUDA available: {torch.cuda.is_available()}')
"
```

**3. Port Already in Use**
```bash
# Find process using port 8000
netstat -tulpn | grep :8000

# Kill process or change port in compose file
```

### Performance Tuning

**High Performance (GPU available):**
```bash
RAG_MODE=quality
ENABLE_RERANKING=true
RERANKER_DEVICE=cuda
RERANKER_BATCH_SIZE=64
```

**Resource Constrained:**
```bash
RAG_MODE=fast
ENABLE_RERANKING=false
CHUNK_SIZE=500
RETRIEVAL_K=3
```

## 🔧 Development vs Production

### Development Setup
```bash
# Use CPU version for development
docker-compose -f docker/compose/docker-compose.yml up -d

# Enable debug logging
export LOG_LEVEL=DEBUG
```

### Production Setup
```bash
# Use GPU version for production
docker-compose -f docker/compose/docker-compose.cuda.yml up -d

# Optimize for production
export RAG_MODE=quality
export LOG_LEVEL=INFO
```

## 🌐 Cloud Deployment

### AWS ECS/Fargate
```bash
# Build and push to ECR
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-west-2.amazonaws.com
docker build -f docker/Dockerfile -t rag-bidding .
docker tag rag-bidding:latest 123456789012.dkr.ecr.us-west-2.amazonaws.com/rag-bidding:latest
docker push 123456789012.dkr.ecr.us-west-2.amazonaws.com/rag-bidding:latest
```

### Google Cloud Run
```bash
# Build and deploy
gcloud builds submit --tag gcr.io/PROJECT-ID/rag-bidding --file docker/Dockerfile
gcloud run deploy --image gcr.io/PROJECT-ID/rag-bidding --platform managed
```

### Azure Container Instances
```bash
# Build and deploy
az acr build --registry myregistry --image rag-bidding --file docker/Dockerfile .
az container create --resource-group myResourceGroup --name rag-app --image myregistry.azurecr.io/rag-bidding
```

## 📊 API Usage Examples

### Basic Query
```bash
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is RAG?", "mode": "balanced"}'
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

## 🔒 Security Best Practices

1. **Environment Variables**: Store sensitive data in `.env` file
2. **Network Security**: Use Docker networks for service isolation
3. **Container Security**: Run as non-root user (pre-configured)
4. **Database Security**: Use strong credentials and limit access
5. **API Security**: Implement rate limiting and authentication in production

## 📚 Additional Resources

- **Main Documentation**: `../README-DOCKER.md`
- **Deployment Guide**: `../DEPLOYMENT.md`
- **API Documentation**: `http://localhost:8000/docs` (after deployment)

## 🤝 Support

- **Issues**: Create GitHub issue
- **Logs**: `docker-compose -f docker/compose/docker-compose.yml logs -f`
- **Health**: `curl http://localhost:8000/health`

---

**🎯 Quick Commands:**

```bash
# Deploy with GPU
./docker/scripts/deploy.sh --gpu

# View logs
docker-compose -f docker/compose/docker-compose.yml logs -f

# Stop all services
docker-compose -f docker/compose/docker-compose.yml down

# Rebuild and redeploy
docker-compose -f docker/compose/docker-compose.yml up -d --build
```