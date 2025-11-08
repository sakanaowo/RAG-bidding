"""
Test Upload Endpoints
Script to test file upload and processing functionality
"""

import requests
import time
import json
from pathlib import Path
import tempfile
from typing import List

# API Configuration
BASE_URL = "http://localhost:8000"
UPLOAD_URL = f"{BASE_URL}/upload"


def create_test_files() -> List[Path]:
    """Create sample test files for upload"""
    test_files = []

    # Create temp directory
    temp_dir = Path(tempfile.gettempdir()) / "rag_test_files"
    temp_dir.mkdir(exist_ok=True)

    # Sample Law document
    law_content = """
    LUẬT SỐ 123/2024/QH15
    VỀ ĐẦU TƯ CÔNG
    
    Căn cứ Hiến pháp nước Cộng hòa xã hội chủ nghĩa Việt Nam;
    Quốc hội ban hành Luật Đầu tư công.
    
    Chương I
    NHỮNG QUY ĐỊNH CHUNG
    
    Điều 1. Phạm vi điều chỉnh
    Luật này quy định về hoạt động đầu tư công...
    
    Điều 2. Đối tượng áp dụng
    1. Cơ quan nhà nước, tổ chức, cá nhân tham gia hoạt động đầu tư công.
    2. Tổ chức, cá nhân có liên quan đến hoạt động đầu tư công.
    """

    law_file = temp_dir / "luat_dau_tu_cong_2024.txt"
    law_file.write_text(law_content, encoding="utf-8")
    test_files.append(law_file)

    # Sample Decree document
    decree_content = """
    NGHỊ ĐỊNH SỐ 456/2024/NĐ-CP
    QUY ĐỊNH CHI TIẾT THI HÀNH LUẬT ĐẦU TƯ CÔNG
    
    Căn cứ Luật tổ chức Chính phủ;
    Căn cứ Luật Đầu tư công số 123/2024/QH15;
    Thủ tướng Chính phủ ban hành Nghị định này.
    
    Chương I
    QUY ĐỊNH CHUNG
    
    Điều 1. Phạm vi điều chỉnh
    Nghị định này quy định chi tiết việc thực hiện...
    """

    decree_file = temp_dir / "nghi_dinh_dau_tu_cong.txt"
    decree_file.write_text(decree_content, encoding="utf-8")
    test_files.append(decree_file)

    # Sample Bidding document
    bidding_content = """
    HỒ SƠ MỜI THẦU
    DỰ ÁN XÂY DỰNG TRƯỜNG HỌC
    
    1. THÔNG TIN CHUNG
    - Tên dự án: Xây dựng trường tiểu học ABC
    - Chủ đầu tư: UBND huyện XYZ
    - Giá trị gói thầu: 50 tỷ đồng
    
    2. YÊU CẦU KỸ THUẬT
    - Diện tích xây dựng: 5,000 m²
    - Số tầng: 3 tầng
    - Vật liệu: Bê tông cốt thép
    
    3. TIÊU CHÍ LỰA CHỌN NHÀ THẦU
    - Năng lực kinh nghiệm
    - Năng lực tài chính
    - Phương án kỹ thuật
    """

    bidding_file = temp_dir / "ho_so_moi_thau_truong_hoc.txt"
    bidding_file.write_text(bidding_content, encoding="utf-8")
    test_files.append(bidding_file)

    # Sample Other document
    other_content = """
    BÁO CÁO TÌNH HÌNH KINH TÊ 2024
    
    I. TỔNG QUAN
    Năm 2024 là năm có nhiều biến động trong nền kinh tế...
    
    II. CÁC CHỈ SỐ KINH TẾ
    1. GDP tăng trưởng: 6.5%
    2. Lạm phát: 3.2%
    3. Xuất khẩu: 350 tỷ USD
    
    III. KHUYẾN NGHỊ
    - Tăng cường đầu tư công nghệ
    - Phát triển nguồn nhân lực
    """

    other_file = temp_dir / "bao_cao_kinh_te_2024.txt"
    other_file.write_text(other_content, encoding="utf-8")
    test_files.append(other_file)

    print(f"✅ Created {len(test_files)} test files in {temp_dir}")
    return test_files


def test_classification(filename: str, content: str = None):
    """Test document classification endpoint"""
    print(f"\n📋 Testing classification for: {filename}")

    response = requests.post(
        f"{UPLOAD_URL}/classify", params={"filename": filename, "content": content}
    )

    if response.status_code == 200:
        result = response.json()
        print(f"   Type: {result['detected_type']}")
        print(f"   Confidence: {result['confidence']:.2f}")
        print(f"   Features: {', '.join(result['features_detected'])}")
        print(f"   Reasoning: {result['reasoning'][:100]}...")
        return result
    else:
        print(f"   ❌ Error: {response.status_code} - {response.text}")
        return None


def test_upload_files(file_paths: List[Path]):
    """Test file upload endpoint"""
    print(f"\n📤 Testing upload of {len(file_paths)} files...")

    # Prepare files for upload
    files = []
    for file_path in file_paths:
        files.append(("files", (file_path.name, open(file_path, "rb"), "text/plain")))

    # Upload parameters
    params = {
        "auto_classify": True,
        "chunk_size": 1000,
        "chunk_overlap": 200,
        "enable_enrichment": True,
        "enable_validation": True,
    }

    try:
        response = requests.post(f"{UPLOAD_URL}/files", files=files, params=params)

        # Close file handles
        for _, (_, file_handle, _) in files:
            file_handle.close()

        if response.status_code == 202:  # Accepted
            result = response.json()
            upload_id = result["upload_id"]
            print(f"   ✅ Upload started: {upload_id}")
            print(f"   Files received: {result['files_received']}")
            print(
                f"   Estimated time: {result.get('estimated_time_minutes', 'Unknown')} minutes"
            )
            return upload_id
        else:
            print(f"   ❌ Upload failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return None

    except Exception as e:
        print(f"   ❌ Upload error: {str(e)}")
        return None


def track_processing_status(upload_id: str, max_wait_minutes: int = 10):
    """Track processing status until completion"""
    print(f"\n⏳ Tracking processing status for: {upload_id}")

    start_time = time.time()
    max_wait_seconds = max_wait_minutes * 60

    while time.time() - start_time < max_wait_seconds:
        try:
            response = requests.get(f"{UPLOAD_URL}/status/{upload_id}")

            if response.status_code == 200:
                status = response.json()

                print(f"   Status: {status['status']}")
                print(
                    f"   Progress: {status['completed_files']}/{status['total_files']} files"
                )

                # Show per-file progress
                if "progress" in status:
                    for progress in status["progress"]:
                        file_status = progress.get("status", "unknown")
                        file_progress = progress.get("progress_percent", 0)
                        filename = progress.get("filename", "Unknown")
                        print(f"     {filename}: {file_status} ({file_progress}%)")

                # Check if completed
                if status["status"] in ["completed", "failed"]:
                    print(f"   ✅ Processing finished: {status['status']}")
                    return status

                time.sleep(5)  # Wait 5 seconds before next check

            else:
                print(f"   ❌ Status check failed: {response.status_code}")
                break

        except Exception as e:
            print(f"   ❌ Status check error: {str(e)}")
            break

    print(f"   ⏰ Timeout after {max_wait_minutes} minutes")
    return None


def test_supported_types():
    """Test supported types endpoint"""
    print("\n📚 Testing supported document types...")

    try:
        response = requests.get(f"{UPLOAD_URL}/supported-types")

        if response.status_code == 200:
            types_info = response.json()

            print("   Document Types:")
            for doc_type, info in types_info["document_types"].items():
                pipeline_status = "✅" if info.get("pipeline_available") else "⏳"
                print(f"     {doc_type}: {info['name_vi']} {pipeline_status}")

            print(f"\n   File Formats: {', '.join(types_info['file_formats'].keys())}")
            print(
                f"   Max files per batch: {types_info['processing_capabilities']['max_files_per_batch']}"
            )
            print(
                f"   Max file size: {types_info['processing_capabilities']['max_file_size_mb']} MB"
            )

        else:
            print(f"   ❌ Error: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"   ❌ Request error: {str(e)}")


def main():
    """Main test function"""
    print("🚀 Starting Upload Endpoint Tests")
    print("=" * 50)

    # Test 1: Check supported types
    test_supported_types()

    # Test 2: Create test files
    test_files = create_test_files()

    # Test 3: Test classification for each file
    for file_path in test_files:
        content = file_path.read_text(encoding="utf-8")
        test_classification(file_path.name, content)

    # Test 4: Upload files
    upload_id = test_upload_files(test_files)

    if upload_id:
        # Test 5: Track processing
        final_status = track_processing_status(upload_id, max_wait_minutes=10)

        if final_status:
            print(f"\n📊 Final Results:")
            print(f"   Total files: {final_status['total_files']}")
            print(f"   Completed: {final_status['completed_files']}")
            print(f"   Failed: {final_status['failed_files']}")

    # Cleanup test files
    print("\n🧹 Cleaning up test files...")
    for file_path in test_files:
        try:
            file_path.unlink()
        except:
            pass

    print("\n✅ Tests completed!")


if __name__ == "__main__":
    main()
