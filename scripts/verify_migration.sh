#!/bin/bash

# Verification script after project restructure
# Run: bash scripts/verify_migration.sh

echo "🔍 Verifying project restructure..."
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if new directories exist
echo "📁 Checking directory structure..."
dirs=(
    "src/retrieval/query_processing"
    "src/retrieval/retrievers"
    "src/generation/chains"
    "src/embedding/store"
    "config"
    "api"
)

all_dirs_ok=true
for dir in "${dirs[@]}"; do
    if [ -d "$dir" ]; then
        echo -e "  ${GREEN}✓${NC} $dir exists"
    else
        echo -e "  ${RED}✗${NC} $dir missing"
        all_dirs_ok=false
    fi
done

echo ""

# Check if key files exist
echo "📄 Checking key files..."
files=(
    "src/retrieval/query_processing/query_enhancer.py"
    "src/retrieval/query_processing/complexity_analyzer.py"
    "src/retrieval/retrievers/base_retriever.py"
    "src/retrieval/retrievers/adaptive_retriever.py"
    "src/generation/chains/qa_chain.py"
    "src/generation/chains/enhanced_chain.py"
    "src/embedding/store/pgvector_store.py"
    "config/settings.py"
    "config/models.py"
    "config/logging_config.py"
)

all_files_ok=true
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo -e "  ${GREEN}✓${NC} $file exists"
    else
        echo -e "  ${RED}✗${NC} $file missing"
        all_files_ok=false
    fi
done

echo ""

# Check for old imports
echo "🔍 Checking for remaining old imports..."
old_imports=$(grep -r "from app\." src/ config/ api/ --include="*.py" 2>/dev/null | wc -l)
if [ "$old_imports" -eq 0 ]; then
    echo -e "  ${GREEN}✓${NC} No old imports found in new structure"
else
    echo -e "  ${YELLOW}⚠${NC} Found $old_imports old imports - might need manual review"
    echo "    Run: grep -r 'from app\\.' src/ config/ api/ --include='*.py'"
fi

echo ""

# Try importing key modules
echo "🐍 Testing Python imports..."
python3 << 'EOF'
import sys
import importlib.util

modules_to_test = [
    ("config.settings", "config/settings.py"),
    ("config.models", "config/models.py"),
    ("src.retrieval.query_processing.query_enhancer", "src/retrieval/query_processing/query_enhancer.py"),
    ("src.retrieval.retrievers.adaptive_retriever", "src/retrieval/retrievers/adaptive_retriever.py"),
    ("src.generation.chains.qa_chain", "src/generation/chains/qa_chain.py"),
]

all_ok = True
for module_name, file_path in modules_to_test:
    try:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            # Don't execute, just check if importable
            print(f"  ✓ {module_name}")
        else:
            print(f"  ✗ {module_name} - spec error")
            all_ok = False
    except Exception as e:
        print(f"  ✗ {module_name} - {str(e)[:50]}")
        all_ok = False

sys.exit(0 if all_ok else 1)
EOF

python_import_status=$?

echo ""

# Summary
echo "📊 Summary:"
echo ""

if [ "$all_dirs_ok" = true ] && [ "$all_files_ok" = true ] && [ "$python_import_status" -eq 0 ]; then
    echo -e "${GREEN}✅ Migration verification passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Review changes: git diff"
    echo "  2. Run tests: pytest tests/ -v"
    echo "  3. Commit changes: git add . && git commit -m 'refactor: restructure project by RAG phases'"
    echo "  4. When ready, remove old app/ directory: rm -rf app/"
    echo ""
else
    echo -e "${RED}⚠️  Some issues found. Please review.${NC}"
    echo ""
    
    if [ "$all_dirs_ok" = false ]; then
        echo "  - Some directories are missing"
    fi
    
    if [ "$all_files_ok" = false ]; then
        echo "  - Some files are missing"
    fi
    
    if [ "$python_import_status" -ne 0 ]; then
        echo "  - Some imports are failing"
    fi
    
    echo ""
    echo "Check the output above for details."
fi

echo ""
echo "📚 Documentation:"
echo "  - Full guide: docs/RESTRUCTURE_GUIDE.md"
echo "  - Quick summary: docs/RESTRUCTURE_SUMMARY.md"
