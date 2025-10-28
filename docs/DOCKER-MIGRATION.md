# 🐳 RAG-Bidding Docker Deployment

All Docker-related files have been organized into the `docker/` folder for better project structure and maintainability.

## 📁 New Structure

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
└── README.md                  # Comprehensive documentation
```

## 🚀 Quick Start Commands

### Using Deployment Scripts (Recommended)

```powershell
# Windows PowerShell - GPU deployment with logs
.\docker\scripts\deploy.ps1 -UseGPU -ShowLogs

# Windows PowerShell - CPU deployment
.\docker\scripts\deploy.ps1
```

```bash
# Linux/macOS - GPU deployment with logs  
./docker/scripts/deploy.sh --gpu --logs

# Linux/macOS - CPU deployment
./docker/scripts/deploy.sh
```

### Manual Docker Compose

```powershell
# Windows - GPU deployment
docker-compose -f docker\compose\docker-compose.cuda.yml up -d

# Windows - CPU deployment  
docker-compose -f docker\compose\docker-compose.yml up -d
```

```bash
# Linux/macOS - GPU deployment
docker-compose -f docker/compose/docker-compose.cuda.yml up -d

# Linux/macOS - CPU deployment
docker-compose -f docker/compose/docker-compose.yml up -d
```

## ⚙️ Configuration

1. **Copy environment template:**
   ```powershell
   cp docker\config\.env.example .env
   ```

2. **Edit `.env` with your OpenAI API key:**
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

3. **Choose performance mode:**
   - `RAG_MODE=fast` - ~500ms response
   - `RAG_MODE=balanced` - ~1-2s response (default)
   - `RAG_MODE=quality` - ~2-5s response  
   - `RAG_MODE=adaptive` - Dynamic optimization

4. **GPU Settings (if available):**
   ```
   RERANKER_DEVICE=cuda
   ENABLE_RERANKING=true
   ```

## 🔍 Health Checks

```bash
# Check application health
curl http://localhost:8000/health

# View system statistics  
curl http://localhost:8000/stats

# Access API documentation
open http://localhost:8000/docs
```

## 📊 Container Management

```powershell
# Check running containers
docker-compose -f docker\compose\docker-compose.yml ps

# View application logs
docker-compose -f docker\compose\docker-compose.yml logs -f app

# Stop all services
docker-compose -f docker\compose\docker-compose.yml down
```

## 📚 Documentation

- **`docker/README.md`** - Comprehensive Docker deployment guide
- **`README-DOCKER.md`** - Quick start guide  
- **`DEPLOYMENT.md`** - Advanced deployment scenarios
- **API Docs**: Available at `http://localhost:8000/docs` after deployment

## 🎯 Benefits of New Structure

✅ **Organized**: All Docker files in dedicated folder  
✅ **Maintainable**: Clear separation of concerns  
✅ **Flexible**: Support for both CPU and GPU deployments  
✅ **Automated**: Scripts handle deployment complexity  
✅ **Documented**: Comprehensive guides for all scenarios  
✅ **Production-Ready**: Security hardening and optimization

## 🚨 Migration Notes

- All Docker files moved from root to `docker/` folder
- Deployment scripts updated with correct paths
- Docker Compose files reference new file locations
- Environment configuration centralized in `docker/config/`

The new structure provides better organization while maintaining all functionality. Use the scripts in `docker/scripts/` for automated deployment or run Docker Compose manually from the project root using the files in `docker/compose/`.