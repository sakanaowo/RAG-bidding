#!/usr/bin/env python3
"""
Calculate embedding costs for processed chunks.
Estimates token count using tiktoken and calculates API costs.
"""
import json
import sys
from pathlib import Path
from typing import Dict, List
import tiktoken

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def count_tokens(text: str, model: str = "cl100k_base") -> int:
    """Count tokens in text using tiktoken."""
    try:
        encoding = tiktoken.get_encoding(model)
        return len(encoding.encode(text))
    except Exception as e:
        print(f"Error encoding text: {e}")
        return 0


def load_chunk_file(file_path: Path) -> List[Dict]:
    """Load chunks from JSONL file."""
    chunks = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    chunks.append(json.loads(line))
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
    return chunks


def calculate_cost(
    total_tokens: int, model: str = "text-embedding-3-large"
) -> Dict[str, float]:
    """Calculate embedding cost for different models."""
    # Pricing per 1M tokens (as of 2024)
    pricing = {
        "text-embedding-3-large": 0.13,  # $0.13 per 1M tokens
        "text-embedding-3-small": 0.02,  # $0.02 per 1M tokens
        "text-embedding-ada-002": 0.10,  # $0.10 per 1M tokens
    }

    cost_per_token = pricing.get(model, 0.13) / 1_000_000
    return {
        "total_tokens": total_tokens,
        "cost_usd": total_tokens * cost_per_token,
        "cost_per_1m_tokens": pricing.get(model, 0.13),
        "model": model,
    }


def main():
    """Calculate costs for all processed chunks."""
    chunks_dir = Path(__file__).parent.parent / "data" / "processed" / "chunks"

    if not chunks_dir.exists():
        print(f"❌ Chunks directory not found: {chunks_dir}")
        sys.exit(1)

    print("=" * 80)
    print("EMBEDDING COST CALCULATION")
    print("=" * 80)
    print(f"📁 Directory: {chunks_dir}")
    print()

    # Stats by document type
    stats_by_type = {}
    total_chunks = 0
    total_chars = 0
    total_tokens = 0

    # Process all JSONL files
    jsonl_files = sorted(chunks_dir.glob("*.jsonl"))
    print(f"📄 Found {len(jsonl_files)} JSONL files\n")

    for file_path in jsonl_files:
        chunks = load_chunk_file(file_path)

        for chunk in chunks:
            doc_type = chunk.get("document_type", "unknown")
            content = chunk.get("content", "")
            char_count = len(content)
            token_count = count_tokens(content)

            # Update stats
            if doc_type not in stats_by_type:
                stats_by_type[doc_type] = {"chunks": 0, "chars": 0, "tokens": 0}

            stats_by_type[doc_type]["chunks"] += 1
            stats_by_type[doc_type]["chars"] += char_count
            stats_by_type[doc_type]["tokens"] += token_count

            total_chunks += 1
            total_chars += char_count
            total_tokens += token_count

    # Print stats by document type
    print("📊 STATISTICS BY DOCUMENT TYPE")
    print("-" * 80)
    print(f"{'Type':<15} {'Chunks':<10} {'Characters':<15} {'Tokens':<15} {'%':<10}")
    print("-" * 80)

    for doc_type in sorted(stats_by_type.keys()):
        stats = stats_by_type[doc_type]
        percentage = (stats["tokens"] / total_tokens * 100) if total_tokens > 0 else 0
        print(
            f"{doc_type:<15} {stats['chunks']:<10} {stats['chars']:<15,} "
            f"{stats['tokens']:<15,} {percentage:>6.1f}%"
        )

    print("-" * 80)
    print(
        f"{'TOTAL':<15} {total_chunks:<10} {total_chars:<15,} {total_tokens:<15,} {'100.0%':>10}"
    )
    print()

    # Calculate costs for different models
    print("💰 COST ESTIMATION")
    print("-" * 80)

    models = [
        "text-embedding-3-large",
        "text-embedding-3-small",
        "text-embedding-ada-002",
    ]

    for model in models:
        cost_info = calculate_cost(total_tokens, model)
        print(f"\n{model}:")
        print(f"  - Cost per 1M tokens: ${cost_info['cost_per_1m_tokens']:.2f}")
        print(f"  - Total tokens: {cost_info['total_tokens']:,}")
        print(f"  - Estimated cost: ${cost_info['cost_usd']:.2f} USD")

    print()
    print("=" * 80)

    # Summary
    avg_chars = total_chars / total_chunks if total_chunks > 0 else 0
    avg_tokens = total_tokens / total_chunks if total_chunks > 0 else 0

    print("📈 SUMMARY")
    print(f"  Total chunks: {total_chunks:,}")
    print(f"  Total characters: {total_chars:,}")
    print(f"  Total tokens: {total_tokens:,}")
    print(f"  Average chars/chunk: {avg_chars:.0f}")
    print(f"  Average tokens/chunk: {avg_tokens:.0f}")
    print("=" * 80)


if __name__ == "__main__":
    main()
