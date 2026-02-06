# Phase 2 Implementation Plan: Migrate LLM to Vertex AI

## Tổng quan

Phase 2 tập trung vào việc chuyển đổi LLM từ OpenAI GPT-4o-mini sang Google Vertex AI (Gemini). Đây là thay đổi có impact lớn nhất vì LLM được sử dụng trong nhiều components.

---

## Google Cloud Run Production Requirements

> [!IMPORTANT]
> Thông tin từ [Google Cloud Run Documentation](https://cloud.google.com/run/docs/overview/what-is-cloud-run)

### Cloud Run Features cho Production

| Feature | Description | Ứng dụng |
|---------|-------------|----------|
| **HTTPS Endpoint** | Tự động provision SSL/TLS | Secure API endpoints |
| **Auto-scaling** | Scale từ 0-N instances | Handle variable load |
| **Revision Rollback** | Gradual rollout, traffic splitting | Safe deployments |
| **IAM Integration** | Fine-grained access control | Service-to-service auth |
| **VPC Connector** | Connect to Cloud SQL, Memorystore | Database access |

### Best Practices cho FastAPI trên Cloud Run

```dockerfile
# Optimized Dockerfile
FROM python:3.10-slim-buster

ENV PYTHONUNBUFFERED=1
ENV PORT=8080

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

# Gunicorn với Uvicorn workers
CMD exec gunicorn --bind :$PORT \
    --workers 2 \
    --worker-class uvicorn.workers.UvicornWorker \
    --timeout 300 \
    src.api.main:app
```

**Key configurations:**
- `--workers 2`: Suitable cho 1 vCPU Cloud Run instances
- `--timeout 300`: LLM calls có thể mất nhiều thời gian
- `PYTHONUNBUFFERED=1`: Logs không bị buffer

---

## Phase 2 Tasks

### Task 2.1: Create LLM Provider Abstraction

#### [NEW] [llm_provider.py](file:///home/sakana/Code/RAG-project/RAG-bidding/src/config/llm_provider.py)

```python
"""
LLM Provider Factory Pattern

Supports:
- OpenAI (ChatOpenAI)
- Vertex AI Gemini (ChatVertexAI)
- Google Gemini API (ChatGoogleGenerativeAI)
"""

from enum import Enum
from typing import Optional
from langchain_core.language_models import BaseChatModel
from src.config.models import settings
import os
import logging

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    OPENAI = "openai"
    VERTEX_AI = "vertex"
    GEMINI = "gemini"


def get_llm_client(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.0,
    **kwargs
) -> BaseChatModel:
    """
    Factory function to create LLM client based on provider.
    
    Args:
        provider: LLM provider (openai, vertex, gemini)
        model: Model name override
        temperature: Sampling temperature
        **kwargs: Additional provider-specific arguments
    
    Returns:
        LangChain BaseChatModel instance
    """
    provider = provider or settings.llm_provider
    
    if provider == LLMProvider.OPENAI:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model or settings.llm_model,
            temperature=temperature,
            **kwargs
        )
    
    elif provider == LLMProvider.VERTEX_AI:
        from langchain_google_vertexai import ChatVertexAI
        return ChatVertexAI(
            model=model or settings.vertex_llm_model,
            project=settings.google_cloud_project,
            location=settings.google_cloud_location,
            temperature=temperature,
            **kwargs
        )
    
    elif provider == LLMProvider.GEMINI:
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=model or settings.gemini_model,
            temperature=temperature,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            **kwargs
        )
    
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


# Singleton default client
_default_client: Optional[BaseChatModel] = None


def get_default_llm() -> BaseChatModel:
    """Get or create default LLM client (singleton)."""
    global _default_client
    if _default_client is None:
        _default_client = get_llm_client()
        logger.info(
            f"✅ Initialized LLM client: provider={settings.llm_provider}, "
            f"model={settings.llm_model if settings.llm_provider == 'openai' else settings.vertex_llm_model}"
        )
    return _default_client
```

---

### Task 2.2: Update Settings

#### [MODIFY] [models.py](file:///home/sakana/Code/RAG-project/RAG-bidding/src/config/models.py)

**Add new fields to `Settings` class:**

```python
# Provider settings (after line 28)
llm_provider: str = os.getenv("LLM_PROVIDER", "openai")  # openai, vertex, gemini
embed_provider: str = os.getenv("EMBED_PROVIDER", "openai")  # openai, vertex
reranker_provider: str = os.getenv("RERANKER_PROVIDER", "bge")  # bge, openai, vertex

# Vertex AI settings
google_cloud_project: str = os.getenv("GOOGLE_CLOUD_PROJECT", "")
google_cloud_location: str = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
vertex_llm_model: str = os.getenv("VERTEX_LLM_MODEL", "gemini-1.5-flash-002")
vertex_embed_model: str = os.getenv("VERTEX_EMBED_MODEL", "text-embedding-004")

# Gemini API (alternative)
gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
```

---

### Task 2.3: Update QA Chain

#### [MODIFY] [qa_chain.py](file:///home/sakana/Code/RAG-project/RAG-bidding/src/generation/chains/qa_chain.py)

**Changes:**

```diff
- from langchain_openai import ChatOpenAI
+ from src.config.llm_provider import get_default_llm

- model = ChatOpenAI(model=settings.llm_model, temperature=0)
+ model = get_default_llm()
```

**Complete change at lines 4 and 24:**
- Line 4: Replace import
- Line 24: Replace model initialization

---

### Task 2.4: Update Enhanced Chain

#### [MODIFY] [enhanced_chain.py](file:///home/sakana/Code/RAG-project/RAG-bidding/src/generation/chains/enhanced_chain.py)

**Apply same pattern:**
```diff
- from langchain_openai import ChatOpenAI
+ from src.config.llm_provider import get_llm_client
```

---

### Task 2.5: Update Reasoning Chain

#### [MODIFY] [reasoning_chain.py](file:///home/sakana/Code/RAG-project/RAG-bidding/src/generation/chains/reasoning_chain.py)

**Apply same pattern:**
```diff
- from langchain_openai import ChatOpenAI
+ from src.config.llm_provider import get_llm_client
```

---

### Task 2.6: Update Summary Service

#### [MODIFY] [summary_service.py](file:///home/sakana/Code/RAG-project/RAG-bidding/src/api/services/summary_service.py)

**Changes at lines 15 and 38:**
```diff
- from langchain_openai import ChatOpenAI
+ from src.config.llm_provider import get_default_llm

- summary_model = ChatOpenAI(model=settings.llm_model, temperature=0)
+ summary_model = get_default_llm()
```

---

### Task 2.7: Update Query Enhancement Base Strategy

#### [MODIFY] [base_strategy.py](file:///home/sakana/Code/RAG-project/RAG-bidding/src/retrieval/query_processing/strategies/base_strategy.py)

**Changes:**
```diff
- from langchain_openai import ChatOpenAI
+ from src.config.llm_provider import get_llm_client

# In __init__ method (around line 40-45):
- self.client = ChatOpenAI(
-     model=llm_model,
-     temperature=temperature,
-     openai_api_key=api_key,
-     max_tokens=500,
-     request_timeout=30,
- )
+ self.client = get_llm_client(
+     model=llm_model,
+     temperature=temperature,
+     max_tokens=500,
+     request_timeout=30,
+ )
```

---

### Task 2.8: Update Dependencies

#### [MODIFY] [environment.yaml](file:///home/sakana/Code/RAG-project/RAG-bidding/environment.yaml)

**Add new dependencies:**
```yaml
# Google Cloud / Vertex AI (add after langchain-openai)
- google-cloud-aiplatform>=1.50.0
- langchain-google-vertexai>=2.0.0
- langchain-google-genai>=2.0.0
```

---

### Task 2.9: Update Environment Variables

#### [MODIFY] [.env](file:///home/sakana/Code/RAG-project/RAG-bidding/.env)

**Add new configuration:**
```env
# ===== Provider Selection =====
LLM_PROVIDER=vertex  # openai, vertex, gemini

# ===== Vertex AI Configuration =====
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
VERTEX_LLM_MODEL=gemini-1.5-flash-002

# ===== Google Application Credentials =====
# For local development:
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
# For Cloud Run: Uses attached service account automatically
```

---

### Task 2.10: Create Unit Tests

#### [NEW] [test_llm_provider.py](file:///home/sakana/Code/RAG-project/RAG-bidding/tests/unit/test_llm_provider.py)

```python
"""Unit tests for LLM provider factory."""

import pytest
from unittest.mock import patch, MagicMock


class TestLLMProvider:
    """Test LLM provider factory pattern."""
    
    def test_get_llm_client_openai(self):
        """Test OpenAI client creation."""
        with patch.dict('os.environ', {'LLM_PROVIDER': 'openai'}):
            from src.config.llm_provider import get_llm_client
            client = get_llm_client(provider='openai')
            assert client is not None
    
    @pytest.mark.skipif(
        not os.getenv('GOOGLE_CLOUD_PROJECT'),
        reason="Vertex AI credentials not configured"
    )
    def test_get_llm_client_vertex(self):
        """Test Vertex AI client creation."""
        from src.config.llm_provider import get_llm_client
        client = get_llm_client(provider='vertex')
        assert client is not None
    
    def test_get_llm_client_invalid_provider(self):
        """Test error handling for invalid provider."""
        from src.config.llm_provider import get_llm_client
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            get_llm_client(provider='invalid')
```

---

## Verification Checklist

### Pre-deployment
- [ ] Install new dependencies: `pip install google-cloud-aiplatform langchain-google-vertexai`
- [ ] Set up GCP credentials: `gcloud auth application-default login`
- [ ] Verify project access: `gcloud config set project YOUR_PROJECT_ID`

### Unit Tests
```bash
cd /home/sakana/Code/RAG-project/RAG-bidding
python -m pytest tests/unit/test_llm_provider.py -v
```

### Integration Test
```bash
# Test with OpenAI first (rollback test)
LLM_PROVIDER=openai python -c "
from src.config.llm_provider import get_default_llm
llm = get_default_llm()
print(llm.invoke('Hello'))
"

# Then test with Vertex AI
LLM_PROVIDER=vertex python -c "
from src.config.llm_provider import get_default_llm
llm = get_default_llm()
print(llm.invoke('Hello'))
"
```

### Full API Test
```bash
# Start server with Vertex AI
LLM_PROVIDER=vertex python -m uvicorn src.api.main:app --reload

# Test conversation endpoint
curl -X POST http://localhost:8000/api/conversations/{conv_id}/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "Điều kiện tham gia đấu thầu là gì?"}'
```

---

## Rollback Plan

Nếu có vấn đề với Vertex AI, rollback về OpenAI bằng cách:

```bash
# Update .env
LLM_PROVIDER=openai

# Restart server
python -m uvicorn src.api.main:app --reload
```

Không cần thay đổi code vì abstraction layer hỗ trợ cả hai providers.

---

## Timeline Estimate

| Task | Time | Priority |
|------|------|----------|
| Task 2.1: LLM Provider | 30 min | P0 |
| Task 2.2: Update Settings | 15 min | P0 |
| Task 2.3-2.7: Update 5 files | 1 hour | P0 |
| Task 2.8-2.9: Dependencies + Env | 15 min | P0 |
| Task 2.10: Unit Tests | 30 min | P1 |
| Verification | 1 hour | P0 |
| **Total** | **~3.5 hours** | |
