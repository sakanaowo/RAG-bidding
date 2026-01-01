"""
Setup script for Alembic migrations

Usage:
    python scripts/setup_alembic.py init    # Initialize Alembic
    python scripts/setup_alembic.py create  # Create initial migration
    python scripts/setup_alembic.py upgrade # Apply migrations
    python scripts/setup_alembic.py status  # Check migration status
"""

import os
import sys
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text, inspect
from src.models.base import engine


def run_command(cmd: list[str]):
    """Run shell command and print output"""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)

    return result.returncode == 0


def check_alembic_installed():
    """Check if Alembic is installed"""
    try:
        import alembic

        print(f"✅ Alembic version {alembic.__version__} is installed")
        return True
    except ImportError:
        print("❌ Alembic is not installed")
        print("Install with: pip install alembic")
        return False


def check_current_schema():
    """Check current database schema"""
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    print(f"\n=== Current Database Schema ===")
    print(f"Tables: {len(tables)}")
    for table in tables:
        columns = inspector.get_columns(table)
        indexes = inspector.get_indexes(table)
        print(f"\n{table}:")
        print(f"  - Columns: {len(columns)}")
        print(f"  - Indexes: {len(indexes)}")


def init_alembic():
    """Initialize Alembic (already done, just verify)"""
    alembic_dir = project_root / "alembic"

    if alembic_dir.exists():
        print("✅ Alembic directory already exists")
        return True

    print("❌ Alembic directory not found")
    print("Run: alembic init alembic")
    return False


def create_initial_migration():
    """Create initial migration from current schema"""
    print("\n=== Creating Initial Migration ===")

    # Generate migration
    success = run_command(
        [
            "alembic",
            "revision",
            "--autogenerate",
            "-m",
            "Initial schema with documents and embeddings",
        ]
    )

    if success:
        print("✅ Migration created successfully")
        print("\nNext steps:")
        print("1. Review the generated migration in alembic/versions/")
        print("2. Run: alembic upgrade head")
    else:
        print("❌ Failed to create migration")


def upgrade_database():
    """Apply all pending migrations"""
    print("\n=== Applying Migrations ===")

    success = run_command(["alembic", "upgrade", "head"])

    if success:
        print("✅ Database upgraded successfully")
    else:
        print("❌ Migration failed")


def show_status():
    """Show current migration status"""
    print("\n=== Migration Status ===")
    run_command(["alembic", "current"])

    print("\n=== Migration History ===")
    run_command(["alembic", "history", "--verbose"])


def main():
    """Main entry point"""
    if not check_alembic_installed():
        return

    # Parse command
    if len(sys.argv) < 2:
        print("Usage: python scripts/setup_alembic.py [init|create|upgrade|status]")
        return

    command = sys.argv[1]

    if command == "init":
        init_alembic()
        check_current_schema()

    elif command == "create":
        create_initial_migration()

    elif command == "upgrade":
        upgrade_database()
        show_status()

    elif command == "status":
        show_status()
        check_current_schema()

    else:
        print(f"Unknown command: {command}")
        print("Available commands: init, create, upgrade, status")


if __name__ == "__main__":
    main()
