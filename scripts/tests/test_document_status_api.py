"""
Test script đơn giản cho Document Status API
"""

import requests
import json

BASE_URL = "http://localhost:8000/api/document-status"


def test_get_status(document_id: str):
    """Test lấy status của một document"""
    print(f"\n{'='*60}")
    print(f"🔍 Test GET status: {document_id}")
    print(f"{'='*60}")

    # Use query parameter instead of path parameter
    response = requests.get(BASE_URL, params={"document_id": document_id})
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(f"Error: {response.text}")

    return response


def test_update_status(
    document_id: str, new_status: str, reason: str = None, superseded_by: str = None
):
    """Test cập nhật status của một document"""
    print(f"\n{'='*60}")
    print(f"✏️  Test UPDATE status: {document_id} → {new_status}")
    print(f"{'='*60}")

    payload = {
        "document_id": document_id,
        "new_status": new_status,
    }

    if reason:
        payload["reason"] = reason
    if superseded_by:
        payload["superseded_by"] = superseded_by

    print(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")

    response = requests.post(f"{BASE_URL}/update", json=payload)
    print(f"\nStatus Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(f"Error: {response.text}")

    return response


def main():
    """Chạy test scenarios"""
    print("🚀 Bắt đầu test Document Status API")
    print(f"🌐 Server: {BASE_URL}\n")

    # Test 1: Lấy status của một document hiện có
    print("\n" + "=" * 60)
    print("TEST 1: Lấy status của document hiện có")
    print("=" * 60)
    # Thử với document ID mới (sau migration)
    response = test_get_status("FORM-Bidding/2025#bee720")

    if response.status_code == 200:
        current_data = response.json()
        print(f"\n✅ Document tồn tại với status: {current_data['current_status']}")
        print(f"   Số chunks: {current_data['chunk_count']}")
    else:
        print(f"\n⚠️  Document không tồn tại, thử với document khác...")
        # Thử với các document ID mới sau migration
        for doc_id in [
            "TT-Circular/2025#3be8b6",
            "ND-Decree/2025#95b863",
            "LAW-Law/2025#cd5116",
        ]:
            response = test_get_status(doc_id)
            if response.status_code == 200:
                current_data = response.json()
                print(f"\n✅ Tìm thấy document: {doc_id}")
                print(f"   Status: {current_data['current_status']}")
                print(f"   Số chunks: {current_data['chunk_count']}")
                break

    # Test 2: Cập nhật status thành EXPIRED
    print("\n" + "=" * 60)
    print("TEST 2: Đánh dấu document hết hạn (EXPIRED)")
    print("=" * 60)
    test_update_status(
        document_id="TT-Circular/2025#3be8b6",
        new_status="expired",
        reason="Văn bản hết hạn theo quy định",
    )

    # Test 3: Kiểm tra lại status sau khi update
    print("\n" + "=" * 60)
    print("TEST 3: Kiểm tra status sau khi cập nhật")
    print("=" * 60)
    test_get_status("TT-Circular/2025#3be8b6")

    # Test 4: Cập nhật status thành SUPERSEDED với link tới document thay thế
    print("\n" + "=" * 60)
    print("TEST 4: Đánh dấu document bị thay thế (SUPERSEDED)")
    print("=" * 60)
    test_update_status(
        document_id="ND-Decree/2025#95b863",
        new_status="superseded",
        reason="Được thay thế bởi Nghị định 50/2024/NĐ-CP",
        superseded_by="ND-50/2024#abc123",
    )

    # Test 5: Kiểm tra document bị thay thế
    print("\n" + "=" * 60)
    print("TEST 5: Kiểm tra document sau khi đánh dấu superseded")
    print("=" * 60)
    response = test_get_status("ND-Decree/2025#95b863")
    if response.status_code == 200:
        data = response.json()
        if data.get("superseded_by"):
            print(
                f"\n✅ Document đã được đánh dấu superseded_by: {data['superseded_by']}"
            )

    # Test 6: Reactivate document
    print("\n" + "=" * 60)
    print("TEST 6: Kích hoạt lại document (ACTIVE)")
    print("=" * 60)
    test_update_status(
        document_id="TT-Circular/2025#3be8b6",
        new_status="active",
        reason="Văn bản được gia hạn hiệu lực",
    )

    # Test 7: Test với document không tồn tại
    print("\n" + "=" * 60)
    print("TEST 7: Test với document không tồn tại")
    print("=" * 60)
    test_get_status("nonexistent_doc_12345")

    print("\n" + "=" * 60)
    print("✅ Hoàn thành tất cả test cases!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n❌ Lỗi: Không thể kết nối tới server!")
        print("💡 Hãy đảm bảo server đang chạy tại http://localhost:8000")
    except Exception as e:
        print(f"\n❌ Lỗi không mong đợi: {e}")
        import traceback

        traceback.print_exc()
