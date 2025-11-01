#!/usr/bin/env python3
"""
Quick summary of batch reprocessing results
"""
import json
from pathlib import Path
from collections import Counter

# Paths
chunks_dir = Path("data/reprocessed/chunks")
metadata_dir = Path("data/reprocessed/metadata")

# Count files
chunk_files = list(chunks_dir.glob("*.jsonl"))
metadata_files = list(metadata_dir.glob("*.json"))

print("=" * 80)
print("📊 BATCH REPROCESSING SUMMARY")
print("=" * 80)
print(f"Chunk files:    {len(chunk_files)}")
print(f"Metadata files: {len(metadata_files)}")
print()

# Analyze metadata
doc_types = Counter()
categories = Counter()
total_chunks = 0

for meta_file in metadata_files:
    with open(meta_file) as f:
        meta = json.load(f)
        doc_types[meta["document_type"]] += 1
        categories[meta["category"]] += 1
        total_chunks += meta["chunk_count"]

print("📋 By Document Type:")
for doc_type, count in doc_types.most_common():
    print(f"   {doc_type:15s}: {count:3d} files")

print()
print(f"💎 Total Chunks: {total_chunks:,}")
print(f"📈 Avg Chunks/File: {total_chunks / len(metadata_files):.1f}")
print("=" * 80)
