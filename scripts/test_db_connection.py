#!/usr/bin/env python3
"""
Test SQLAlchemy models and database connection
Quick verification script
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from src.models.base import SessionLocal, engine
from src.models.db_utils import verify_schema, get_database_stats


def test_connection():
    """Test basic database connection"""
    print("Testing database connection...")
    try:
        with SessionLocal() as db:
            result = db.execute(text("SELECT 1")).scalar()
            if result == 1:
                print("✅ Database connection successful")
                return True
            else:
                print("❌ Unexpected result from database")
                return False
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


def test_schema():
    """Test schema verification"""
    print("\nVerifying database schema...")
    try:
        verify_schema()
        return True
    except Exception as e:
        print(f"❌ Schema verification failed: {e}")
        return False


def test_stats():
    """Test database statistics"""
    print("\nGetting database statistics...")
    try:
        import json

        stats = get_database_stats()
        print(json.dumps(stats, indent=2, default=str))
        return True
    except Exception as e:
        print(f"❌ Failed to get stats: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("SQLAlchemy Database Connection Test")
    print("=" * 60)

    tests = [
        ("Connection", test_connection),
        ("Schema", test_schema),
        ("Statistics", test_stats),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"❌ Test '{name}' crashed: {e}")
            results.append((name, False))

    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)

    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {name}")

    all_passed = all(success for _, success in results)

    if all_passed:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n⚠️ Some tests failed. Check errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
