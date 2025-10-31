"""
Test script for DocxLoader
Tests DOCX loading and Vietnamese legal document extraction
"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.preprocessing.loaders import DocxLoader, RawDocxContent


def test_docx_loader_basic():
    """Test 1: Basic DOCX loading"""
    print("\n" + "="*60)
    print("TEST 1: Basic DOCX Loading")
    print("="*60)
    
    loader = DocxLoader()
    test_file = project_root / "data/raw/Luat chinh/HỢP NHẤT 126 2025 về Luật đấu thầu.docx"
    
    print(f"\n📄 Loading: {test_file.name}")
    
    try:
        result = loader.load(str(test_file))
        
        print(f"\n✅ Successfully loaded!")
        print(f"   - Text length: {len(result.text):,} characters")
        print(f"   - Metadata keys: {list(result.metadata.keys())}")
        print(f"   - Structure elements: {len(result.structure)} items")
        print(f"   - Tables extracted: {len(result.tables)}")
        
        # Print metadata
        print(f"\n📋 Metadata:")
        for key, value in result.metadata.items():
            if key != "filename":  # Skip filename (too long)
                print(f"   - {key}: {value}")
        
        # Print statistics
        print(f"\n📊 Statistics:")
        for key, value in result.statistics.items():
            print(f"   - {key}: {value:,}" if isinstance(value, int) else f"   - {key}: {value}")
        
        return True
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_docx_loader_structure():
    """Test 2: Structure extraction"""
    print("\n" + "="*60)
    print("TEST 2: Structure Extraction")
    print("="*60)
    
    loader = DocxLoader()
    test_file = project_root / "data/raw/Luat chinh/HỢP NHẤT 126 2025 về Luật đấu thầu.docx"
    
    try:
        result = loader.load(str(test_file))
        
        print(f"\n📑 Document Structure:")
        
        # Group by type
        structure_by_type = {}
        for item in result.structure:
            item_type = item["type"]
            if item_type not in structure_by_type:
                structure_by_type[item_type] = []
            structure_by_type[item_type].append(item)
        
        for item_type, items in structure_by_type.items():
            print(f"\n   {item_type.upper()}: {len(items)} items")
            # Show first 3 examples
            for i, item in enumerate(items[:3]):
                text = item["text"][:60] + "..." if len(item["text"]) > 60 else item["text"]
                print(f"      {i+1}. {text}")
                if "number" in item:
                    print(f"         Number: {item['number']}")
        
        return True
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_docx_loader_all_types():
    """Test 3: Test different document types"""
    print("\n" + "="*60)
    print("TEST 3: Different Document Types")
    print("="*60)
    
    loader = DocxLoader()
    
    test_files = [
        "data/raw/Luat chinh/HỢP NHẤT 126 2025 về Luật đấu thầu.docx",
        "data/raw/Nghi dinh/43-2013-ND-CP.docx",  # If exists
        "data/raw/Thong tu/08-2013-TT-BKHCN.docx",  # If exists
    ]
    
    for test_path in test_files:
        full_path = project_root / test_path
        if not full_path.exists():
            print(f"\n⏭️  Skipping (not found): {test_path}")
            continue
        
        print(f"\n📄 Testing: {full_path.name}")
        
        try:
            result = loader.load(str(full_path))
            
            doc_type = result.metadata.get("doc_type", "unknown")
            doc_number = result.metadata.get("doc_number", "N/A")
            
            print(f"   ✅ Type: {doc_type}")
            print(f"   📝 Number: {doc_number}")
            print(f"   📏 Length: {len(result.text):,} chars")
            print(f"   🏗️  Structure: {len(result.structure)} elements")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    return True


def test_docx_loader_hierarchy():
    """Test 4: Hierarchy detection"""
    print("\n" + "="*60)
    print("TEST 4: Hierarchy Detection")
    print("="*60)
    
    loader = DocxLoader()
    test_file = project_root / "data/raw/Luat chinh/HỢP NHẤT 126 2025 về Luật đấu thầu.docx"
    
    try:
        result = loader.load(str(test_file))
        
        # Check hierarchy levels
        hierarchy_levels = ["phan", "chuong", "muc", "dieu", "khoan", "diem"]
        
        print(f"\n🏗️  Hierarchy Detection Results:")
        for level in hierarchy_levels:
            items = [item for item in result.structure if item["type"] == level]
            if items:
                print(f"\n   {level.upper()}: {len(items)} found")
                # Show first 2 examples
                for i, item in enumerate(items[:2]):
                    number = item.get("number", "?")
                    text = item["text"][:50] + "..." if len(item["text"]) > 50 else item["text"]
                    print(f"      {i+1}. [{number}] {text}")
        
        return True
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n" + "="*80)
    print("🧪 DOCX LOADER TEST SUITE")
    print("="*80)
    
    results = []
    
    # Run all tests
    results.append(("Basic Loading", test_docx_loader_basic()))
    results.append(("Structure Extraction", test_docx_loader_structure()))
    results.append(("Document Types", test_docx_loader_all_types()))
    results.append(("Hierarchy Detection", test_docx_loader_hierarchy()))
    
    # Summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    total = len(results)
    passed = sum(1 for _, r in results if r)
    
    print(f"\n{'='*80}")
    print(f"Total: {passed}/{total} tests passed")
    print("="*80)
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
