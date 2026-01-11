#!/usr/bin/env python3
"""
Create Test Admin User for Analytics Dashboard Testing

This script creates the admin user needed for integration tests.

Credentials:
- Email: admin@example.com
- Password: Admin123456
- Role: admin

Usage:
    python scripts/tests/create_test_admin.py

Requirements:
    - Database must be running and accessible
    - Environment variables must be configured (DATABASE_URL or .env file)
"""

import sys
import os
import argparse

# Add project root to path
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from uuid import uuid4
from datetime import datetime

# Load environment variables
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


def create_admin_user(
    email: str = "admin@example.com",
    password: str = "Admin123456",
    username: str = "admin",
    full_name: str = "Test Admin",
    force_create: bool = False,
):
    """
    Create an admin user for testing.

    Args:
        email: Admin email
        password: Admin password
        username: Admin username
        full_name: Admin full name
        force_create: If True, update existing user to admin role
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from src.config.models import settings
    from src.models.users import User
    from src.auth.password import password_hasher

    print(f"🔐 Creating test admin user: {email}")
    print(f"📊 Database: {settings.database_url[:50]}...")

    # Create database connection
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Check if user exists
        existing_user = session.query(User).filter(User.email == email).first()

        if existing_user:
            if force_create:
                print(f"⚠️  User {email} exists, updating to admin role...")
                existing_user.role = "admin"
                existing_user.is_active = True
                existing_user.is_verified = True
                existing_user.password_hash = password_hasher.hash(password)
                session.commit()
                print(f"✅ User updated: {email} (role=admin)")
                return existing_user
            else:
                print(f"ℹ️  User {email} already exists (role={existing_user.role})")
                if existing_user.role != "admin":
                    print(f"   Use --force to update role to admin")
                return existing_user

        # Create new admin user
        admin_user = User(
            id=uuid4(),
            email=email,
            username=username,
            full_name=full_name,
            password_hash=password_hasher.hash(password),
            role="admin",
            is_active=True,
            is_verified=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        session.add(admin_user)
        session.commit()

        print(f"✅ Admin user created successfully!")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        print(f"   Role: admin")
        print(f"   ID: {admin_user.id}")

        return admin_user

    except Exception as e:
        session.rollback()
        print(f"❌ Error creating admin user: {e}")
        raise
    finally:
        session.close()


def create_regular_user(
    email: str = "user@example.com",
    password: str = "User123456",
    username: str = "testuser",
    full_name: str = "Test User",
):
    """Create a regular (non-admin) user for testing."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from src.config.models import settings
    from src.models.users import User
    from src.auth.password import password_hasher

    print(f"👤 Creating test user: {email}")

    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Check if user exists
        existing_user = session.query(User).filter(User.email == email).first()

        if existing_user:
            print(f"ℹ️  User {email} already exists (role={existing_user.role})")
            return existing_user

        # Create new user
        user = User(
            id=uuid4(),
            email=email,
            username=username,
            full_name=full_name,
            password_hash=password_hasher.hash(password),
            role="user",
            is_active=True,
            is_verified=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        session.add(user)
        session.commit()

        print(f"✅ User created successfully!")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        print(f"   Role: user")

        return user

    except Exception as e:
        session.rollback()
        print(f"❌ Error creating user: {e}")
        raise
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(
        description="Create test admin user for analytics dashboard testing"
    )
    parser.add_argument(
        "--email",
        default="admin@example.com",
        help="Admin email (default: admin@example.com)",
    )
    parser.add_argument(
        "--password",
        default="Admin123456",
        help="Admin password (default: Admin123456)",
    )
    parser.add_argument(
        "--username",
        default="admin",
        help="Admin username (default: admin)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force update existing user to admin role",
    )
    parser.add_argument(
        "--with-user",
        action="store_true",
        help="Also create a regular test user",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("  Analytics Dashboard Test User Setup")
    print("=" * 60)
    print()

    # Create admin user
    create_admin_user(
        email=args.email,
        password=args.password,
        username=args.username,
        force_create=args.force,
    )

    # Optionally create regular user
    if args.with_user:
        print()
        create_regular_user()

    print()
    print("=" * 60)
    print("  Test Credentials Summary")
    print("=" * 60)
    print(f"  Admin: {args.email} / {args.password}")
    if args.with_user:
        print(f"  User:  user@example.com / User123456")
    print()
    print("  To run integration tests:")
    print("  pytest tests/integration/test_analytics_dashboard.py -v")
    print("=" * 60)


if __name__ == "__main__":
    main()
