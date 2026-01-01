#!/usr/bin/env python3
"""
Test script to process only .doc files
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.batch_reprocess_all import BatchProcessor

# Initialize processor
processor = BatchProcessor(
    raw_dir="data/raw", output_dir="data/processed_with_doc", max_workers=1
)

# Discover all documents
all_docs = processor.discover_documents()

# Filter only .doc files
doc_files = [doc for doc in all_docs if Path(doc.path).suffix.lower() == ".doc"]

print(f"\n📋 Found {len(doc_files)} .doc files:")
for doc in doc_files:
    print(f"   - {Path(doc.path).name}")

# Confirm
print(f"\n⚠️  Process {len(doc_files)} .doc files?")
response = input("Continue? [y/N]: ")

if response.lower() != "y":
    print("❌ Cancelled")
    sys.exit(0)

# Process
stats = processor.process_batch(doc_files)

# Report
print(processor.generate_report())
