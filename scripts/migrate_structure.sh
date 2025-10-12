#!/bin/bash

# Migration script for restructuring RAG-bidding project
# Run from project root: bash scripts/migrate_structure.sh

set -e  # Exit on error

echo "🚀 Starting project restructure migration..."

# Create necessary directories if they don't exist
echo "📁 Creating directory structure..."

# Ingestion directories
mkdir -p src/ingestion/crawlers
mkdir -p src/ingestion/extractors
mkdir -p src/ingestion/validators

# Preprocessing directories
mkdir -p src/preprocessing/cleaners
mkdir -p src/preprocessing/parsers
mkdir -p src/preprocessing/metadata

# Chunking directories
mkdir -p src/chunking/strategies

# Retrieval directories (Query Enhancement)
mkdir -p src/retrieval/query_processing/strategies
mkdir -p src/retrieval/retrievers
mkdir -p src/retrieval/ranking
mkdir -p src/retrieval/filters

# Generation directories
mkdir -p src/generation/chains
mkdir -p src/generation/prompts
mkdir -p src/generation/formatters
mkdir -p src/generation/validators

# Evaluation directories
mkdir -p src/evaluation/metrics
mkdir -p src/evaluation/benchmarks

# API directories
mkdir -p api/routers
mkdir -p api/schemas
mkdir -p api/middleware

# Test directories
mkdir -p tests/unit/test_retrieval
mkdir -p tests/integration
mkdir -p tests/fixtures

# Documentation
mkdir -p docs/phases
mkdir -p docs/guides

echo "✅ Directory structure created!"

# Move Data Processing files
echo "📦 Moving data processing files..."

# Crawlers
if [ -f "app/data/crawler/thuvienphapluat_crawler.py" ]; then
    mv app/data/crawler/thuvienphapluat_crawler.py src/ingestion/crawlers/
    echo "  ✓ Moved crawler"
fi

# OCR processors
if [ -d "app/data/ocr-process" ]; then
    cp -r app/data/ocr-process/* src/ingestion/extractors/ 2>/dev/null || true
    echo "  ✓ Copied OCR processors"
fi

# Markdown preprocessors
if [ -d "app/data/core/md-preprocess" ]; then
    cp -r app/data/core/md-preprocess/* src/preprocessing/parsers/ 2>/dev/null || true
    echo "  ✓ Copied markdown preprocessors"
fi

# Chunking
if [ -f "app/data/core/optimal_chunker.py" ]; then
    mv app/data/core/optimal_chunker.py src/chunking/
    echo "  ✓ Moved optimal_chunker"
fi

if [ -f "app/data/core/chunk-strategy.py" ]; then
    mv app/data/core/chunk-strategy.py src/chunking/strategies/
    echo "  ✓ Moved chunk strategy"
fi

echo "✅ Data processing files moved!"

# Move RAG Components
echo "🔍 Moving RAG components..."

# Query Enhancement
if [ -f "app/rag/query_enhancement.py" ]; then
    mv app/rag/query_enhancement.py src/retrieval/query_processing/query_enhancer.py
    echo "  ✓ Moved query_enhancement.py → query_enhancer.py"
fi

if [ -f "app/rag/QuestionComplexAnalyzer.py" ]; then
    mv app/rag/QuestionComplexAnalyzer.py src/retrieval/query_processing/complexity_analyzer.py
    echo "  ✓ Moved QuestionComplexAnalyzer.py → complexity_analyzer.py"
fi

# Retrievers
if [ -f "app/rag/retriever.py" ]; then
    mv app/rag/retriever.py src/retrieval/retrievers/base_retriever.py
    echo "  ✓ Moved retriever.py → base_retriever.py"
fi

if [ -f "app/rag/adaptive_retriever.py" ]; then
    mv app/rag/adaptive_retriever.py src/retrieval/retrievers/adaptive_retriever.py
    echo "  ✓ Moved adaptive_retriever.py"
fi

# Chains
if [ -f "app/rag/chain.py" ]; then
    mv app/rag/chain.py src/generation/chains/qa_chain.py
    echo "  ✓ Moved chain.py → qa_chain.py"
fi

if [ -f "app/rag/enhanced_chain.py" ]; then
    mv app/rag/enhanced_chain.py src/generation/chains/enhanced_chain.py
    echo "  ✓ Moved enhanced_chain.py"
fi

# Prompts
if [ -f "app/rag/prompts.py" ]; then
    mv app/rag/prompts.py src/generation/prompts/qa_prompts.py
    echo "  ✓ Moved prompts.py → qa_prompts.py"
fi

# Evaluation
if [ -f "app/rag/eval.py" ]; then
    mv app/rag/eval.py src/evaluation/metrics/retrieval_metrics.py
    echo "  ✓ Moved eval.py → retrieval_metrics.py"
fi

echo "✅ RAG components moved!"

# Move API files
echo "🌐 Moving API files..."

if [ -f "app/api/main.py" ]; then
    cp app/api/main.py api/main.py
    echo "  ✓ Copied API main.py"
fi

echo "✅ API files moved!"

# Create __init__.py files
echo "📝 Creating __init__.py files..."

find src -type d -exec touch {}/__init__.py \;
find api -type d -exec touch {}/__init__.py \;

echo "✅ __init__.py files created!"

echo ""
echo "🎉 Migration completed successfully!"
echo ""
echo "Next steps:"
echo "1. Review moved files in src/ directory"
echo "2. Run: python scripts/update_imports.py"
echo "3. Test imports: python -m pytest tests/"
echo "4. Remove old app/ directory when ready: rm -rf app/"
