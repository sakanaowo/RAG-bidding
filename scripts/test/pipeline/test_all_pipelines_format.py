#!/usr/bin/env python3
"""
Comprehensive test script to check all pipelines output format consistency
"""

import sys
import os
import json
from pathlib import Path

sys.path.insert(0, "/home/sakana/Code/RAG-bidding")


def test_pipeline_output_format():
    """Test all pipelines to ensure consistent JSONL output format"""

    print("🔍 TESTING ALL PIPELINE OUTPUT FORMATS")
    print("=" * 60)

    # Expected standard format based on processed_chunks.jsonl
    expected_keys = {"id", "text", "metadata", "embedding_ready", "processing_stats"}

    test_results = {}

    # 1. Test Bidding Pipeline (HSYC)
    print("\n1️⃣ TESTING BIDDING PIPELINE (HSYC)")
    print("-" * 40)

    try:
        from src.preprocessing.bidding_preprocessing.pipeline import (
            BiddingPreprocessingPipeline,
        )

        pipeline = BiddingPreprocessingPipeline(
            validate_integrity=False
        )  # Disable validator to focus on format
        file_path = "/home/sakana/Code/RAG-bidding/data/raw/Ho so moi thau/1. Mẫu HSYC/01D. Mẫu HSYC Tư vấn.docx"
        output_dir = "/tmp/test_bidding_format"

        results = pipeline.process_file(file_path, output_dir)

        if results["status"] == "completed":
            chunks_file = os.path.join(output_dir, "chunks.jsonl")
            if os.path.exists(chunks_file):
                with open(chunks_file, "r", encoding="utf-8") as f:
                    chunk = json.loads(f.readline())

                chunk_keys = set(chunk.keys())
                test_results["bidding"] = {
                    "status": "success",
                    "keys": list(chunk_keys),
                    "has_required_keys": expected_keys.issubset(chunk_keys),
                    "sample_id": chunk.get("id", "N/A"),
                    "text_length": len(chunk.get("text", "")),
                    "embedding_ready": chunk.get("embedding_ready", False),
                }
                print(f"✅ Success: {chunk_keys}")
            else:
                test_results["bidding"] = {
                    "status": "failed",
                    "error": "chunks.jsonl not found",
                }
                print("❌ Failed: chunks.jsonl not found")
        else:
            test_results["bidding"] = {
                "status": "failed",
                "error": results.get("error", "Unknown"),
            }
            print(f"❌ Pipeline failed: {results.get('error', 'Unknown')}")

    except Exception as e:
        test_results["bidding"] = {"status": "failed", "error": str(e)}
        print(f"❌ Exception: {e}")

    # 2. Test Circular Pipeline (Thông tư)
    print("\n2️⃣ TESTING CIRCULAR PIPELINE (THÔNG TƯ)")
    print("-" * 40)

    try:
        from src.preprocessing.circular_preprocessing.pipeline import (
            CircularPreprocessingPipeline,
        )

        pipeline = CircularPreprocessingPipeline(validate_integrity=False)
        file_path = Path(
            "/home/sakana/Code/RAG-bidding/data/raw/Thong tu/0. Lời văn thông tư.docx"
        )
        output_dir = Path("/tmp/test_circular_format")
        output_dir.mkdir(exist_ok=True)

        results = pipeline.process_single_file(file_path, output_dir)

        if results["status"] == "completed":
            chunks_file = os.path.join(output_dir, "chunks.jsonl")
            if os.path.exists(chunks_file):
                with open(chunks_file, "r", encoding="utf-8") as f:
                    chunk = json.loads(f.readline())

                chunk_keys = set(chunk.keys())
                test_results["circular"] = {
                    "status": "success",
                    "keys": list(chunk_keys),
                    "has_required_keys": expected_keys.issubset(chunk_keys),
                    "sample_id": chunk.get("id", "N/A"),
                    "text_length": len(chunk.get("text", "")),
                    "embedding_ready": chunk.get("embedding_ready", False),
                }
                print(f"✅ Success: {chunk_keys}")
            else:
                test_results["circular"] = {
                    "status": "failed",
                    "error": "chunks.jsonl not found",
                }
                print("❌ Failed: chunks.jsonl not found")
        else:
            test_results["circular"] = {
                "status": "failed",
                "error": results.get("error", "Unknown"),
            }
            print(f"❌ Pipeline failed: {results.get('error', 'Unknown')}")

    except Exception as e:
        test_results["circular"] = {"status": "failed", "error": str(e)}
        print(f"❌ Exception: {e}")

    # 3. Test Decree Pipeline (Nghị định)
    print("\n3️⃣ TESTING DECREE PIPELINE (NGHỊ ĐỊNH)")
    print("-" * 40)

    try:
        from src.preprocessing.decree_preprocessing.pipeline import (
            DecreePreprocessingPipeline,
        )

        # Find a decree file
        decree_files = []
        decree_dir = "/home/sakana/Code/RAG-bidding/data/raw/Nghi dinh"
        if os.path.exists(decree_dir):
            for file in os.listdir(decree_dir):
                if file.endswith((".doc", ".docx")):
                    decree_files.append(os.path.join(decree_dir, file))

        if decree_files:
            pipeline = DecreePreprocessingPipeline(validate_integrity=False)
            file_path = Path(decree_files[0])
            output_dir = "/tmp/test_decree_format"
            os.makedirs(output_dir, exist_ok=True)

            # DecreePreprocessingPipeline returns chunks directly, not a result dict
            chunks = pipeline.process_single_file(file_path)

            if chunks:
                # DecreePreprocessingPipeline returns chunks directly
                chunk = chunks[0] if chunks else {}

                chunk_keys = set(chunk.keys())
                test_results["decree"] = {
                    "status": "success",
                    "keys": list(chunk_keys),
                    "has_required_keys": expected_keys.issubset(chunk_keys),
                    "sample_id": chunk.get("id", "N/A"),
                    "text_length": len(chunk.get("text", chunk.get("content", ""))),
                    "embedding_ready": chunk.get("embedding_ready", False),
                }
                print(f"✅ Success: {chunk_keys}")
            else:
                test_results["decree"] = {
                    "status": "failed",
                    "error": "No chunks returned",
                }
                print("❌ Pipeline failed: No chunks returned")
        else:
            test_results["decree"] = {
                "status": "skipped",
                "error": "No decree files found",
            }
            print("⏭️ Skipped: No decree files found")

    except Exception as e:
        test_results["decree"] = {"status": "failed", "error": str(e)}
        print(f"❌ Exception: {e}")

    # 4. Test Law Pipeline (Luật)
    print("\n4️⃣ TESTING LAW PIPELINE (LUẬT)")
    print("-" * 40)

    try:
        from src.preprocessing.law_preprocessing.pipeline import (
            LawPreprocessingPipeline,
        )

        # Find a law file
        law_files = []
        law_dir = "/home/sakana/Code/RAG-bidding/data/raw/Luat chinh"
        if os.path.exists(law_dir):
            for file in os.listdir(law_dir):
                if file.endswith((".doc", ".docx")):
                    law_files.append(os.path.join(law_dir, file))

        if law_files:
            pipeline = LawPreprocessingPipeline(validate_integrity=False)
            file_path = Path(law_files[0])
            output_dir = Path("/tmp/test_law_format")
            output_dir.mkdir(exist_ok=True)

            # LawPreprocessingPipeline returns chunks directly
            chunks = pipeline.process_single_file(file_path, output_dir)

            if chunks:
                chunk = chunks[0] if chunks else {}

                chunk_keys = set(chunk.keys())
                test_results["law"] = {
                    "status": "success",
                    "keys": list(chunk_keys),
                    "has_required_keys": expected_keys.issubset(chunk_keys),
                    "sample_id": chunk.get("id", "N/A"),
                    "text_length": len(
                        chunk.get("text", chunk.get("chunk_content", ""))
                    ),
                    "embedding_ready": chunk.get("embedding_ready", False),
                }
                print(f"✅ Success: {chunk_keys}")
            else:
                test_results["law"] = {
                    "status": "failed",
                    "error": "No chunks returned",
                }
                print("❌ Pipeline failed: No chunks returned")
        else:
            test_results["law"] = {"status": "skipped", "error": "No law files found"}
            print("⏭️ Skipped: No law files found")

    except Exception as e:
        test_results["law"] = {"status": "failed", "error": str(e)}
        print(f"❌ Exception: {e}")

    # Summary Report
    print("\n" + "=" * 60)
    print("📊 FINAL SUMMARY REPORT")
    print("=" * 60)

    all_consistent = True

    for pipeline_name, result in test_results.items():
        status_emoji = (
            "✅"
            if result["status"] == "success"
            else "❌" if result["status"] == "failed" else "⏭️"
        )
        print(f"\n{status_emoji} {pipeline_name.upper()} PIPELINE:")

        if result["status"] == "success":
            has_required = result["has_required_keys"]
            consistency_emoji = "✅" if has_required else "❌"
            print(f"  {consistency_emoji} Format consistency: {has_required}")
            print(f"  📋 Keys: {result['keys']}")
            print(f"  🆔 Sample ID: {result['sample_id']}")
            print(f"  📝 Text length: {result['text_length']}")
            print(f"  🚀 Embedding ready: {result['embedding_ready']}")

            if not has_required:
                missing_keys = expected_keys - set(result["keys"])
                extra_keys = set(result["keys"]) - expected_keys
                if missing_keys:
                    print(f"  ❌ Missing keys: {missing_keys}")
                if extra_keys:
                    print(f"  ℹ️  Extra keys: {extra_keys}")
                all_consistent = False
        else:
            print(f"  ❌ Status: {result['status']}")
            print(f"  ❌ Error: {result.get('error', 'Unknown')}")
            if result["status"] == "failed":
                all_consistent = False

    print(
        f"\n{'🎉 ALL PIPELINES CONSISTENT!' if all_consistent else '⚠️  INCONSISTENCIES FOUND!'}"
    )
    print(f"Expected format: {sorted(expected_keys)}")

    return test_results


if __name__ == "__main__":
    test_pipeline_output_format()
