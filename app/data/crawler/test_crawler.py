#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test file cho Thuvienphapluat Crawler Module

Chạy file này để test các chức năng của module crawler.
"""

import sys
import os

# Thêm thư mục hiện tại vào Python path để import module
sys.path.insert(0, os.path.dirname(__file__))

from thuvienphapluat_crawler import (
    ThuvienphapluatCrawler,
    crawl_and_export_to_markdown,
    batch_crawl_urls,
)


def test_crawler_class():
    """Test ThuvienphapluatCrawler class"""
    print("🧪 Testing ThuvienphapluatCrawler class...")

    # Khởi tạo crawler
    crawler = ThuvienphapluatCrawler(default_output_dir="./test_output/")

    # Test URL
    test_url = "https://thuvienphapluat.vn/van-ban/Dau-tu/Nghi-dinh-214-2025-ND-CP-huong-dan-Luat-Dau-thau-ve-lua-chon-nha-thau-668157.aspx"

    try:
        result = crawler.crawl_single_url(test_url)
        if result:
            print(f"✅ Class test thành công! File: {result}")
            return True
        else:
            print("❌ Class test thất bại!")
            return False
    except Exception as e:
        print(f"❌ Lỗi trong class test: {str(e)}")
        return False


def test_convenience_functions():
    """Test convenience functions"""
    print("\n🧪 Testing convenience functions...")

    test_url = "https://thuvienphapluat.vn/van-ban/Dau-tu/Nghi-dinh-214-2025-ND-CP-huong-dan-Luat-Dau-thau-ve-lua-chon-nha-thau-668157.aspx"

    try:
        # Test single URL function
        result = crawl_and_export_to_markdown(test_url, output_dir="./test_output/")
        if result:
            print(f"✅ Convenience function test thành công! File: {result}")
            return True
        else:
            print("❌ Convenience function test thất bại!")
            return False
    except Exception as e:
        print(f"❌ Lỗi trong convenience function test: {str(e)}")
        return False


def test_batch_crawl():
    """Test batch crawling"""
    print("\n🧪 Testing batch crawl...")

    # Chỉ test với 1 URL để tránh spam
    test_urls = [
        "https://thuvienphapluat.vn/van-ban/Dau-tu/Nghi-dinh-214-2025-ND-CP-huong-dan-Luat-Dau-thau-ve-lua-chon-nha-thau-668157.aspx"
    ]

    try:
        results = batch_crawl_urls(test_urls, output_dir="./test_output/", delay=1)

        successful = sum(1 for r in results if r["success"])
        if successful > 0:
            print(f"✅ Batch crawl test thành công! {successful}/{len(test_urls)} URLs")
            return True
        else:
            print("❌ Batch crawl test thất bại!")
            return False
    except Exception as e:
        print(f"❌ Lỗi trong batch crawl test: {str(e)}")
        return False


def main():
    """Main test runner"""
    print("🚀 Bắt đầu test Thuvienphapluat Crawler Module")
    print("=" * 60)

    # Tạo thư mục test output
    os.makedirs("./test_output/", exist_ok=True)

    tests = [
        ("ThuvienphapluatCrawler Class", test_crawler_class),
        ("Convenience Functions", test_convenience_functions),
        ("Batch Crawl", test_batch_crawl),
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n📋 Test: {test_name}")
        print("-" * 40)

        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Unexpected error in {test_name}: {str(e)}")
            results.append((test_name, False))

    # Tổng kết
    print("\n" + "=" * 60)
    print("📊 KẾT QUẢ TEST:")
    print("=" * 60)

    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
        if success:
            passed += 1

    print("-" * 60)
    print(f"📈 Tổng kết: {passed}/{len(results)} tests passed")

    if passed == len(results):
        print("🎉 Tất cả test đều PASS! Module sẵn sàng sử dụng.")
        return True
    else:
        print("⚠️  Một số test FAIL. Kiểm tra lại module.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
