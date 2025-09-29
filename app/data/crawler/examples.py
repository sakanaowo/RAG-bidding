#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example script cho Thuvienphapluat Crawler Module

File này minh họa các cách sử dụng khác nhau của crawler module.
"""

import os
import sys

# Thêm thư mục hiện tại vào Python path
sys.path.insert(0, os.path.dirname(__file__))

from thuvienphapluat_crawler import (
    ThuvienphapluatCrawler,
    crawl_and_export_to_markdown,
    batch_crawl_urls,
)


def example_1_simple_usage():
    """
    Example 1: Sử dụng đơn giản với convenience functions
    """
    print("📖 Example 1: Sử dụng đơn giản")
    print("=" * 40)

    # URL để test
    url = "https://thuvienphapluat.vn/van-ban/Dau-tu/Nghi-dinh-214-2025-ND-CP-huong-dan-Luat-Dau-thau-ve-lua-chon-nha-thau-668157.aspx"

    # Crawl và export
    result = crawl_and_export_to_markdown(url=url, output_dir="./examples_output/")

    if result:
        print(f"✅ Thành công! File được lưu tại: {result}")
    else:
        print("❌ Crawl thất bại!")

    return result is not None


def example_2_batch_crawling():
    """
    Example 2: Crawl nhiều URL cùng lúc
    """
    print("\n📖 Example 2: Batch crawling")
    print("=" * 40)

    # Danh sách URL (chỉ dùng 1 URL để demo, tránh spam)
    urls = [
        "https://thuvienphapluat.vn/van-ban/Dau-tu/Nghi-dinh-214-2025-ND-CP-huong-dan-Luat-Dau-thau-ve-lua-chon-nha-thau-668157.aspx",
        # Có thể thêm URLs khác ở đây
    ]

    # Batch crawl với delay 2 giây
    results = batch_crawl_urls(urls=urls, output_dir="./examples_output/", delay=2)

    # Kiểm tra kết quả
    successful = sum(1 for r in results if r["success"])
    print(f"\nKết quả: {successful}/{len(urls)} URLs thành công")

    return successful > 0


def example_3_advanced_usage():
    """
    Example 3: Sử dụng nâng cao với ThuvienphapluatCrawler class
    """
    print("\n📖 Example 3: Sử dụng nâng cao")
    print("=" * 40)

    # Khởi tạo crawler với cấu hình tùy chỉnh
    crawler = ThuvienphapluatCrawler(
        user_agent="RAG-Bidding-Bot/1.0",
        timeout=60,
        default_output_dir="./examples_output/",
    )

    # URL để test
    url = "https://thuvienphapluat.vn/van-ban/Dau-tu/Nghi-dinh-214-2025-ND-CP-huong-dan-Luat-Dau-thau-ve-lua-chon-nha-thau-668157.aspx"

    # Crawl single URL
    result = crawler.crawl_single_url(url)

    if result:
        print(f"✅ Advanced crawl thành công! File: {result}")

        # Hiển thị thông tin file
        file_size = os.path.getsize(result)
        print(f"📄 Kích thước file: {file_size:,} bytes")

        return True
    else:
        print("❌ Advanced crawl thất bại!")
        return False


def example_4_custom_processing():
    """
    Example 4: Xử lý tùy chỉnh - chỉ trích xuất nội dung không lưu file
    """
    print("\n📖 Example 4: Custom processing")
    print("=" * 40)

    import requests
    from bs4 import BeautifulSoup

    # Khởi tạo crawler
    crawler = ThuvienphapluatCrawler()

    url = "https://thuvienphapluat.vn/van-ban/Dau-tu/Nghi-dinh-214-2025-ND-CP-huong-dan-Luat-Dau-thau-ve-lua-chon-nha-thau-668157.aspx"

    try:
        # Manual request
        response = requests.get(url, headers=crawler.headers, timeout=crawler.timeout)
        print(f"📡 Response status: {response.status_code}")

        if response.status_code == 200:
            # Parse HTML
            soup = BeautifulSoup(response.content, "html.parser")
            content_div = soup.find("div", class_="content1")

            if content_div:
                # Chỉ trích xuất nội dung, không lưu file
                clean_content = crawler.extract_clean_content(content_div)

                print(f"📝 Đã trích xuất {len(clean_content)} ký tự")
                print(f"📄 Preview nội dung (500 ký tự đầu):")
                print("-" * 40)
                print(
                    clean_content[:500] + "..."
                    if len(clean_content) > 500
                    else clean_content
                )
                print("-" * 40)

                # Có thể xử lý nội dung theo ý muốn tại đây
                # Ví dụ: lưu vào database, gửi qua API, etc.

                return True
            else:
                print("❌ Không tìm thấy nội dung")
                return False
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Lỗi: {str(e)}")
        return False


def main():
    """
    Main function để chạy tất cả examples
    """
    print("🚀 Thuvienphapluat Crawler - Examples")
    print("=" * 50)

    # Tạo thư mục output
    os.makedirs("./examples_output/", exist_ok=True)

    examples = [
        ("Simple Usage", example_1_simple_usage),
        ("Batch Crawling", example_2_batch_crawling),
        ("Advanced Usage", example_3_advanced_usage),
        ("Custom Processing", example_4_custom_processing),
    ]

    results = []

    for name, example_func in examples:
        try:
            success = example_func()
            results.append((name, success))
        except Exception as e:
            print(f"❌ Lỗi trong {name}: {str(e)}")
            results.append((name, False))

    # Tóm tắt
    print("\n" + "=" * 50)
    print("📊 KẾT QUẢ EXAMPLES:")
    print("=" * 50)

    for name, success in results:
        status = "✅ OK" if success else "❌ FAIL"
        print(f"{status} - {name}")

    print("\n🎓 Examples hoàn thành!")
    print("📁 Kiểm tra thư mục './examples_output/' để xem các file đã tạo.")

    # Hiển thị danh sách file đã tạo
    output_dir = "./examples_output/"
    if os.path.exists(output_dir):
        files = [f for f in os.listdir(output_dir) if f.endswith(".md")]
        if files:
            print(f"\n📄 Các file markdown đã tạo ({len(files)} files):")
            for file in files:
                file_path = os.path.join(output_dir, file)
                file_size = os.path.getsize(file_path)
                print(f"  - {file} ({file_size:,} bytes)")


if __name__ == "__main__":
    main()
