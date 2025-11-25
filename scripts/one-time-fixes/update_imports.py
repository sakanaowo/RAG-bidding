#!/usr/bin/env python3
"""
Script to update imports after restructuring the project.
Run from project root: python scripts/update_imports.py
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple

# Import mapping: old_path -> new_path
IMPORT_MAPPINGS = {
    # Config
    "app.core.enhanced_config": "config.settings",
    "app.core.config": "config.models",
    "app.core.logging": "config.logging_config",
    "app.core.vectorstore": "src.embedding.store.pgvector_store",
    # Data processing - Crawlers
    "app.data.crawler.thuvienphapluat_crawler": "src.ingestion.crawlers.thuvienphapluat_crawler",
    # Data processing - OCR
    "app.data.ocr-process": "src.ingestion.extractors",
    # Data processing - Preprocessing
    "app.data.core.md-preprocess": "src.preprocessing.parsers",
    # Chunking
    "app.data.core.optimal_chunker": "src.chunking.optimal_chunker",
    "app.data.core.chunk-strategy": "src.chunking.strategies.chunk_strategy",
    # Query Enhancement
    "app.rag.query_enhancement": "src.retrieval.query_processing.query_enhancer",
    "app.rag.QuestionComplexAnalyzer": "src.retrieval.query_processing.complexity_analyzer",
    # Retrievers
    "app.rag.retriever": "src.retrieval.retrievers.base_retriever",
    "app.rag.adaptive_retriever": "src.retrieval.retrievers.adaptive_retriever",
    # Chains
    "app.rag.chain": "src.generation.chains.qa_chain",
    "app.rag.enhanced_chain": "src.generation.chains.enhanced_chain",
    # Prompts
    "app.rag.prompts": "src.generation.prompts.qa_prompts",
    # Evaluation
    "app.rag.eval": "src.evaluation.metrics.retrieval_metrics",
    # API
    "app.api.main": "api.main",
}


def find_python_files(root_dir: str, exclude_dirs: List[str] = None) -> List[Path]:
    """Find all Python files in the project."""
    if exclude_dirs is None:
        exclude_dirs = [".venv", "__pycache__", ".git", "venv", "env"]

    python_files = []
    for path in Path(root_dir).rglob("*.py"):
        # Skip excluded directories
        if any(excluded in str(path) for excluded in exclude_dirs):
            continue
        python_files.append(path)

    return python_files


def update_import_line(line: str, mappings: Dict[str, str]) -> Tuple[str, bool]:
    """Update a single import line if it matches any mapping."""
    updated = False
    original_line = line

    for old_import, new_import in mappings.items():
        # Pattern 1: from X import Y
        pattern1 = rf"from\s+{re.escape(old_import)}\s+import"
        if re.search(pattern1, line):
            line = re.sub(pattern1, f"from {new_import} import", line)
            updated = True

        # Pattern 2: import X
        pattern2 = rf"import\s+{re.escape(old_import)}(\s|$|,)"
        if re.search(pattern2, line):
            line = re.sub(
                rf"import\s+{re.escape(old_import)}", f"import {new_import}", line
            )
            updated = True

        # Pattern 3: from X.Y import Z (partial match)
        if old_import in line and "import" in line:
            # More aggressive replacement for nested imports
            line = line.replace(old_import, new_import)
            updated = True

    return line, updated


def update_file_imports(
    filepath: Path, mappings: Dict[str, str], dry_run: bool = False
) -> int:
    """Update imports in a single file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"❌ Error reading {filepath}: {e}")
        return 0

    updated_lines = []
    changes_count = 0

    for line in lines:
        updated_line, was_updated = update_import_line(line, mappings)
        updated_lines.append(updated_line)

        if was_updated:
            changes_count += 1
            if dry_run:
                print(f"  📝 {filepath.name}:")
                print(f"    - {line.strip()}")
                print(f"    + {updated_line.strip()}")

    if changes_count > 0 and not dry_run:
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.writelines(updated_lines)
            print(
                f"✅ Updated {filepath.relative_to(Path.cwd())} ({changes_count} changes)"
            )
        except Exception as e:
            print(f"❌ Error writing {filepath}: {e}")

    return changes_count


def main():
    """Main function to update all imports."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Update imports after project restructure"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show changes without applying them"
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Root directory to search (default: current directory)",
    )
    args = parser.parse_args()

    root_dir = Path(args.root).resolve()

    print("🔍 Searching for Python files...")
    python_files = find_python_files(root_dir)
    print(f"   Found {len(python_files)} Python files")

    if args.dry_run:
        print("\n🔍 DRY RUN - No files will be modified\n")
    else:
        print("\n📝 Updating imports...\n")

    total_changes = 0
    files_changed = 0

    for filepath in python_files:
        changes = update_file_imports(filepath, IMPORT_MAPPINGS, args.dry_run)
        if changes > 0:
            total_changes += changes
            files_changed += 1

    print(
        f"\n{'🔍 Would update' if args.dry_run else '✅ Updated'} {files_changed} files with {total_changes} total changes"
    )

    if args.dry_run:
        print("\n💡 Run without --dry-run to apply changes")


if __name__ == "__main__":
    main()
