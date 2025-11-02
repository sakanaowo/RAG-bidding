#!/usr/bin/env python3
"""
Migration script: reprocessed → processed
Renames directories and updates all code references.
"""
import os
import re
import shutil
from pathlib import Path
from typing import List, Tuple


class ReprocessedToProcessedMigration:
    """Handle migration from 'reprocessed' to 'processed' naming."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.data_dir = project_root / "data"
        self.scripts_dir = project_root / "scripts"
        self.src_dir = project_root / "src"

    def create_backup(self) -> Path:
        """Create backup of important files."""
        backup_dir = self.project_root / "backup_before_migration"
        backup_dir.mkdir(exist_ok=True)

        print(f"📦 Creating backup in {backup_dir}")

        # Backup key files
        files_to_backup = [
            self.data_dir / "reprocessed",
        ]

        for file_path in files_to_backup:
            if file_path.exists():
                if file_path.is_dir():
                    dest = backup_dir / file_path.name
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(file_path, dest)
                    print(f"  ✓ Backed up directory: {file_path.name}")
                else:
                    shutil.copy2(file_path, backup_dir)
                    print(f"  ✓ Backed up file: {file_path.name}")

        return backup_dir

    def move_directories(self):
        """Move/rename reprocessed directories to processed."""
        moves = [
            (self.data_dir / "reprocessed", self.data_dir / "processed"),
        ]

        print("\n📁 Moving directories...")
        for old_path, new_path in moves:
            if old_path.exists():
                if new_path.exists():
                    print(f"  ⚠️  {new_path} already exists, merging...")
                    # Merge directories
                    for item in old_path.iterdir():
                        dest = new_path / item.name
                        if item.is_dir():
                            if dest.exists():
                                shutil.rmtree(dest)
                            shutil.move(str(item), str(dest))
                        else:
                            shutil.move(str(item), str(dest))
                    shutil.rmtree(old_path)
                else:
                    shutil.move(str(old_path), str(new_path))
                print(f"  ✓ {old_path.name} → {new_path.name}")
            else:
                print(f"  ⚠️  {old_path} not found, skipping")

    def update_python_files(self):
        """Update all Python files with new paths."""
        print("\n🔧 Updating Python files...")

        patterns = [
            (r"data/reprocessed", "data/processed"),
            (r"data\\reprocessed", "data\\processed"),
            (r'"reprocessed"', '"processed"'),
            (r"'reprocessed'", "'processed'"),
            (r"reprocessed_with_doc", "processed_with_doc"),
        ]

        python_files = list(self.scripts_dir.glob("**/*.py"))
        python_files.extend(self.src_dir.glob("**/*.py"))

        updated_files = []
        for file_path in python_files:
            if self._update_file(file_path, patterns):
                updated_files.append(file_path.relative_to(self.project_root))

        if updated_files:
            print(f"  ✓ Updated {len(updated_files)} files:")
            for f in updated_files:
                print(f"    - {f}")
        else:
            print("  ℹ️  No files needed updates")

    def _update_file(self, file_path: Path, patterns: List[Tuple[str, str]]) -> bool:
        """Update a single file with pattern replacements."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content
            for pattern, replacement in patterns:
                content = re.sub(pattern, replacement, content)

            if content != original_content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                return True

            return False

        except Exception as e:
            print(f"    ⚠️  Error updating {file_path}: {e}")
            return False

    def validate_migration(self):
        """Validate migration was successful."""
        print("\n✅ Validating migration...")

        checks = [
            (self.data_dir / "processed", "data/processed directory exists"),
            (self.data_dir / "processed" / "chunks", "chunks directory exists"),
            (
                not (self.data_dir / "reprocessed").exists(),
                "old reprocessed directory removed",
            ),
        ]

        all_passed = True
        for check, description in checks:
            if isinstance(check, bool):
                passed = check
            else:
                passed = check.exists()

            status = "✓" if passed else "✗"
            print(f"  {status} {description}")

            if not passed:
                all_passed = False

        # Check for any remaining "reprocessed" references
        print("\n🔍 Checking for remaining 'reprocessed' references...")
        remaining = self._find_remaining_references()

        if remaining:
            print(f"  ⚠️  Found {len(remaining)} files with 'reprocessed' references:")
            for f in remaining[:10]:  # Show first 10
                print(f"    - {f}")
            if len(remaining) > 10:
                print(f"    ... and {len(remaining) - 10} more")
            all_passed = False
        else:
            print("  ✓ No 'reprocessed' references found")

        return all_passed

    def _find_remaining_references(self) -> List[Path]:
        """Find files still containing 'reprocessed'."""
        remaining = []

        search_dirs = [self.scripts_dir, self.src_dir]
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue

            for file_path in search_dir.glob("**/*.py"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    if "reprocessed" in content.lower():
                        remaining.append(file_path.relative_to(self.project_root))
                except Exception:
                    pass

        return remaining

    def run(self):
        """Execute full migration."""
        print("=" * 80)
        print("MIGRATION: reprocessed → processed")
        print("=" * 80)
        print(f"Project root: {self.project_root}")
        print()

        # Create backup
        backup_dir = self.create_backup()
        print(f"\n✓ Backup created at: {backup_dir}")

        # Move directories
        self.move_directories()

        # Update Python files
        self.update_python_files()

        # Validate
        print()
        success = self.validate_migration()

        print("\n" + "=" * 80)
        if success:
            print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
        else:
            print("⚠️  MIGRATION COMPLETED WITH WARNINGS")
        print("=" * 80)


def main():
    """Run migration."""
    project_root = Path(__file__).parent.parent

    migration = ReprocessedToProcessedMigration(project_root)
    migration.run()


if __name__ == "__main__":
    main()
