#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Thuvienphapluat.vn Web Crawler Module

Module này cung cấp các chức năng để crawl và trích xuất nội dung từ website
thuvienphapluat.vn, sau đó export sang định dạng Markdown.

Author: Generated from Jupyter Notebook
Date: 2025-09-29
"""

import os
import re
import time
import requests
from datetime import datetime
from urllib.parse import urlparse
from bs4 import BeautifulSoup, NavigableString, Comment
from typing import Optional, List, Dict, Any


class ThuvienphapluatCrawler:
    """
    Class chính để crawl dữ liệu từ thuvienphapluat.vn
    """

    def __init__(
        self,
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        timeout: int = 30,
        default_output_dir: str = "../processed/",
    ):
        """
        Khởi tạo crawler

        Args:
            user_agent (str): User agent string để tránh bị block
            timeout (int): Timeout cho requests (seconds)
            default_output_dir (str): Thư mục mặc định để lưu file
        """
        self.headers = {"User-Agent": user_agent}
        self.timeout = timeout
        self.default_output_dir = default_output_dir

    def extract_content_from_div(self, content_div) -> str:
        """
        Trích xuất nội dung từ div và chuyển đổi sang markdown (phiên bản cơ bản)

        Args:
            content_div: BeautifulSoup element chứa nội dung

        Returns:
            str: Nội dung đã chuyển đổi sang markdown
        """
        if not content_div:
            return "Không tìm thấy nội dung"

        markdown_content = []

        # Duyệt qua tất cả các thẻ con
        for element in content_div.find_all(recursive=True):
            # Bỏ qua các comment và navigable string
            if isinstance(element, (Comment, NavigableString)):
                continue

            # Xử lý các thẻ tiêu đề
            if element.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                level = int(element.name[1])
                text = element.get_text(strip=True)
                if text:
                    markdown_content.append("#" * level + " " + text + "\n")

            # Xử lý thẻ paragraph
            elif element.name == "p":
                text = element.get_text(strip=True)
                if text:
                    markdown_content.append(text + "\n\n")

            # Xử lý danh sách có thứ tự
            elif element.name == "ol":
                for i, li in enumerate(element.find_all("li"), 1):
                    text = li.get_text(strip=True)
                    if text:
                        markdown_content.append(f"{i}. {text}\n")
                markdown_content.append("\n")

            # Xử lý danh sách không thứ tự
            elif element.name == "ul":
                for li in element.find_all("li"):
                    text = li.get_text(strip=True)
                    if text:
                        markdown_content.append(f"- {text}\n")
                markdown_content.append("\n")

            # Xử lý các thẻ strong/b
            elif element.name in ["strong", "b"]:
                text = element.get_text(strip=True)
                if text:
                    markdown_content.append(f"**{text}**")

            # Xử lý các thẻ em/i
            elif element.name in ["em", "i"]:
                text = element.get_text(strip=True)
                if text:
                    markdown_content.append(f"*{text}*")

            # Xử lý thẻ div với class đặc biệt
            elif element.name == "div":
                text = element.get_text(strip=True)
                # Chỉ thêm nội dung nếu div không có thẻ con phức tạp
                if text and not element.find_all(
                    ["div", "p", "h1", "h2", "h3", "h4", "h5", "h6"]
                ):
                    markdown_content.append(text + "\n\n")

        return "".join(markdown_content)

    def extract_clean_content(self, content_div) -> str:
        """
        Trích xuất nội dung sạch và chuyển đổi sang markdown (phiên bản cải tiến)

        Args:
            content_div: BeautifulSoup element chứa nội dung

        Returns:
            str: Nội dung đã được làm sạch và chuyển đổi sang markdown
        """
        if not content_div:
            return "Không tìm thấy nội dung"

        markdown_lines = []
        processed_elements = set()

        def clean_text(text):
            """Làm sạch text, loại bỏ khoảng trắng thừa"""
            return " ".join(text.split())

        def process_element(element, level=0):
            """Xử lý từng element một cách đệ quy"""
            if element in processed_elements:
                return

            processed_elements.add(element)

            # Xử lý tiêu đề
            if element.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                level_num = int(element.name[1])
                text = clean_text(element.get_text())
                if text and len(text) > 2:  # Chỉ lấy tiêu đề có ý nghĩa
                    markdown_lines.append("#" * level_num + " " + text + "\n\n")

            # Xử lý paragraph
            elif element.name == "p":
                text = clean_text(element.get_text())
                if text and len(text) > 10:  # Chỉ lấy đoạn văn có ý nghĩa
                    markdown_lines.append(text + "\n\n")

            # Xử lý div có nội dung văn bản
            elif element.name == "div":
                # Nếu div không chứa các thẻ block khác, lấy text
                if not element.find_all(
                    ["div", "p", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol"]
                ):
                    text = clean_text(element.get_text())
                    if text and len(text) > 10:
                        markdown_lines.append(text + "\n\n")
                else:
                    # Nếu có thẻ con, xử lý đệ quy
                    for child in element.children:
                        if hasattr(child, "name") and child.name:
                            process_element(child, level + 1)

            # Xử lý danh sách
            elif element.name == "ul":
                for li in element.find_all("li"):
                    text = clean_text(li.get_text())
                    if text:
                        markdown_lines.append(f"- {text}\n")
                markdown_lines.append("\n")

            elif element.name == "ol":
                for i, li in enumerate(element.find_all("li"), 1):
                    text = clean_text(li.get_text())
                    if text:
                        markdown_lines.append(f"{i}. {text}\n")
                markdown_lines.append("\n")

        # Bắt đầu xử lý từ root element
        process_element(content_div)

        # Làm sạch kết quả
        content = "".join(markdown_lines)
        # Loại bỏ nhiều dòng trống liên tiếp
        content = re.sub(r"\n{3,}", "\n\n", content)

        return content.strip()

    def export_to_markdown(
        self, content: str, url: str, output_dir: Optional[str] = None
    ) -> Optional[str]:
        """
        Export nội dung ra file markdown

        Args:
            content (str): Nội dung để export
            url (str): URL gốc
            output_dir (str, optional): Thư mục output. Mặc định sử dụng default_output_dir

        Returns:
            str: Đường dẫn file đã tạo, hoặc None nếu có lỗi
        """
        if output_dir is None:
            output_dir = self.default_output_dir

        # Tạo thư mục nếu chưa có
        os.makedirs(output_dir, exist_ok=True)

        # Tạo tên file từ URL
        parsed_url = urlparse(url)
        path_parts = parsed_url.path.split("/")

        # Lấy phần cuối của URL làm tên file, loại bỏ extension
        filename_base = path_parts[-1].replace(".aspx", "").replace(".html", "")
        if not filename_base:
            filename_base = "crawled_content"

        # Tạo timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{filename_base}_{timestamp}.md"
        filepath = os.path.join(output_dir, filename)

        # Tạo header cho file markdown
        header = f"""---
title: "Nội dung từ {parsed_url.netloc}"
url: {url}
crawled_at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
source: thuvienphapluat.vn
---

"""

        # Ghi file
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(header)
                f.write(content)

            print(f"✅ Đã export thành công vào file: {filepath}")
            print(f"📄 Kích thước file: {os.path.getsize(filepath):,} bytes")
            return filepath

        except Exception as e:
            print(f"❌ Lỗi khi export file: {str(e)}")
            return None

    def crawl_single_url(
        self, url: str, output_dir: Optional[str] = None
    ) -> Optional[str]:
        """
        Crawl một URL đơn lẻ và export sang markdown

        Args:
            url (str): URL cần crawl
            output_dir (str, optional): Thư mục output

        Returns:
            str: Đường dẫn file đã tạo, hoặc None nếu có lỗi
        """
        print(f"🔄 Bắt đầu crawl: {url}")

        try:
            # 1. Gửi request
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            print(f"📡 Status code: {response.status_code}")

            if response.status_code != 200:
                print(
                    f"❌ Không thể truy cập trang web. Status: {response.status_code}"
                )
                return None

            # 2. Parse HTML
            soup = BeautifulSoup(response.content, "html.parser")
            content_div = soup.find("div", class_="content1")

            if not content_div:
                print("❌ Không tìm thấy div với class 'content1'")
                return None

            print("✅ Tìm thấy nội dung")

            # 3. Trích xuất nội dung
            clean_content = self.extract_clean_content(content_div)
            print(f"📝 Đã trích xuất {len(clean_content)} ký tự")

            # 4. Export ra markdown
            output_file = self.export_to_markdown(clean_content, url, output_dir)

            return output_file

        except requests.RequestException as e:
            print(f"❌ Lỗi khi request: {str(e)}")
            return None
        except Exception as e:
            print(f"❌ Lỗi không xác định: {str(e)}")
            return None

    def crawl_multiple_urls(
        self, urls: List[str], output_dir: Optional[str] = None, delay: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Crawl nhiều URL với delay giữa các request

        Args:
            urls (List[str]): Danh sách các URL cần crawl
            output_dir (str, optional): Thư mục output
            delay (int): Delay giữa các request (seconds)

        Returns:
            List[Dict]: Danh sách kết quả crawling
        """
        results = []
        total_urls = len(urls)

        print(f"🚀 Bắt đầu crawl {total_urls} URL...")
        print(f"⏱️  Delay giữa các request: {delay} giây")
        print("=" * 50)

        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{total_urls}] Processing: {url}")

            result = self.crawl_single_url(url, output_dir)
            results.append(
                {
                    "url": url,
                    "success": result is not None,
                    "output_file": result,
                    "index": i,
                }
            )

            # Delay giữa các request để tránh bị block
            if i < total_urls:
                print(f"⏳ Chờ {delay} giây...")
                time.sleep(delay)

        # Tóm tắt kết quả
        print("\n" + "=" * 50)
        print("📊 TỔNG KẾT:")
        successful = sum(1 for r in results if r["success"])
        failed = total_urls - successful

        print(f"✅ Thành công: {successful}/{total_urls}")
        print(f"❌ Thất bại: {failed}/{total_urls}")

        if successful > 0:
            print(f"\n📁 Các file đã tạo:")
            for result in results:
                if result["success"]:
                    print(f"  - {result['output_file']}")

        return results


# Convenience functions để sử dụng dễ dàng hơn
def crawl_and_export_to_markdown(
    url: str, output_dir: str = "../processed/"
) -> Optional[str]:
    """
    Function tiện ích để crawl một URL và export sang markdown

    Args:
        url (str): URL cần crawl
        output_dir (str): Thư mục output

    Returns:
        str: Đường dẫn file đã tạo, hoặc None nếu có lỗi
    """
    crawler = ThuvienphapluatCrawler(default_output_dir=output_dir)
    return crawler.crawl_single_url(url, output_dir)


def batch_crawl_urls(
    urls: List[str], output_dir: str = "../processed/", delay: int = 2
) -> List[Dict[str, Any]]:
    """
    Function tiện ích để crawl nhiều URL

    Args:
        urls (List[str]): Danh sách URL
        output_dir (str): Thư mục output
        delay (int): Delay giữa requests

    Returns:
        List[Dict]: Kết quả crawling
    """
    crawler = ThuvienphapluatCrawler(default_output_dir=output_dir)
    return crawler.crawl_multiple_urls(urls, output_dir, delay)


# Example usage và testing
if __name__ == "__main__":
    # Test với một URL mẫu
    test_url = "https://thuvienphapluat.vn/van-ban/Dau-tu/Nghi-dinh-214-2025-ND-CP-huong-dan-Luat-Dau-thau-ve-lua-chon-nha-thau-668157.aspx"

    print("🧪 Testing Thuvienphapluat Crawler...")
    print("=" * 50)

    # Test crawl single URL
    result = crawl_and_export_to_markdown(test_url, output_dir="./crawled_data/")

    if result:
        print(f"\n🎉 Test thành công! File đã được lưu tại: {result}")
    else:
        print("\n❌ Test thất bại")

    # Example usage với class
    print("\n" + "=" * 50)
    print("📝 Example usage với ThuvienphapluatCrawler class:")
    print(
        """
# Khởi tạo crawler
crawler = ThuvienphapluatCrawler(default_output_dir='./my_data/')

# Crawl một URL
result = crawler.crawl_single_url('https://thuvienphapluat.vn/van-ban/...')

# Crawl nhiều URL
urls = ['url1', 'url2', 'url3']
results = crawler.crawl_multiple_urls(urls, delay=3)
"""
    )
