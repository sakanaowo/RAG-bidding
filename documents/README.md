# 📚 Documentation Structure

This directory contains all project documentation organized by purpose.

## 📁 Directory Structure

### 🚨 `/chat-session-implementation/` ⭐ IMPORTANT
**Status:** 🟡 READY TO IMPLEMENT  
Chat session migration plan (Redis → PostgreSQL):
- `TODO_CHAT_SESSION_MIGRATION.md` - Quick checklist
- `CHAT_SESSION_POSTGRESQL_PLAN.md` - Full plan (750+ lines)
- `CHAT_SESSION_DB_SCHEMA.md` - Database schema
- **Priority:** HIGH - Triển khai sau khi performance ổn định

### `/phase-reports-deprecated/` ⚠️ DEPRECATED
Old project phase reports (Phase 4-5 from Nov 2025):
- Phase 4: Batch reprocessing (COMPLETED)
- Phase 5: Morning plans, checklists (COMPLETED)
- **Do not use** - Kept for historical reference only

### `/technical/`
Technical documentation and system architecture:
- Performance optimization, caching strategies
- System architecture, pipeline integration
- Reranking analysis, performance reports
- **Active:** Current production documentation

### `/verification/`
Verification and validation reports:
- Cache verification
- General verification reports

### `/setup/`
Setup and installation guides:
- Database setup
- Quick setup guide

### `/planning/`
Project planning and analysis:
- `preprocess-plan-deprecated/` ⚠️ DEPRECATED - Old preprocessing architecture (Nov 2025)
  - **Do not use** - Preprocessing already complete

## 📝 Document Types

**Implementation Plans** → `/chat-session-implementation/` 🚨  
**Reports** → `/verification/`  
**Architecture** → `/technical/`  
**Setup** → `/setup/`  
**Deprecated** → `*-deprecated/` folders

## 🔗 Quick Links

- [Main README](../README.md) - Project overview
- [Setup Guide](setup/QUICK_SETUP.md) - Installation instructions
- 🚨 [Chat Session Plan](chat-session-implementation/README.md) - **IMPORTANT** Implementation needed
- [Pipeline Integration](technical/system-architecture/PIPELINE_INTEGRATION_SUMMARY.md) - Current system
- [Performance Analysis](technical/performance-analysis/) - Current bottlenecks
