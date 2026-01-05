#!/usr/bin/env python3
"""
Create Test Users Script
Tạo 100 users (test001 -> test100) trong database để test hiệu năng
"""

import sys
import os
from datetime import datetime

# Thêm src vào Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from sqlalchemy.orm import Session
from src.models.base import SessionLocal, engine
from src.models.users import User
from src.auth.password import PasswordHasher


def create_test_users(
    start: int = 1,
    end: int = 100,
    password: str = "TestPass123!",
    force_recreate: bool = False,
):
    """
    Tạo test users từ test001 đến test100

    Args:
        start: Số bắt đầu (default: 1)
        end: Số kết thúc (default: 100)
        password: Password chung cho tất cả test users
        force_recreate: Xóa và tạo lại nếu user đã tồn tại
    """
    password_hasher = PasswordHasher()
    password_hash = password_hasher.hash(password)

    db: Session = SessionLocal()

    try:
        created_count = 0
        skipped_count = 0
        updated_count = 0

        print(f"\n{'='*60}")
        print(f"🚀 Creating Test Users (test{start:03d} -> test{end:03d})")
        print(f"{'='*60}")
        print(f"📧 Email format: testXXX@testmail.com")
        print(f"🔐 Password: {password}")
        print(f"🔄 Force recreate: {force_recreate}")
        print(f"{'='*60}\n")

        for i in range(start, end + 1):
            username = f"test{i:03d}"
            email = f"test{i:03d}@testmail.com"
            full_name = f"Test User {i:03d}"

            # Check if user already exists
            existing_user = db.query(User).filter(User.email == email).first()

            if existing_user:
                if force_recreate:
                    # Update existing user
                    existing_user.username = username
                    existing_user.password_hash = password_hash
                    existing_user.full_name = full_name
                    existing_user.is_active = True
                    existing_user.role = "user"
                    updated_count += 1
                    if i % 20 == 0 or i == end:
                        print(f"🔄 Updated: {username} ({email})")
                else:
                    skipped_count += 1
                    if i % 20 == 0 or i == end:
                        print(f"⏭️  Skipped (exists): {username}")
            else:
                # Create new user
                new_user = User(
                    email=email,
                    username=username,
                    password_hash=password_hash,
                    full_name=full_name,
                    role="user",
                    is_active=True,
                )
                db.add(new_user)
                created_count += 1
                if i % 20 == 0 or i == end:
                    print(f"✅ Created: {username} ({email})")

        # Commit changes
        db.commit()

        print(f"\n{'='*60}")
        print(f"📊 SUMMARY")
        print(f"{'='*60}")
        print(f"✅ Created: {created_count} users")
        print(f"🔄 Updated: {updated_count} users")
        print(f"⏭️  Skipped: {skipped_count} users")
        print(f"📝 Total: {created_count + updated_count + skipped_count} users")
        print(f"{'='*60}\n")

        # Verify users
        total_test_users = (
            db.query(User).filter(User.email.like("test%@testmail.com")).count()
        )
        print(f"🔍 Total test users in DB: {total_test_users}")

        return {
            "created": created_count,
            "updated": updated_count,
            "skipped": skipped_count,
            "total_in_db": total_test_users,
        }

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        db.close()


def list_test_users():
    """Liệt kê tất cả test users trong database"""
    db: Session = SessionLocal()

    try:
        users = (
            db.query(User)
            .filter(User.email.like("test%@testmail.com"))
            .order_by(User.email)
            .all()
        )

        print(f"\n{'='*60}")
        print(f"📋 Test Users in Database ({len(users)} users)")
        print(f"{'='*60}")

        for user in users:
            status = "✅ Active" if user.is_active else "❌ Inactive"
            print(f"{user.username:12s} | {user.email:25s} | {status}")

        print(f"{'='*60}\n")

        return users

    finally:
        db.close()


def delete_test_users():
    """Xóa tất cả test users (test001 -> test100)"""
    db: Session = SessionLocal()

    try:
        deleted_count = (
            db.query(User)
            .filter(User.email.like("test%@testmail.com"))
            .delete(synchronize_session=False)
        )

        db.commit()

        print(f"\n🗑️  Deleted {deleted_count} test users")

        return deleted_count

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        db.close()


def get_user_credentials(start: int = 1, end: int = 100) -> list:
    """
    Lấy danh sách credentials của test users

    Returns:
        List of dicts với email và password
    """
    credentials = []
    for i in range(start, end + 1):
        credentials.append(
            {
                "email": f"test{i:03d}@testmail.com",
                "password": "TestPass123!",
                "username": f"test{i:03d}",
            }
        )
    return credentials


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Manage test users for performance testing"
    )
    parser.add_argument(
        "action",
        choices=["create", "list", "delete", "recreate"],
        help="Action to perform",
    )
    parser.add_argument(
        "--start", type=int, default=1, help="Start number (default: 1)"
    )
    parser.add_argument(
        "--end", type=int, default=100, help="End number (default: 100)"
    )
    parser.add_argument(
        "--password",
        type=str,
        default="TestPass123!",
        help="Password for all test users (default: TestPass123!)",
    )

    args = parser.parse_args()

    if args.action == "create":
        create_test_users(
            start=args.start, end=args.end, password=args.password, force_recreate=False
        )
    elif args.action == "list":
        list_test_users()
    elif args.action == "delete":
        confirm = input("⚠️  Are you sure you want to delete all test users? (yes/no): ")
        if confirm.lower() == "yes":
            delete_test_users()
        else:
            print("Cancelled.")
    elif args.action == "recreate":
        confirm = input(
            "⚠️  This will delete and recreate all test users. Continue? (yes/no): "
        )
        if confirm.lower() == "yes":
            delete_test_users()
            create_test_users(
                start=args.start,
                end=args.end,
                password=args.password,
                force_recreate=False,
            )
        else:
            print("Cancelled.")
