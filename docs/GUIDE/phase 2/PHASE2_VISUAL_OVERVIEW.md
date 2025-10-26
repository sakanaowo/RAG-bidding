# 📊 Phase 2 Reranking - Visual Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PHASE 2: DOCUMENT RERANKING                       │
│                  Vietnamese Legal RAG Enhancement                    │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  CURRENT STATE (Phase 1 ✅)        →        TARGET STATE (Phase 2)   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Query                                      Query                    │
│    ↓                                          ↓                      │
│  Enhancement (4 strategies) ✅             Enhancement ✅            │
│    ↓                                          ↓                      │
│  Vector Search (k=5-10) ✅                 Vector Search (k=10) ✅   │
│    ↓                                          ↓                      │
│  RRF Fusion ✅                              RRF Fusion ✅            │
│    ↓                                          ↓                      │
│  ❌ NO RERANKING                            ⭐ RERANKING ⭐          │
│    ↓                                          ↓                      │
│  Documents (not optimal order)             Documents (optimal)       │
│    ↓                                          ↓                      │
│  Answer Generation                         Answer Generation         │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                     RERANKING METHODS COMPARISON                     │
├──────────────────┬──────────────┬──────────────┬───────────────────┤
│ Method           │ Accuracy     │ Latency      │ Cost              │
├──────────────────┼──────────────┼──────────────┼───────────────────┤
│ Cross-Encoder    │ ⭐⭐⭐⭐⭐  │ ~100ms       │ $0 (self-hosted)  │
│ ⭐ RECOMMENDED   │ (Very High)  │ (Fast)       │                   │
├──────────────────┼──────────────┼──────────────┼───────────────────┤
│ LLM-based        │ ⭐⭐⭐⭐    │ ~500-800ms   │ ~$5/month         │
│ (GPT-4o-mini)    │ (High)       │ (Slow)       │ (Low usage)       │
├──────────────────┼──────────────┼──────────────┼───────────────────┤
│ Legal Scoring    │ ⭐⭐⭐       │ ~5ms         │ $0 (rule-based)   │
│ (Rule-based)     │ (Medium)     │ (Very Fast)  │                   │
├──────────────────┼──────────────┼──────────────┼───────────────────┤
│ Cohere API       │ ⭐⭐⭐⭐⭐  │ ~200-400ms   │ $30/month         │
│ (Alternative)    │ (Very High)  │ (Medium)     │ (1000 searches)   │
└──────────────────┴──────────────┴──────────────┴───────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                      IMPLEMENTATION TIMELINE                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Week 1: Phase 2A - Core Reranking ⭐ START HERE                    │
│  ├── Day 1-2: Base infrastructure + Cross-Encoder                   │
│  ├── Day 3-4: Integration with Retrievers                           │
│  └── Day 5:   Testing + Benchmarking                                │
│                                                                       │
│  Week 2: Phase 2B+C - Advanced (Optional)                           │
│  ├── Days 1-3: LLM-based reranking                                  │
│  └── Days 4-5: Legal domain scoring                                 │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    MODE-SPECIFIC CONFIGURATION                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  FAST MODE (< 300ms)                                                │
│  ├── Query Enhancement: ❌ Disabled                                 │
│  ├── Retrieval: k=3                                                 │
│  ├── Reranking: ❌ Disabled (or Legal Scoring only)                │
│  └── Use Case: Simple queries, quick answers                        │
│                                                                       │
│  BALANCED MODE (< 800ms)                                            │
│  ├── Query Enhancement: ✅ Multi-Query + Step-Back                  │
│  ├── Retrieval: k=8                                                 │
│  ├── Reranking: ✅ Cross-Encoder ⭐                                 │
│  └── Use Case: Most queries (80% of traffic)                        │
│                                                                       │
│  QUALITY MODE (< 1500ms)                                            │
│  ├── Query Enhancement: ✅ All 4 strategies                         │
│  ├── Retrieval: k=10                                                │
│  ├── Reranking: ✅ Cross-Encoder + LLM validation ⭐               │
│  └── Use Case: Complex legal queries, high stakes                   │
│                                                                       │
│  ADAPTIVE MODE (Dynamic)                                            │
│  ├── Complexity Analysis → Route to appropriate mode                │
│  ├── Simple → Fast, Medium → Balanced, Complex → Quality            │
│  └── Reranking: ✅ Based on complexity ⭐                           │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                        EXPECTED IMPROVEMENTS                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Accuracy Metrics:                                                   │
│  ├── MRR (Mean Reciprocal Rank):   0.70 → 0.85  (+21% ⬆)           │
│  ├── NDCG@5:                        0.75 → 0.90  (+20% ⬆)           │
│  └── Recall@5:                      0.85 → 0.95  (+12% ⬆)           │
│                                                                       │
│  Performance Impact:                                                 │
│  ├── Fast mode:      No change      (~300ms)                        │
│  ├── Balanced mode:  +100ms         (500ms → 600ms)                 │
│  └── Quality mode:   +150ms         (500ms → 650ms)                 │
│                                                                       │
│  User Experience:                                                    │
│  ├── Relevance satisfaction:        3.5/5 → 4.2/5  (+20% ⬆)        │
│  ├── Task completion rate:          75%   → 90%    (+15% ⬆)        │
│  └── Fewer follow-up queries:       40%   → 20%    (-50% ⬇)        │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                          TECHNICAL STACK                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  New Dependencies:                                                   │
│  ├── sentence-transformers>=2.2.0   (Cross-Encoder models)          │
│  ├── torch>=2.0.0                   (PyTorch backend)               │
│  └── transformers>=4.30.0           (HuggingFace)                   │
│                                                                       │
│  Models to Download:                                                 │
│  ├── BAAI/bge-reranker-v2-m3        (~400MB) ⭐ Primary             │
│  └── bkai-foundation-models/vietnamese-bi-encoder  (Alternative)    │
│                                                                       │
│  Infrastructure:                                                     │
│  ├── Disk: +500MB (models)                                          │
│  ├── RAM:  +1GB   (model in memory)                                 │
│  └── GPU:  Optional (faster inference, ~2x speedup)                 │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                     CROSS-ENCODER WORKFLOW                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Input: Query + 10 Documents from Vector Search                     │
│    │                                                                 │
│    ├─► Pair 1: [Query, Doc 1] ──┐                                  │
│    ├─► Pair 2: [Query, Doc 2] ──┤                                  │
│    ├─► Pair 3: [Query, Doc 3] ──┤                                  │
│    ├─► ...                       ├─► Cross-Encoder Model            │
│    ├─► Pair 9: [Query, Doc 9] ──┤    (BAAI/bge-reranker-v2-m3)     │
│    └─► Pair 10: [Query, Doc 10]─┘                                  │
│                                   │                                  │
│                                   ↓                                  │
│                           Relevance Scores                           │
│                           [0.92, 0.85, 0.78, ...]                   │
│                                   │                                  │
│                                   ↓                                  │
│                           Sort by Score                              │
│                                   │                                  │
│                                   ↓                                  │
│  Output: Top 5 Documents (Best → Worst)                             │
│    1. Doc 3  (score: 0.92) ⭐ Most relevant                         │
│    2. Doc 1  (score: 0.85)                                          │
│    3. Doc 7  (score: 0.78)                                          │
│    4. Doc 2  (score: 0.71)                                          │
│    5. Doc 9  (score: 0.68)                                          │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                        VIETNAMESE LEGAL EXAMPLE                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Query: "Thời hạn hiệu lực của bảo đảm dự thầu là bao lâu?"         │
│                                                                       │
│  WITHOUT Reranking (Vector Search Only):                            │
│  ┌────────────────────────────────────────────────────────┐         │
│  │ 1. Điều 68. Bảo đảm thực hiện hợp đồng... [0.78] ❌    │         │
│  │ 2. Điều 14. Bảo đảm dự thầu... [0.75] ✅ (should be 1st)│        │
│  │ 3. Điều 10. Ưu đãi nhà thầu trong nước... [0.71] ❌    │         │
│  │ 4. Điều 39. Thời gian thực hiện gói thầu... [0.68] ❌  │         │
│  │ 5. Điều 51. Yêu cầu hệ thống mạng... [0.65] ❌         │         │
│  └────────────────────────────────────────────────────────┘         │
│  Problem: Điều 14 (correct answer) is ranked #2                     │
│                                                                       │
│  WITH Reranking (Cross-Encoder):                                    │
│  ┌────────────────────────────────────────────────────────┐         │
│  │ 1. Điều 14. Bảo đảm dự thầu... [0.92] ✅ (correct!)    │         │
│  │ 2. Điều 68. Bảo đảm thực hiện hợp đồng... [0.71]       │         │
│  │ 3. Điều 39. Thời gian thực hiện gói thầu... [0.58]     │         │
│  │ 4. Điều 10. Ưu đãi nhà thầu trong nước... [0.42]       │         │
│  │ 5. Điều 51. Yêu cầu hệ thống mạng... [0.31]            │         │
│  └────────────────────────────────────────────────────────┘         │
│  ✅ Correct answer now ranked #1!                                   │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                         QUICK START STEPS                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Day 1: Get Reranking Working (3 hours)                             │
│  ┌────────────────────────────────────────────────────┐             │
│  │ ① Install dependencies (5 min)                     │             │
│  │   pip install sentence-transformers torch          │             │
│  │                                                     │             │
│  │ ② Create base_reranker.py (15 min)                │             │
│  │   Abstract class for all rerankers                 │             │
│  │                                                     │             │
│  │ ③ Create cross_encoder_reranker.py (30 min)       │             │
│  │   Implementation using BAAI model                  │             │
│  │                                                     │             │
│  │ ④ Test reranker standalone (15 min)               │             │
│  │   python test_quick.py                             │             │
│  │                                                     │             │
│  │ ⑤ Integrate with EnhancedRetriever (1 hour)       │             │
│  │   Add reranker parameter, update logic             │             │
│  │                                                     │             │
│  │ ⑥ Update factory pattern (30 min)                 │             │
│  │   Initialize reranker in create_retriever()        │             │
│  │                                                     │             │
│  │ ⑦ Test via API (15 min)                           │             │
│  │   curl localhost:8000/ask -d '{"mode":"quality"}'  │             │
│  └────────────────────────────────────────────────────┘             │
│                                                                       │
│  ✅ Done! Reranking now working in quality mode                     │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                           SUCCESS METRICS                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Before deploying to production, verify:                             │
│                                                                       │
│  Technical Metrics:                                                  │
│  ☐ Cross-encoder loads without errors                               │
│  ☐ Reranking completes in < 150ms (10 docs)                         │
│  ☐ Total latency < 800ms (balanced mode)                            │
│  ☐ Memory usage < 2GB                                               │
│  ☐ All unit tests passing                                           │
│                                                                       │
│  Quality Metrics:                                                    │
│  ☐ MRR improved by > 15%                                            │
│  ☐ NDCG@5 improved by > 15%                                         │
│  ☐ Top result is correct for > 80% of test queries                  │
│                                                                       │
│  Production Readiness:                                               │
│  ☐ Handles 100 queries without crashes                              │
│  ☐ Error handling for edge cases                                    │
│  ☐ Logging properly configured                                      │
│  ☐ A/B test shows improvement                                       │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                              RESOURCES                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  📄 Documentation:                                                   │
│  ├── Full Plan:        dev-log/PHASE2_RERANKING_PLAN.md             │
│  └── Quick Start:      dev-log/PHASE2_QUICK_START.md                │
│                                                                       │
│  🔗 External Links:                                                  │
│  ├── BAAI Reranker:    huggingface.co/BAAI/bge-reranker-v2-m3       │
│  ├── Sentence-Transformers: sbert.net/examples/applications/        │
│  └── Cross-Encoders:   sbert.net/docs/pretrained_cross-encoders.html│
│                                                                       │
│  📚 Papers:                                                          │
│  ├── RankGPT:          arxiv.org/abs/2304.09542                     │
│  └── ColBERTv2:        arxiv.org/abs/2112.01488                     │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

**Ready to implement? Start with `PHASE2_QUICK_START.md`!** 🚀
