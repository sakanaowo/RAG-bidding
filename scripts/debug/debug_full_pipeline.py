#!/usr/bin/env python3
"""
Debug script to check what happens to final_chunks in pipeline
"""

import os
import sys

sys.path.insert(0, "/home/sakana/Code/RAG-bidding")

from src.preprocessing.bidding_preprocessing.pipeline import (
    BiddingPreprocessingPipeline,
)


def debug_full_pipeline():
    """Debug full pipeline to see where final_chunks disappears"""

    file_path = "/home/sakana/Code/RAG-bidding/data/raw/Ho so moi thau/1. Mẫu HSYC/01A. Mẫu HSYC Xây lắp.docx"
    output_dir = "/tmp/debug_pipeline_output"

    # Initialize pipeline
    pipeline = BiddingPreprocessingPipeline()

    print("🔍 Running full pipeline to debug final_chunks...")

    # Run full process method
    results = pipeline.process_file(file_path, output_dir)

    print(f"\n📊 Results status: {results.get('status')}")
    print(f"📊 Final chunks in results: {len(results.get('final_chunks', []))}")

    # Check if chunks were actually written
    chunks_file = os.path.join(output_dir, "chunks.jsonl")
    if os.path.exists(chunks_file):
        with open(chunks_file, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                lines = content.split("\n")
                print(f"📄 chunks.jsonl has {len(lines)} lines")
                print(f"📄 First line preview: {lines[0][:100]}...")
            else:
                print("📄 chunks.jsonl is EMPTY!")
    else:
        print("📄 chunks.jsonl does not exist!")

    # Check stages
    if "stages" in results:
        for stage_name, stage_data in results["stages"].items():
            if isinstance(stage_data, dict) and "success" in stage_data:
                success = stage_data["success"]
                print(f"🔧 Stage {stage_name}: {'✅' if success else '❌'}")

    # Check validation
    if "validation" in results:
        validation = results["validation"]
        print(f"✅ Validation passed: {validation.get('is_valid', False)}")
        if not validation.get("is_valid", False):
            print(f"❌ Validation errors: {validation.get('errors', [])}")


if __name__ == "__main__":
    debug_full_pipeline()
