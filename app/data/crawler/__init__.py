#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crawler Package for RAG Bidding System

Module này chứa các crawler để thu thập dữ liệu từ các nguồn khác nhau.
"""

from .thuvienphapluat_crawler import (
    ThuvienphapluatCrawler,
    crawl_and_export_to_markdown,
    batch_crawl_urls,
)

__version__ = "1.0.0"
__author__ = "RAG Bidding Team"

__all__ = ["ThuvienphapluatCrawler", "crawl_and_export_to_markdown", "batch_crawl_urls"]
