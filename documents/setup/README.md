# 🛠️ Setup & Installation Guides

Complete setup documentation for the RAG Bidding System.

---

## 📚 Available Guides

### 🚀 [Quick Setup Guide](QUICK_SETUP.md)
**For:** First-time users who want to get started quickly  
**Time:** ~10 minutes  
**Covers:**
- Automated PostgreSQL + pgvector installation
- Environment configuration
- Database initialization
- Basic data import

**Start here if:** You want the fastest path to a working system.

---

### 📖 [Complete Database Setup](DATABASE_SETUP.md)
**For:** Developers who need full control and understanding  
**Time:** 30-60 minutes  
**Covers:**
- Manual PostgreSQL installation and configuration
- Detailed pgvector setup
- Environment variable reference
- Data import options (raw documents vs. preprocessed)
- Verification procedures
- Troubleshooting common issues
- Performance tuning
- Advanced configuration (indexes, connection pooling, backups)

**Start here if:** You need production deployment or want to understand the full system.

---

### 🔧 [Legacy Setup Guide](setup.md)
**Status:** Maintained for reference  
**For:** Users of previous system versions  

---

## 🎯 Quick Decision Guide

**Choose Quick Setup if you want to:**
- ✅ Get started immediately
- ✅ Use default configuration
- ✅ Follow automated setup
- ✅ Import pre-processed data

**Choose Complete Database Setup if you need:**
- 🔧 Custom PostgreSQL configuration
- 🔧 Production deployment
- 🔧 Performance tuning
- 🔧 Manual control over each step
- 🔧 Troubleshooting guidance

---

## 📋 Setup Checklist

### Prerequisites
- [ ] Ubuntu 20.04+ / Debian 11+ / macOS 12+
- [ ] sudo/admin access
- [ ] 8GB+ RAM (16GB recommended)
- [ ] 20GB+ free disk space
- [ ] OpenAI API key ([Get one here](https://platform.openai.com/api-keys))

### Installation Steps
- [ ] Install PostgreSQL 18
- [ ] Install pgvector extension
- [ ] Create database and user
- [ ] Configure environment (.env file)
- [ ] Create conda environment
- [ ] Bootstrap database
- [ ] Import data
- [ ] Verify installation

### Post-Installation
- [ ] Test retrieval
- [ ] Review configuration
- [ ] Set up backups (production only)
- [ ] Configure monitoring (production only)

---

## 🔗 Related Resources

### Configuration Files
- [`.env.example`](../../.env.example) - Environment template
- [`environment.yaml`](../../environment.yaml) - Conda environment
- [`setup_db.sh`](../../setup_db.sh) - Automated database setup script

### Scripts
- [`scripts/bootstrap_db.py`](../../scripts/bootstrap_db.py) - Initialize database
- [`scripts/import_processed_chunks.py`](../../scripts/import_processed_chunks.py) - Import data
- [`scripts/batch_reprocess_all.py`](../../scripts/batch_reprocess_all.py) - Process raw documents

### Documentation
- [Technical Documentation](../technical/) - System architecture and optimization
- [Phase Reports](../phase-reports/) - Project milestones
- [Pipeline Integration](../technical/PIPELINE_INTEGRATION_SUMMARY.md) - Current system status

---

## 💡 Tips

### For Development
```bash
# Use Quick Setup
# Enable debug logging in .env
LOG_LEVEL=DEBUG
```

### For Production
```bash
# Use Complete Database Setup
# Configure performance tuning
# Set up backups
# Enable monitoring
```

### For Testing
```bash
# Import sample data only
python scripts/import_processed_chunks.py \
  --chunks-dir data/processed/chunks \
  --batch-size 10 \
  --max-chunks 100
```

---

## 🆘 Need Help?

1. **Quick issues:** Check [Quick Setup - Common Issues](QUICK_SETUP.md#-common-issues)
2. **Detailed troubleshooting:** See [Database Setup - Troubleshooting](DATABASE_SETUP.md#-troubleshooting)
3. **GitHub Issues:** Report bugs or ask questions
4. **Documentation:** Browse `documents/` folder

---

**Last Updated:** November 4, 2025  
**Status:** ✅ Ready for use
