#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crawler Module Import Script

Script này giúp import dễ dàng crawler module từ bất kỳ đâu trong dự án.
"""

import sys
import os

# Thêm đường dẫn tới crawler module
crawler_path = os.path.join(os.path.dirname(__file__), "data", "crawler")
sys.path.insert(0, crawler_path)

# Import và re-export các functions chính
try:
    from thuvienphapluat_crawler import (
        ThuvienphapluatCrawler,
        crawl_and_export_to_markdown,
        batch_crawl_urls,
    )

    print("✅ Crawler module imported successfully!")
    print("📚 Available functions:")
    print("  - ThuvienphapluatCrawler (class)")
    print("  - crawl_and_export_to_markdown(url, output_dir)")
    print("  - batch_crawl_urls(urls, output_dir, delay)")

except ImportError as e:
    print(f"❌ Failed to import crawler module: {e}")
    print("🔧 Make sure you're running this from the app/ directory")

__all__ = ["ThuvienphapluatCrawler", "crawl_and_export_to_markdown", "batch_crawl_urls"]
