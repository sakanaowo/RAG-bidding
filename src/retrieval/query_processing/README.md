# Query Enhancement Module

**Location**: `src/retrieval/query_processing/`  
**Phase**: Phase 5 - Retrieval Enhancement  
**Status**: 🚧 In Development

## 📋 Overview

Query Enhancement là kỹ thuật quan trọng trong RAG để cải thiện chất lượng retrieval bằng cách:
- Tạo nhiều biến thể của câu hỏi (Multi-Query)
- Tạo hypothetical documents (HyDE)
- Phân tích và đơn giản hóa câu hỏi phức tạp (Decomposition)
- Tạo câu hỏi tổng quát hơn (Step-back)

## 🗂️ Module Structure

```
query_processing/
├── __init__.py
├── query_enhancer.py           # ✅ Main enhancement orchestrator
├── complexity_analyzer.py       # ✅ Vietnamese query complexity analysis
│
└── strategies/                  # 🚧 Enhancement strategies
    ├── __init__.py
    ├── multi_query.py          # TODO: Multi-query generation
    ├── hyde.py                 # TODO: Hypothetical Document Embeddings
    ├── step_back.py            # TODO: Step-back prompting
    └── decomposition.py        # TODO: Query decomposition
```

## 🎯 Implementation Plan

### Phase 1: Core Setup ✅
- [x] Move existing code to new structure
- [x] Update imports
- [x] Basic QueryEnhancer class
- [x] ComplexityAnalyzer for Vietnamese

### Phase 2: Strategy Implementation 🚧
- [ ] Implement Multi-Query strategy
- [ ] Implement HyDE strategy
- [ ] Implement Step-back strategy
- [ ] Implement Decomposition strategy

### Phase 3: Integration 📋
- [ ] Integrate with AdaptiveRetriever
- [ ] Add caching layer
- [ ] Performance optimization

### Phase 4: Testing ⏳
- [ ] Unit tests for each strategy
- [ ] Integration tests
- [ ] Benchmark against baseline

## 📖 Usage Examples

### Basic Usage

```python
from src.retrieval.query_processing.query_enhancer import (
    QueryEnhancer, 
    QueryEnhancerConfig,
    EnhancementStrategy
)

# Initialize with single strategy
config = QueryEnhancerConfig(
    strategies=[EnhancementStrategy.MULTI_QUERY],
    max_queries=3
)
enhancer = QueryEnhancer(config)

# Enhance query
query = "Điều kiện để tham gia đấu thầu xây dựng là gì?"
enhanced_queries = enhancer.enhance(query)

print(f"Original: {query}")
for i, eq in enumerate(enhanced_queries, 1):
    print(f"{i}. {eq}")
```

### Advanced Usage - Multiple Strategies

```python
# Use multiple enhancement strategies
config = QueryEnhancerConfig(
    strategies=[
        EnhancementStrategy.MULTI_QUERY,
        EnhancementStrategy.HYDE,
        EnhancementStrategy.STEP_BACK
    ],
    max_queries=5,
    enable_caching=True
)

enhancer = QueryEnhancer(config)
enhanced = enhancer.enhance("Cách tính giá dự thầu cho dự án phần mềm?")
```

### Integration with Retrieval

```python
from src.retrieval.retrievers.adaptive_retriever import AdaptiveRetriever
from src.embedding.store.pgvector_store import vector_store

# Create enhanced retriever
retriever = AdaptiveRetriever(
    vector_store=vector_store,
    query_enhancer=enhancer
)

# Retrieve with query enhancement
results = retriever.retrieve(
    query="Quy trình đấu thầu quốc tế?",
    top_k=5
)
```

## 🔧 Configuration

### QueryEnhancerConfig

```python
@dataclass
class QueryEnhancerConfig:
    llm_model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_queries: int = 3
    strategies: List[EnhancementStrategy] = None
    enable_caching: bool = True
```

### Environment Variables

```bash
# .env file
LLM_MODEL=gpt-4o-mini
MAX_ENHANCED_QUERIES=3
ENABLE_QUERY_CACHE=true
```

## 🎨 Enhancement Strategies

### 1. Multi-Query Generation
**Purpose**: Tạo nhiều cách diễn đạt khác nhau cho cùng một câu hỏi

```python
# Input
"Điều kiện tham gia đấu thầu là gì?"

# Output
[
    "Điều kiện tham gia đấu thầu là gì?",  # Original
    "Yêu cầu để được tham gia đấu thầu?",
    "Tiêu chuẩn nhà thầu phải đáp ứng?",
    "Tư cách hợp lệ của nhà thầu?"
]
```

**When to use**: 
- Câu hỏi có thể diễn đạt nhiều cách
- Tăng recall khi search

### 2. HyDE (Hypothetical Document Embeddings)
**Purpose**: Tạo một document giả định trả lời câu hỏi, dùng để search

```python
# Input
"Thời hạn nộp hồ sơ dự thầu?"

# Output (hypothetical answer)
"""
Thời hạn nộp hồ sơ dự thầu được quy định tại Điều 9 Luật Đấu thầu 2023.
Theo đó, thời gian tối thiểu từ khi phát hành HSMT đến hạn nộp hồ sơ là:
- 30 ngày đối với đấu thầu quốc tế
- 20 ngày đối với đấu thầu trong nước
...
"""
```

**When to use**:
- Cần tìm documents có answer tương tự
- Query ngắn nhưng cần context dài

### 3. Step-Back Prompting
**Purpose**: Tạo câu hỏi tổng quát hơn để lấy broader context

```python
# Input (specific)
"Mức phạt vi phạm hợp đồng xây dựng trường học?"

# Output (step-back)
"Quy định về xử phạt vi phạm hợp đồng trong xây dựng công trình công cộng?"
```

**When to use**:
- Câu hỏi quá cụ thể
- Cần hiểu context rộng hơn

### 4. Query Decomposition
**Purpose**: Phân tách câu hỏi phức tạp thành sub-questions

```python
# Input (complex)
"So sánh quy trình đấu thầu xây dựng và mua sắm thiết bị y tế?"

# Output (decomposed)
[
    "Quy trình đấu thầu xây dựng công trình?",
    "Quy trình đấu thầu mua sắm thiết bị y tế?",
    "Điểm khác biệt giữa đấu thầu xây dựng và mua sắm?"
]
```

**When to use**:
- Câu hỏi có nhiều phần
- So sánh hoặc phân tích
- Câu hỏi "và"/"hoặc"

## 🧪 Testing

### Run Tests

```bash
# All query enhancement tests
pytest tests/unit/test_retrieval/ -v

# Specific test file
pytest tests/unit/test_retrieval/test_query_enhancer.py -v

# With coverage
pytest tests/unit/test_retrieval/ --cov=src.retrieval.query_processing
```

### Test Structure

```
tests/unit/test_retrieval/
├── test_query_enhancer.py          # Main enhancer tests
├── test_complexity_analyzer.py      # Complexity analysis tests
└── test_strategies/
    ├── test_multi_query.py
    ├── test_hyde.py
    ├── test_step_back.py
    └── test_decomposition.py
```

## 📊 Performance Considerations

### Caching Strategy
```python
# Query enhancement can be expensive (LLM calls)
# Use caching for repeated queries
config = QueryEnhancerConfig(
    enable_caching=True  # ✅ Recommended
)
```

### Batch Processing
```python
# For bulk processing, batch queries
queries = ["query1", "query2", "query3"]
enhanced_batch = enhancer.enhance_batch(queries)
```

### Rate Limiting
```python
# Control LLM API calls
config = QueryEnhancerConfig(
    max_queries=3,  # Limit enhanced queries
    strategies=[EnhancementStrategy.MULTI_QUERY]  # Use fewer strategies
)
```

## 🔗 Related Modules

- **Retrievers**: `src/retrieval/retrievers/`
- **Ranking**: `src/retrieval/ranking/`
- **Generation**: `src/generation/chains/`
- **Evaluation**: `src/evaluation/metrics/`

## 📚 References

- [LangChain Multi-Query](https://python.langchain.com/docs/modules/data_connection/retrievers/MultiQueryRetriever)
- [HyDE Paper](https://arxiv.org/abs/2212.10496)
- [Step-Back Prompting](https://arxiv.org/abs/2310.06117)
- [Query Decomposition Techniques](https://arxiv.org/abs/2205.10625)

## 🤝 Contributing

When implementing new strategies:

1. Create strategy file in `strategies/`
2. Inherit from base strategy class (TBD)
3. Implement `enhance()` method
4. Add tests
5. Update this README
6. Add usage examples

## 📝 TODO

- [ ] Implement all 4 strategies
- [ ] Add base Strategy abstract class
- [ ] Implement query caching with TTL
- [ ] Add Vietnamese-specific enhancements
- [ ] Benchmark each strategy
- [ ] Add strategy selection based on query type
- [ ] Implement hybrid strategies
- [ ] Add monitoring/logging for LLM calls
- [ ] Cost tracking for API calls
- [ ] A/B testing framework

---

**Last Updated**: October 12, 2025  
**Maintainer**: @sakanaowo  
**Status**: Active Development
