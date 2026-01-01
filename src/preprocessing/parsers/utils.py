"""
Utility functions cho markdown preprocessing
"""

import tiktoken
import glob
import os
import json
from typing import List, Dict, Tuple
from dataclasses import dataclass
import numpy as np
from datetime import datetime


@dataclass
class TokenStats:
    """Thống kê về tokens"""

    text: str
    char_count: int
    token_count: int
    ratio: float
    model: str
    is_within_limit: bool
    embedding_dim: int = None


class TokenChecker:
    """Kiểm tra token size cho embedding models"""

    # Token limits cho các models phổ biến
    TOKEN_LIMITS = {
        # OpenAI
        "text-embedding-3-small": 8191,
        "text-embedding-3-large": 8191,
        "text-embedding-ada-002": 8191,
        # Cohere
        "embed-multilingual-v3.0": 512,
        "embed-english-v3.0": 512,
        # Other
        "sentence-transformers": 512,  # Mặc định BERT-based
    }

    # Embedding dimensions
    EMBEDDING_DIMS = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
        "embed-multilingual-v3.0": 1024,
        "embed-english-v3.0": 1024,
    }

    def __init__(self, model: str = "text-embedding-3-small"):
        """
        Args:
            model: Tên model embedding
        """
        self.model = model
        self.token_limit = self.TOKEN_LIMITS.get(model, 8191)
        self.embedding_dim = self.EMBEDDING_DIMS.get(model)

        # Load tokenizer
        if "text-embedding-3" in model or "ada-002" in model:
            self.encoding = tiktoken.get_encoding("cl100k_base")
        else:
            self.encoding = tiktoken.get_encoding("p50k_base")

    def count_tokens(self, text: str) -> int:
        """Đếm số tokens"""
        tokens = self.encoding.encode(text)
        return len(tokens)

    def check_text(self, text: str) -> TokenStats:
        """Kiểm tra một đoạn text"""
        char_count = len(text)
        token_count = self.count_tokens(text)
        ratio = char_count / token_count if token_count > 0 else 0
        is_within_limit = token_count <= self.token_limit

        return TokenStats(
            text=text[:100] + "..." if len(text) > 100 else text,
            char_count=char_count,
            token_count=token_count,
            ratio=ratio,
            model=self.model,
            is_within_limit=is_within_limit,
            embedding_dim=self.embedding_dim,
        )

    def check_chunks(self, chunks: List[str]) -> List[TokenStats]:
        """Kiểm tra nhiều chunks"""
        return [self.check_text(chunk) for chunk in chunks]


def process_md_documents_pipeline(
    input_dir: str, output_dir: str
) -> Tuple[List[dict], dict]:
    """Complete pipeline để xử lý tất cả .md files"""
    try:
        from .md_processor import MarkdownDocumentProcessor
    except ImportError:
        from md_processor import MarkdownDocumentProcessor

    processor = MarkdownDocumentProcessor()

    # Find all .md files
    md_files = glob.glob(os.path.join(input_dir, "*.md"))
    print(f"🔍 Found {len(md_files)} .md files to process")

    all_chunks = []
    processing_stats = {
        "processed_files": 0,
        "failed_files": 0,
        "total_chunks": 0,
        "total_tokens": 0,
    }

    for md_file in md_files:
        try:
            print(f"\n📄 Processing: {os.path.basename(md_file)}")

            # Step 1-2: Parse và validate
            document = processor.parse_md_file(md_file)

            if not processor.validate_document(document):
                print(f"   ❌ Validation failed, skipping...")
                processing_stats["failed_files"] += 1
                continue

            # Step 3: Chunk optimally
            chunks = processor.process_to_chunks(document)
            print(f"   📊 Created {len(chunks)} chunks")

            # Step 4: Validate chunks
            validated_chunks = processor.validate_chunks(chunks)
            print(f"   ✅ Validated {len(validated_chunks)} chunks")

            all_chunks.extend(validated_chunks)
            processing_stats["processed_files"] += 1
            processing_stats["total_chunks"] += len(validated_chunks)

        except Exception as e:
            print(f"   ❌ Error processing {md_file}: {str(e)}")
            processing_stats["failed_files"] += 1

    # Export all chunks
    output_file = os.path.join(output_dir, "processed_chunks.jsonl")
    total_exported = export_chunks_to_jsonl(all_chunks, output_file)

    # Generate report
    report = generate_processing_report(all_chunks)

    print(f"\n🎉 PROCESSING COMPLETE!")
    print(f"   📁 Files processed: {processing_stats['processed_files']}")
    print(f"   ❌ Files failed: {processing_stats['failed_files']}")
    print(f"   📦 Total chunks: {total_exported}")
    print(f"   💾 Output file: {output_file}")
    print(f"   📊 Avg quality score: {report['summary']['avg_quality_score']:.2f}")

    return all_chunks, report


def export_chunks_to_jsonl(chunks: List[dict], output_path: str) -> int:
    """Export chunks cho vector database"""

    # Format for vector database
    vectordb_format = []
    for chunk in chunks:
        record = {
            "id": chunk["id"],
            "text": chunk["text"],
            "metadata": chunk["metadata"],
            "embedding_ready": True,
            "processing_stats": {
                "char_count": chunk["metadata"]["char_count"],
                "token_count": chunk["metadata"]["token_count"],
                "quality_score": sum(chunk["metadata"]["quality_flags"].values())
                / len(chunk["metadata"]["quality_flags"]),
            },
        }
        vectordb_format.append(record)

    # Export to JSONL
    with open(output_path, "w", encoding="utf-8") as f:
        for record in vectordb_format:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

    return len(vectordb_format)


def generate_processing_report(chunks: List[dict]) -> dict:
    """Generate comprehensive processing report"""

    total_chunks = len(chunks)
    total_chars = sum(c["metadata"]["char_count"] for c in chunks)
    total_tokens = sum(c["metadata"]["token_count"] for c in chunks)

    quality_scores = [
        sum(c["metadata"]["quality_flags"].values())
        / len(c["metadata"]["quality_flags"])
        for c in chunks
    ]

    level_distribution = {}
    for chunk in chunks:
        level = chunk["metadata"]["chunk_level"]
        level_distribution[level] = level_distribution.get(level, 0) + 1

    return {
        "summary": {
            "total_chunks": total_chunks,
            "total_characters": total_chars,
            "total_tokens": total_tokens,
            "avg_chunk_size": total_chars / total_chunks if total_chunks else 0,
            "avg_quality_score": (
                sum(quality_scores) / len(quality_scores) if quality_scores else 0
            ),
        },
        "distribution": {
            "level_distribution": level_distribution,
            "size_ranges": _calculate_size_ranges(chunks),
            "token_ranges": _calculate_token_ranges(chunks),
        },
        "quality": {
            "high_quality_chunks": sum(1 for score in quality_scores if score >= 0.8),
            "medium_quality_chunks": sum(
                1 for score in quality_scores if 0.5 <= score < 0.8
            ),
            "low_quality_chunks": sum(1 for score in quality_scores if score < 0.5),
        },
    }


def _calculate_size_ranges(chunks: List[dict]) -> dict:
    """Calculate size distribution ranges"""
    sizes = [c["metadata"]["char_count"] for c in chunks]
    if not sizes:
        return {}

    return {
        "min": min(sizes),
        "max": max(sizes),
        "avg": sum(sizes) / len(sizes),
        "small_chunks": sum(1 for s in sizes if s < 500),
        "medium_chunks": sum(1 for s in sizes if 500 <= s <= 1500),
        "large_chunks": sum(1 for s in sizes if s > 1500),
    }


def _calculate_token_ranges(chunks: List[dict]) -> dict:
    """Calculate token distribution ranges"""
    tokens = [c["metadata"]["token_count"] for c in chunks]
    if not tokens:
        return {}

    return {
        "min": min(tokens),
        "max": max(tokens),
        "avg": sum(tokens) / len(tokens),
        "over_limit": sum(1 for t in tokens if t > 8000),
    }
