# RAG-Bidding Production Deployment Guide

This guide provides comprehensive instructions for deploying the RAG-bidding application to production using Docker.

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose installed
- NVIDIA Docker runtime (for GPU support, optional)
- OpenAI API key

### 1. Basic Deployment (CPU only)

```bash
# Clone the repository
git clone <your-repo-url>
cd RAG-bidding

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your OpenAI API key and other configurations

# Build and start services
docker-compose up -d

# Check logs
docker-compose logs -f app
```

### 2. GPU-Accelerated Deployment (Recommended for production)

```bash
# Use CUDA-enabled configuration
docker-compose -f docker-compose.cuda.yml up -d

# Monitor GPU usage
nvidia-smi
```

## 📋 Configuration

### Environment Variables

Edit the `.env` file with your specific configuration:

```bash
# Required
OPENAI_API_KEY=your_openai_api_key_here

# Optional - Model configurations
RAG_MODE=balanced  # fast, balanced, quality, adaptive
RERANKER_DEVICE=cuda  # Use 'cuda' for GPU acceleration
ENABLE_RERANKING=true
```

### Available RAG Modes

- **fast**: Minimal processing, fastest response (~500ms)
- **balanced**: Good quality with reasonable speed (~1-2s)
- **quality**: Best quality with full reranking (~2-5s)
- **adaptive**: Dynamic optimization based on query complexity

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
│   (Embeddings   │
│   & LLM)       │
└─────────────────┘
```

## 🛠️ Production Deployment Options

### Option 1: Docker Compose (Recommended for single server)

```bash
# Production deployment with all optimizations
docker-compose -f docker-compose.cuda.yml up -d
```

### Option 2: Kubernetes Deployment

Create Kubernetes manifests:

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rag-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: rag-app
  template:
    metadata:
      labels:
        app: rag-app
    spec:
      containers:
      - name: rag-app
        image: your-registry/rag-bidding:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          value: "postgresql+psycopg://user:pass@postgres:5432/ragdb"
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: openai-secret
              key: api-key
        resources:
          requests:
            nvidia.com/gpu: 1
          limits:
            nvidia.com/gpu: 1
---
apiVersion: v1
kind: Service
metadata:
  name: rag-app-service
spec:
  selector:
    app: rag-app
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

### Option 3: Cloud Deployment

#### AWS ECS/Fargate
```bash
# Build and push to ECR
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-west-2.amazonaws.com
docker build -t rag-bidding .
docker tag rag-bidding:latest 123456789012.dkr.ecr.us-west-2.amazonaws.com/rag-bidding:latest
docker push 123456789012.dkr.ecr.us-west-2.amazonaws.com/rag-bidding:latest
```

#### Google Cloud Run
```bash
# Build and deploy
gcloud builds submit --tag gcr.io/PROJECT-ID/rag-bidding
gcloud run deploy --image gcr.io/PROJECT-ID/rag-bidding --platform managed
```

## 🔧 Performance Optimization

### 1. Hardware Recommendations

**Minimum Requirements:**
- CPU: 4 cores
- RAM: 8GB
- Storage: 50GB SSD

**Recommended for Production:**
- CPU: 8+ cores
- RAM: 16GB+
- GPU: NVIDIA GPU with 8GB+ VRAM (for reranking)
- Storage: 100GB+ NVMe SSD

### 2. Database Optimization

```sql
-- Optimize PostgreSQL for vector operations
ALTER SYSTEM SET shared_preload_libraries = 'vector';
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
```

### 3. Application Tuning

```bash
# High-performance configuration
RAG_MODE=quality
ENABLE_RERANKING=true
RERANKER_DEVICE=cuda
PARALLEL_PROCESSING=true
CACHE_EMBEDDINGS=true
RERANKER_BATCH_SIZE=64
```

## 📊 Monitoring and Observability

### Health Checks

```bash
# Check application health
curl http://localhost:8000/health

# Check system stats
curl http://localhost:8000/stats
```

### Monitoring Setup

Add monitoring stack with Prometheus and Grafana:

```yaml
# Add to docker-compose.yml
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

## 🔒 Security Considerations

### 1. Environment Security
- Store sensitive variables in secrets management (AWS Secrets Manager, K8s Secrets)
- Use least-privilege database users
- Enable TLS/SSL for all connections

### 2. Network Security
```bash
# Restrict database access
docker-compose exec postgres psql -U superuser -d ragdb -c "
ALTER SYSTEM SET listen_addresses = 'localhost';
"
```

### 3. Container Security
- Run containers as non-root user (already configured)
- Regular security updates
- Image vulnerability scanning

## 🚨 Troubleshooting

### Common Issues

1. **Database Connection Issues**
```bash
# Check database connectivity
docker-compose exec app python -c "
from config.models import settings
import psycopg
conn = psycopg.connect(settings.database_url.replace('postgresql+psycopg', 'postgresql'))
print('Database connection: OK')
"
```

2. **GPU Not Detected**
```bash
# Verify NVIDIA runtime
docker run --rm --gpus all nvidia/cuda:12.1-base nvidia-smi
```

3. **Performance Issues**
```bash
# Check resource usage
docker stats
```

### Logs Analysis
```bash
# Application logs
docker-compose logs -f app

# Database logs
docker-compose logs -f postgres

# Filter error logs
docker-compose logs app | grep ERROR
```

## 📈 Scaling

### Horizontal Scaling
```yaml
# docker-compose.yml
services:
  app:
    deploy:
      replicas: 3
    # Add load balancer
  nginx:
    image: nginx
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
```

### Database Scaling
- Read replicas for query scaling
- Connection pooling with PgBouncer
- Vector index optimization

## 🔄 CI/CD Pipeline

Example GitHub Actions workflow:

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Build and Deploy
      run: |
        docker build -t rag-bidding .
        # Deploy to your infrastructure
```

## 📚 API Documentation

Once deployed, access:
- API Documentation: `http://your-domain:8000/docs`
- Health Check: `http://your-domain:8000/health`
- System Stats: `http://your-domain:8000/stats`

## 🧪 Testing Production Deployment

```bash
# Test basic functionality
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is RAG?", "mode": "balanced"}'

# Load testing with Apache Bench
ab -n 100 -c 10 -T application/json -p test-payload.json http://localhost:8000/ask
```