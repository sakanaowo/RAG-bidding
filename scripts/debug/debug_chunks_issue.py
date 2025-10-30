#!/usr/bin/env python3
"""
Debug script to find why chunks.jsonl is empty
"""

import sys
import os

sys.path.insert(0, "/home/sakana/Code/RAG-bidding")

from src.preprocessing.bidding_preprocessing.pipeline import (
    BiddingPreprocessingPipeline,
)


def debug_chunks_issue():
    """Debug empty chunks issue"""

    file_path = "/home/sakana/Code/RAG-bidding/data/raw/Ho so moi thau/1. Mẫu HSYC/01A. Mẫu HSYC Xây lắp.docx"

    # Initialize pipeline
    pipeline = BiddingPreprocessingPipeline()

    # Process the file step by step
    print("🔍 Debugging chunks processing...")

    # Stage 1: Extract
    print("\n1. Extracting...")
    extraction_result = pipeline.extractor.extract(file_path)
    content = extraction_result.text
    metadata = extraction_result.metadata

    print(f"   - Content length: {len(content)}")

    # Stage 2: Clean
    print("\n2. Cleaning...")
    cleaned_content = pipeline.cleaner.clean(content)
    print(f"   - Cleaned length: {len(cleaned_content)}")

    # Stage 3: Parse
    print("\n3. Parsing...")
    parsing_result = pipeline.parser.parse(cleaned_content, metadata)
    print(f"   - Sections: {len(parsing_result.get('sections', []))}")

    # Stage 4: Chunk
    print("\n4. Chunking...")
    sections = parsing_result.get("sections", [])
    print(f"   - Sections count: {len(sections)}")

    # Just chunk the cleaned content directly
    print("   - Using cleaned content directly for chunking")
    chunks = pipeline.chunker.chunk_text(cleaned_content)

    print(f"   - Chunks generated: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        print(f"     Chunk {i}: {len(chunk.get('content', ''))} chars")
        print(f"     Keys: {list(chunk.keys())}")

    # Stage 5: Map directly
    print("\n5. Mapping...")
    document_metadata = {
        "source_file": os.path.basename(file_path),
        "file_path": file_path,
        "bidding_type": metadata.get("bidding_type"),
        "extraction_metadata": metadata,
        "parsing_metadata": parsing_result["metadata"],
    }

    print("   - Calling mapper.map_chunks...")
    final_chunks = pipeline.mapper.map_chunks(chunks, document_metadata)
    print(f"   - Final chunks: {len(final_chunks)}")

    if final_chunks:
        for i, chunk in enumerate(final_chunks):
            content_len = 0
            if "content" in chunk:
                content_len = len(str(chunk["content"]))
            elif "text" in chunk:
                content_len = len(str(chunk["text"]))
            print(f"     Final chunk {i}: {content_len} chars")
            print(f"     Keys: {list(chunk.keys())}")
    else:
        print("   - ❌ FINAL CHUNKS IS EMPTY!")
        print("   - Checking mapper function...")

        # Manual check
        if chunks:
            print(f"   - Original chunks exist: {len(chunks)}")
            print(f"   - Document metadata: {document_metadata}")

            # Test mapper directly
            try:
                test_result = pipeline.mapper.map_chunks(chunks, document_metadata)
                print(f"   - Direct mapper test: {len(test_result)} chunks")
            except Exception as e:
                print(f"   - Mapper error: {e}")
                import traceback

                traceback.print_exc()


if __name__ == "__main__":
    debug_chunks_issue()
