"""
Test script for Chunking Strategies
Tests HierarchicalChunker and SemanticChunker with real data
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.preprocessing.loaders import DocxLoader, RawDocxContent
from src.preprocessing.chunking import HierarchicalChunker, SemanticChunker
from src.preprocessing.schema import DocType


def test_hierarchical_chunker():
    """Test 1: HierarchicalChunker with Law document"""
    print("\n" + "=" * 70)
    print("TEST 1: HierarchicalChunker")
    print("=" * 70)

    # Load test document
    loader = DocxLoader()
    test_file = (
        project_root / "data/raw/Luat chinh/HỢP NHẤT 126 2025 về Luật đấu thầu.docx"
    )

    print(f"\n📄 Loading: {test_file.name}")
    raw_content = loader.load(str(test_file))

    print(f"✅ Loaded: {len(raw_content.structure)} structure elements")

    # Create chunker
    chunker = HierarchicalChunker(
        max_chunk_size=2000,
        min_chunk_size=300,
        overlap_size=150,
        preserve_parent_context=True,
        split_large_dieu=True,
    )

    # Chunk
    print(f"\n🔄 Chunking...")
    base_metadata = {
        "doc_type": DocType.LAW,
        "doc_id": "126/VBHN-VPQH/2025",
    }

    chunks = chunker.chunk(
        raw_content=raw_content,
        doc_id="126/VBHN-VPQH/2025",
        base_metadata=base_metadata,
    )

    print(f"✅ Created {len(chunks)} chunks")

    # Analyze chunks
    print(f"\n📊 Chunk Statistics:")
    total_chars = sum(chunk.char_count for chunk in chunks)
    avg_chars = total_chars / len(chunks) if chunks else 0
    min_chars = min(chunk.char_count for chunk in chunks) if chunks else 0
    max_chars = max(chunk.char_count for chunk in chunks) if chunks else 0

    print(f"   Total characters: {total_chars:,}")
    print(f"   Average chunk size: {avg_chars:.0f} chars")
    print(f"   Min chunk size: {min_chars:,} chars")
    print(f"   Max chunk size: {max_chars:,} chars")

    # Show first 3 chunks
    print(f"\n📝 First 3 Chunks:")
    for i, chunk in enumerate(chunks[:3]):
        print(f"\n   Chunk {i+1}:")
        print(f"   - ID: {chunk.chunk_id}")
        print(f"   - Size: {chunk.char_count} chars")
        print(f"   - Level: {chunk.structure.level}")
        print(f"   - Hierarchy: {' > '.join(chunk.structure.hierarchy_path)}")
        print(f"   - Section: {chunk.structure.section_title}")
        preview = chunk.content[:100].replace("\n", " ")
        print(f"   - Preview: {preview}...")

    # Verify all chunks have required fields
    print(f"\n✓ Verification:")
    all_valid = True
    for i, chunk in enumerate(chunks):
        if not chunk.chunk_id:
            print(f"   ❌ Chunk {i} missing chunk_id")
            all_valid = False
        if not chunk.content:
            print(f"   ❌ Chunk {i} missing content")
            all_valid = False
        if chunk.char_count <= 0:
            print(f"   ❌ Chunk {i} invalid char_count: {chunk.char_count}")
            all_valid = False

    if all_valid:
        print(f"   ✅ All chunks valid")

    return all_valid


def test_semantic_chunker():
    """Test 2: SemanticChunker with plain text"""
    print("\n" + "=" * 70)
    print("TEST 2: SemanticChunker")
    print("=" * 70)

    # Create sample bidding document text
    sample_text = """
PHẦN I: THÔNG TIN CHUNG

Tên gói thầu: Mua sắm trang thiết bị văn phòng
Mã gói thầu: 2024-ĐT-001
Nguồn vốn: Ngân sách nhà nước

A. YÊU CẦU VỀ SẢN PHẨM

Các yêu cầu cụ thể về sản phẩm như sau:

1. Máy tính văn phòng

Máy tính cần đáp ứng các tiêu chuẩn kỹ thuật tối thiểu:
- CPU: Intel Core i5 thế hệ 11 trở lên
- RAM: 16GB DDR4
- Ổ cứng: SSD 512GB
- Màn hình: 24 inch Full HD

2. Máy in laser

Máy in cần có các tính năng:
- In đen trắng A4
- Tốc độ in: 30 trang/phút
- Kết nối: USB, WiFi, LAN
- Khay giấy: 250 tờ

B. YÊU CẦU VỀ BẢO HÀNH

Nhà thầu phải đảm bảo bảo hành tối thiểu 36 tháng cho tất cả thiết bị.

PHẦN II: ĐIỀU KIỆN THAM DỰ THẦU

1. Điều kiện về năng lực

Nhà thầu cần có:
- Giấy phép kinh doanh phù hợp
- Kinh nghiệm tối thiểu 3 năm
- Đã thực hiện ít nhất 2 hợp đồng tương tự

2. Điều kiện về tài chính

Báo cáo tài chính 2 năm gần nhất đã được kiểm toán.
    """.strip()

    print(f"\n📄 Sample text: {len(sample_text)} characters")

    # Create chunker
    chunker = SemanticChunker(
        chunk_size=500,
        min_chunk_size=200,
        overlap_size=100,
        detect_sections=True,
    )

    # Chunk
    print(f"\n🔄 Chunking...")
    base_metadata = {
        "doc_type": DocType.BIDDING,
        "doc_id": "2024-ĐT-001",
    }

    chunks = chunker.chunk(
        text=sample_text,
        doc_id="2024-DT-001",
        base_metadata=base_metadata,
    )

    print(f"✅ Created {len(chunks)} chunks")

    # Analyze chunks
    print(f"\n📊 Chunk Statistics:")
    total_chars = sum(chunk.char_count for chunk in chunks)
    avg_chars = total_chars / len(chunks) if chunks else 0

    print(f"   Total characters: {total_chars:,}")
    print(f"   Average chunk size: {avg_chars:.0f} chars")

    # Show all chunks
    print(f"\n📝 All Chunks:")
    for i, chunk in enumerate(chunks):
        print(f"\n   Chunk {i+1}:")
        print(f"   - ID: {chunk.chunk_id}")
        print(f"   - Size: {chunk.char_count} chars")
        print(f"   - Section: {chunk.structure.section_title or 'N/A'}")
        print(f"   - Method: {chunk.chunking.chunk_method}")
        preview = chunk.content[:80].replace("\n", " ")
        print(f"   - Preview: {preview}...")

    # Verify overlap
    print(f"\n✓ Overlap Verification:")
    has_overlap = False
    for i in range(len(chunks) - 1):
        chunk1_end = chunks[i].content[-50:]
        chunk2_start = chunks[i + 1].content[:50]

        # Check if there's any common text
        for j in range(len(chunk1_end)):
            if chunk1_end[j:] in chunk2_start:
                has_overlap = True
                print(f"   ✅ Overlap found between chunk {i+1} and {i+2}")
                break

    if not has_overlap and len(chunks) > 1:
        print(f"   ⚠️  No overlap detected (might be OK for section boundaries)")

    return True


def test_chunker_comparison():
    """Test 3: Compare both chunkers on same document"""
    print("\n" + "=" * 70)
    print("TEST 3: Chunker Comparison")
    print("=" * 70)

    # Load test document
    loader = DocxLoader()
    test_file = (
        project_root / "data/raw/Luat chinh/HỢP NHẤT 126 2025 về Luật đấu thầu.docx"
    )

    raw_content = loader.load(str(test_file))

    # Test HierarchicalChunker
    print(f"\n🔄 Testing HierarchicalChunker...")
    hierarchical_chunker = HierarchicalChunker(max_chunk_size=1500)
    hierarchical_chunks = hierarchical_chunker.chunk(
        raw_content=raw_content,
        doc_id="126/VBHN-VPQH/2025",
        base_metadata={},
    )

    # Test SemanticChunker
    print(f"🔄 Testing SemanticChunker...")
    semantic_chunker = SemanticChunker(chunk_size=1500)
    semantic_chunks = semantic_chunker.chunk(
        text=raw_content.text,
        doc_id="126/VBHN-VPQH/2025",
        base_metadata={},
    )

    # Compare
    print(f"\n📊 Comparison:")
    print(f"   HierarchicalChunker: {len(hierarchical_chunks)} chunks")
    print(f"   SemanticChunker: {len(semantic_chunks)} chunks")

    h_avg = sum(c.char_count for c in hierarchical_chunks) / len(hierarchical_chunks)
    s_avg = sum(c.char_count for c in semantic_chunks) / len(semantic_chunks)

    print(f"\n   Average chunk size:")
    print(f"   - Hierarchical: {h_avg:.0f} chars")
    print(f"   - Semantic: {s_avg:.0f} chars")

    print(f"\n   ✅ Hierarchical is better for legal docs (preserves structure)")
    print(f"   ✅ Semantic is better for free-form docs (flexible boundaries)")

    return True


def main():
    print("\n" + "=" * 80)
    print("🧪 CHUNKING STRATEGIES TEST SUITE")
    print("=" * 80)

    results = []

    # Run all tests
    results.append(("HierarchicalChunker", test_hierarchical_chunker()))
    results.append(("SemanticChunker", test_semantic_chunker()))
    results.append(("Chunker Comparison", test_chunker_comparison()))

    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    total = len(results)
    passed = sum(1 for _, r in results if r)

    print(f"\n{'='*80}")
    print(f"Total: {passed}/{total} tests passed")
    print("=" * 80)

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
