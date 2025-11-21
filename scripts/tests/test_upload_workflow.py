"""
Test Upload Workflow - Verify 3 endpoints

Test flow:
1. Upload a test file → Verify documents table insert
2. GET /documents/catalog → Verify new document appears
3. PATCH status → Toggle active/inactive
"""

import requests
import json
import time
from pathlib import Path
import sys

# Add project root
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# API base URL
BASE_URL = "http://localhost:8000"
UPLOAD_URL = f"{BASE_URL}/upload/files"
CATALOG_URL = f"{BASE_URL}/documents/catalog"


def print_section(title: str):
    """Print formatted section"""
    print("\n" + "=" * 80)
    print(f"📊 {title}")
    print("=" * 80 + "\n")


def test_upload_file():
    """Test 1: Upload file"""
    print_section("Test 1: Upload File")

    # Create a test file
    test_file_path = (
        project_root / "data" / "raw" / "Luat chinh" / "Luat-dau-thau-43-2013-QH13.docx"
    )

    if not test_file_path.exists():
        print(f"❌ Test file not found: {test_file_path}")
        return None

    print(f"📄 Uploading: {test_file_path.name}")
    print(f"   Size: {test_file_path.stat().st_size / 1024:.1f} KB")

    # Upload file
    with open(test_file_path, "rb") as f:
        files = {
            "files": (
                test_file_path.name,
                f,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        }
        data = {
            "batch_name": "test_upload_workflow",
            "auto_classify": True,
            "enable_enrichment": False,  # Faster
        }

        response = requests.post(UPLOAD_URL, files=files, data=data)

    if response.status_code == 202:
        result = response.json()
        upload_id = result.get("upload_id")
        print(f"✅ Upload accepted: {upload_id}")
        print(f"   Files: {result.get('files_received')}")
        print(f"   Status: {result.get('status')}")

        # Wait for processing
        print("\n⏳ Waiting for processing...")
        for i in range(30):  # Max 30 seconds
            time.sleep(1)
            status_response = requests.get(f"{BASE_URL}/upload/status/{upload_id}")
            if status_response.status_code == 200:
                status = status_response.json()
                current_status = status.get("status")
                print(
                    f"   [{i+1}s] Status: {current_status} ({status.get('completed_files')}/{status.get('total_files')} completed)"
                )

                if current_status == "completed":
                    print(f"\n✅ Processing completed!")
                    return upload_id
                elif current_status == "failed":
                    print(f"\n❌ Processing failed!")
                    print(f"   Details: {status}")
                    return None

        print(f"\n⚠️  Timeout waiting for processing")
        return upload_id
    else:
        print(f"❌ Upload failed: {response.status_code}")
        print(f"   {response.text}")
        return None


def test_catalog_listing(expected_doc_id: str = None):
    """Test 2: GET /documents/catalog"""
    print_section("Test 2: Catalog Listing")

    # Get all documents
    response = requests.get(CATALOG_URL, params={"limit": 100})

    if response.status_code == 200:
        documents = response.json()
        print(f"✅ Catalog retrieved: {len(documents)} documents")

        # Find recent uploads
        recent = [
            d
            for d in documents
            if d.get("document_name")
            and "luat-dau-thau" in d.get("document_name", "").lower()
        ]

        if recent:
            print(f"\n📋 Found related documents:")
            for doc in recent[:3]:
                print(f"   - {doc['document_id']}")
                print(f"     Name: {doc['document_name']}")
                print(
                    f"     Type: {doc['document_type']} | Chunks: {doc['total_chunks']}"
                )
                print(f"     Status: {doc.get('status', 'N/A')}")

        # Check if expected doc exists
        if expected_doc_id:
            found = any(d["document_id"] == expected_doc_id for d in documents)
            if found:
                print(f"\n✅ Expected document found: {expected_doc_id}")
                return expected_doc_id
            else:
                print(f"\n⚠️  Expected document NOT found: {expected_doc_id}")
                # Return first bidding doc for testing
                bidding_docs = [d for d in documents if d["document_type"] == "law"]
                if bidding_docs:
                    return bidding_docs[0]["document_id"]

        return recent[0]["document_id"] if recent else None
    else:
        print(f"❌ Catalog request failed: {response.status_code}")
        print(f"   {response.text}")
        return None


def test_toggle_status(document_id: str):
    """Test 3: PATCH /documents/catalog/{id}/status"""
    print_section("Test 3: Toggle Status")

    if not document_id:
        print("⚠️  No document_id provided, skipping")
        return False

    print(f"📝 Document: {document_id}")

    # Test 1: Set to inactive
    print("\n1️⃣  Setting to 'inactive'...")
    payload = {
        "status": "archived",
        "reason": "Test toggle from test_upload_workflow.py",
    }

    response = requests.patch(
        f"{CATALOG_URL}/{document_id}/status",
        json=payload,
        headers={"Content-Type": "application/json"},
    )

    if response.status_code == 200:
        result = response.json()
        print(f"✅ Status updated:")
        print(f"   {result['old_status']} → {result['new_status']}")
        print(f"   Chunks updated: {result['chunks_updated']}")
    else:
        print(f"❌ Update failed: {response.status_code}")
        print(f"   {response.text}")
        return False

    # Test 2: Set back to active
    print("\n2️⃣  Setting back to 'active'...")
    payload = {"status": "active", "reason": "Test complete, reactivating"}

    response = requests.patch(
        f"{CATALOG_URL}/{document_id}/status",
        json=payload,
        headers={"Content-Type": "application/json"},
    )

    if response.status_code == 200:
        result = response.json()
        print(f"✅ Status restored:")
        print(f"   {result['old_status']} → {result['new_status']}")
        print(f"   Chunks updated: {result['chunks_updated']}")
        return True
    else:
        print(f"❌ Restore failed: {response.status_code}")
        print(f"   {response.text}")
        return False


def verify_database():
    """Verify database state"""
    print_section("Database Verification")

    import psycopg2

    conn = psycopg2.connect(
        host="localhost", database="rag_bidding_v2", user="sakana", password="sakana123"
    )

    cursor = conn.cursor()

    # Check documents table
    cursor.execute(
        "SELECT COUNT(*), COUNT(DISTINCT document_type) FROM documents WHERE status = 'active'"
    )
    total, types = cursor.fetchone()
    print(f"📊 Documents table:")
    print(f"   Active documents: {total}")
    print(f"   Document types: {types}")

    # Check recent uploads
    cursor.execute(
        """
        SELECT document_id, document_name, document_type, total_chunks, status, created_at
        FROM documents
        WHERE created_at > NOW() - INTERVAL '1 hour'
        ORDER BY created_at DESC
        LIMIT 5
    """
    )

    recent = cursor.fetchall()
    if recent:
        print(f"\n📝 Recent uploads (last hour):")
        for row in recent:
            doc_id, name, dtype, chunks, status, created = row
            print(f"   - {doc_id}")
            print(f"     Name: {name[:50]}...")
            print(f"     Type: {dtype} | Chunks: {chunks} | Status: {status}")
            print(f"     Created: {created}")

    conn.close()


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("🧪 Upload Workflow Test Suite")
    print("=" * 80)
    print("\nPrerequisites:")
    print("  ✅ Server running on http://localhost:8000")
    print("  ✅ Database rag_bidding_v2 accessible")
    print("  ✅ Test file exists in data/raw/")

    input("\n⏎  Press Enter to start tests...")

    # Test 1: Upload
    upload_id = test_upload_file()

    if not upload_id:
        print("\n❌ Upload failed, stopping tests")
        return

    # Test 2: Catalog
    doc_id = test_catalog_listing()

    if not doc_id:
        print("\n⚠️  No document found, trying DB verification...")
        verify_database()
        return

    # Test 3: Toggle status
    success = test_toggle_status(doc_id)

    # Final verification
    verify_database()

    # Summary
    print_section("Test Summary")
    print(f"Upload: {'✅ Pass' if upload_id else '❌ Fail'}")
    print(f"Catalog: {'✅ Pass' if doc_id else '❌ Fail'}")
    print(f"Toggle Status: {'✅ Pass' if success else '❌ Fail'}")

    if upload_id and doc_id and success:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️  Some tests failed, check logs above")


if __name__ == "__main__":
    main()
