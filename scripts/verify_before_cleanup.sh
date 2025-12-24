#!/bin/bash
# Verification Script - Check Before Cleanup
# Run: bash scripts/verify_before_cleanup.sh

echo "🔍 VERIFICATION REPORT - Files to be Cleaned Up"
echo "=" | awk '{for(i=1;i<=70;i++)printf "="}END{print ""}'
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check 1: Empty Reranker Files
echo "1️⃣  EMPTY RERANKER FILES (to be DELETED)"
echo "---"
for file in cohere_reranker.py cross_encoder_reranker.py legal_score_reranker.py llm_reranker.py; do
    filepath="src/retrieval/ranking/$file"
    if [ -f "$filepath" ]; then
        lines=$(wc -l < "$filepath")
        has_class=$(grep -c "^class " "$filepath" || echo 0)
        has_def=$(grep -c "^def " "$filepath" || echo 0)
        
        if [ $has_class -eq 0 ] && [ $has_def -eq 0 ]; then
            echo -e "${GREEN}✅ $file${NC} - $lines lines, no implementation"
        else
            echo -e "${RED}⚠️  $file${NC} - $lines lines, HAS CODE! (has_class=$has_class, has_def=$has_def)"
        fi
    else
        echo -e "${YELLOW}⚠️  $file - NOT FOUND${NC}"
    fi
done
echo ""

# Check 2: Files importing deprecated rerankers
echo "2️⃣  FILES IMPORTING DEPRECATED RERANKERS"
echo "---"
deprecated_imports=$(grep -r "from.*\(cohere_reranker\|cross_encoder_reranker\|legal_score_reranker\|llm_reranker\)" \
    src/ scripts/ --include="*.py" 2>/dev/null | grep -v "__pycache__" | grep -v "\.pyc")

if [ -z "$deprecated_imports" ]; then
    echo -e "${GREEN}✅ No files import deprecated rerankers (except __init__.py with try/except)${NC}"
else
    echo -e "${RED}⚠️  Found imports:${NC}"
    echo "$deprecated_imports"
fi
echo ""

# Check 3: PhoBERT usage in production
echo "3️⃣  PHOBERT USAGE IN PRODUCTION CODE"
echo "---"
phobert_prod=$(grep -r "PhoBERTReranker" src/ --include="*.py" 2>/dev/null | \
    grep -v "__pycache__" | grep -v "test" | grep -v "\.pyc" | grep -v "docstring" | grep -v "#")

if [ -z "$phobert_prod" ]; then
    echo -e "${GREEN}✅ PhoBERT NOT used in production (only in tests)${NC}"
else
    echo -e "${YELLOW}⚠️  PhoBERT found in production:${NC}"
    echo "$phobert_prod"
fi
echo ""

# Check 4: Legacy test files
echo "4️⃣  LEGACY TEST FILES (to be DELETED)"
echo "---"
for file in scripts/tests/legacy_test_upload_api.py scripts/test_upload_v3.py; do
    if [ -f "$file" ]; then
        lines=$(wc -l < "$file")
        echo -e "${GREEN}✅ $file${NC} - $lines lines"
        
        # Check if it's actually legacy
        if grep -q "legacy\|Legacy\|OLD\|deprecated" "$file"; then
            echo "   → Contains legacy markers: ✅"
        else
            echo "   → No legacy markers found: ⚠️  (check manually)"
        fi
    else
        echo -e "${YELLOW}⚠️  $file - NOT FOUND${NC}"
    fi
done
echo ""

# Check 5: Temp files
echo "5️⃣  TEMP FILES (to be DELETED)"
echo "---"
temp_files=(
    "temp/CONVERSATION_SUMMARY_DETAILED.md"
    "temp/detailed_schema_analysis.md"
    "temp/make.sql"
    "temp/proposed_schema_v3.md"
    "temp/REFACTORING_PLAN.md"
    "temp/REFACTORING_PLAN_REVIEW_VI.md"
    "temp/step4_completion_report.md"
)

total_size=0
for file in "${temp_files[@]}"; do
    if [ -f "$file" ]; then
        size=$(du -h "$file" | cut -f1)
        echo -e "${GREEN}✅ $file${NC} - $size"
        # Add to total (in KB)
        kb=$(du -k "$file" | cut -f1)
        total_size=$((total_size + kb))
    else
        echo -e "${YELLOW}⚠️  $file - NOT FOUND${NC}"
    fi
done
echo "   Total: ${total_size}KB"
echo ""

# Check 6: Old data folder
echo "6️⃣  OLD DATA FOLDER (to be ARCHIVED)"
echo "---"
if [ -d "data/processed_old" ]; then
    size=$(du -sh data/processed_old | cut -f1)
    file_count=$(find data/processed_old -type f | wc -l)
    echo -e "${GREEN}✅ data/processed_old/${NC} - $size ($file_count files)"
    echo "   Will be moved to: data/archive/processed_old_$(date +%Y%m%d)/"
else
    echo -e "${YELLOW}⚠️  data/processed_old/ - NOT FOUND${NC}"
fi
echo ""

# Check 7: Current active tests still work?
echo "7️⃣  VERIFY CORE TESTS STILL EXIST"
echo "---"
core_tests=(
    "scripts/tests/test_core_system.py"
    "scripts/tests/test_singleton_production.py"
    "scripts/tests/unit/test_singleton_reranker.py"
    "scripts/tests/test_db_connection.py"
    "scripts/tests/test_api_server.py"
)

for test in "${core_tests[@]}"; do
    if [ -f "$test" ]; then
        echo -e "${GREEN}✅ $test${NC}"
    else
        echo -e "${RED}❌ $test - MISSING!${NC}"
    fi
done
echo ""

# Check 8: Production reranker intact?
echo "8️⃣  PRODUCTION RERANKER (BGE) INTACT"
echo "---"
if [ -f "src/retrieval/ranking/bge_reranker.py" ]; then
    lines=$(wc -l < "src/retrieval/ranking/bge_reranker.py")
    has_class=$(grep -c "^class BGEReranker" "src/retrieval/ranking/bge_reranker.py")
    has_singleton=$(grep -c "get_singleton_reranker" "src/retrieval/ranking/bge_reranker.py")
    
    if [ $has_class -gt 0 ] && [ $has_singleton -gt 0 ]; then
        echo -e "${GREEN}✅ bge_reranker.py${NC} - $lines lines, singleton pattern present"
    else
        echo -e "${RED}⚠️  bge_reranker.py${NC} - Potential issues (class=$has_class, singleton=$has_singleton)"
    fi
else
    echo -e "${RED}❌ bge_reranker.py - MISSING!${NC}"
fi
echo ""

# Summary
echo "=" | awk '{for(i=1;i<=70;i++)printf "="}END{print ""}'
echo "📊 SUMMARY"
echo "=" | awk '{for(i=1;i<=70;i++)printf "="}END{print ""}'
echo ""
echo "Files to DELETE (17 files, ~230KB):"
echo "  - 4 empty reranker files"
echo "  - 2 legacy test files"
echo "  - 11 temp files"
echo ""
echo "Files to ARCHIVE (keep as backup):"
echo "  - 4 PhoBERT test files → scripts/tests/archived/"
echo "  - 1 archived doc → documents/archived/"
echo "  - data/processed_old/ → data/archive/"
echo ""
echo "Files to KEEP:"
echo "  - bge_reranker.py (production)"
echo "  - openai_reranker.py (production alternative)"
echo "  - All core tests"
echo ""
echo "⚠️  REVIEW CAREFULLY BEFORE PROCEEDING!"
echo ""
echo "Next steps:"
echo "  1. Review output above"
echo "  2. If all checks pass → Run: bash scripts/cleanup_phase2.sh"
echo "  3. After cleanup → Run tests: python scripts/tests/test_core_system.py"
echo ""
