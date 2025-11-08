#!/usr/bin/env python3
"""Update metadata files: reprocessed → processed paths."""
import json
from pathlib import Path


def update_metadata_file(file_path: Path) -> bool:
    """Update paths in a single metadata file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Check if needs update
        needs_update = False

        # Update output_file path
        if "output_file" in data and "reprocessed" in data["output_file"]:
            data["output_file"] = data["output_file"].replace(
                "reprocessed", "processed"
            )
            needs_update = True

        # Update any other paths if they exist
        for key in ["source_file", "chunk_file", "metadata_file"]:
            if key in data and "reprocessed" in str(data[key]):
                data[key] = str(data[key]).replace("reprocessed", "processed")
                needs_update = True

        if needs_update:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True

        return False

    except Exception as e:
        print(f"❌ Error updating {file_path}: {e}")
        return False


def main():
    """Update all metadata files."""
    metadata_dir = Path("data/processed/metadata")

    if not metadata_dir.exists():
        print(f"❌ Metadata directory not found: {metadata_dir}")
        return

    print("=" * 80)
    print("UPDATING METADATA FILES: reprocessed → processed")
    print("=" * 80)
    print(f"Directory: {metadata_dir}")
    print()

    # Find all JSON files
    json_files = list(metadata_dir.glob("*.json"))
    print(f"📄 Found {len(json_files)} metadata files\n")

    # Update each file
    updated_count = 0
    for file_path in json_files:
        if update_metadata_file(file_path):
            print(f"  ✓ {file_path.name}")
            updated_count += 1

    # Summary
    print()
    print("=" * 80)
    print(f"✅ Updated {updated_count}/{len(json_files)} files")
    print("=" * 80)


if __name__ == "__main__":
    main()
