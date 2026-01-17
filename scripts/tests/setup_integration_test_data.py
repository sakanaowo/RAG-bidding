"""
Setup script for real integration tests
Creates test users and sample data for testing analytics

Usage:
    python scripts/tests/setup_integration_test_data.py

Requirements:
    - Database must be running and migrated
    - Server should NOT be running (direct DB access)
"""

import sys
import os

# Add project root to path
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

import uuid
from datetime import datetime, timedelta
from decimal import Decimal
import random

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config.settings import settings
from src.models.users import User
from src.models.conversations import Conversation
from src.models.queries import Query
from src.models.messages import Message
from src.models.documents import Document
from src.models.feedback import Feedback
from src.models.user_metrics import UserUsageMetric
from src.auth.password import PasswordHasher

password_hasher = PasswordHasher()


def create_test_users(session):
    """Create admin and regular test users"""
    print("\n📝 Creating test users...")

    # Check if admin exists
    admin = session.query(User).filter(User.email == "admin@test.com").first()
    if not admin:
        admin = User(
            id=uuid.uuid4(),
            email="admin@test.com",
            username="testadmin",
            full_name="Test Admin",
            password_hash=password_hasher.hash("admin123456"),
            role="admin",
            is_active=True,
            created_at=datetime.utcnow(),
        )
        session.add(admin)
        print("  ✅ Created admin user: admin@test.com")
    else:
        # Update role to admin if exists
        admin.role = "admin"
        print("  ✅ Admin user already exists, updated role")

    # Check if regular user exists
    user = session.query(User).filter(User.email == "user@test.com").first()
    if not user:
        user = User(
            id=uuid.uuid4(),
            email="user@test.com",
            username="testuser",
            full_name="Test User",
            password_hash=password_hasher.hash("user123456"),
            role="user",
            is_active=True,
            created_at=datetime.utcnow(),
        )
        session.add(user)
        print("  ✅ Created regular user: user@test.com")
    else:
        print("  ✅ Regular user already exists")

    session.commit()
    return admin, user


def create_sample_queries(session, admin_user, regular_user, num_queries=20):
    """Create sample queries for testing"""
    print(f"\n📝 Creating {num_queries} sample queries...")

    users = [admin_user, regular_user]
    rag_modes = ["full_rag", "no_rag", "hybrid"]

    # Create conversations first
    conversations = []
    for user in users:
        for i in range(3):
            conv = Conversation(
                id=uuid.uuid4(),
                user_id=user.id,
                title=f"Test Conversation {i+1}",
                created_at=datetime.utcnow() - timedelta(days=random.randint(0, 30)),
            )
            session.add(conv)
            conversations.append(conv)

    session.commit()

    # Create queries with varied data
    for i in range(num_queries):
        conversation = random.choice(conversations)
        query_time = datetime.utcnow() - timedelta(
            days=random.randint(0, 30),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
        )

        input_tokens = random.randint(50, 500)
        output_tokens = random.randint(100, 1000)
        total_tokens = input_tokens + output_tokens

        query = Query(
            id=uuid.uuid4(),
            conversation_id=conversation.id,
            user_id=conversation.user_id,
            query_text=f"Test query {i+1}: How to prepare bidding documents?",
            rag_mode=random.choice(rag_modes),
            tokens_total=total_tokens,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=Decimal(str(round(total_tokens * 0.00001, 6))),
            total_latency_ms=random.randint(500, 5000),
            retrieval_count=random.randint(0, 5),
            created_at=query_time,
        )
        session.add(query)

        # Create message for some queries
        msg = None
        if random.random() > 0.3:
            msg = Message(
                id=uuid.uuid4(),
                conversation_id=conversation.id,
                user_id=conversation.user_id,
                role="assistant",
                content=f"Sample response {i+1}: Here is how to prepare bidding documents...",
                rag_mode=query.rag_mode,
                tokens_total=total_tokens,
                created_at=query_time,
            )
            session.add(msg)

        # Create feedback for some messages
        if msg and random.random() > 0.5:
            feedback = Feedback(
                id=uuid.uuid4(),
                message_id=msg.id,
                user_id=conversation.user_id,
                rating=random.choice([1, 2, 3, 4, 5]),
                feedback_type=random.choice(["accuracy", "helpfulness", "relevance"]),
                comment=f"Test feedback {i+1}" if random.random() > 0.7 else None,
                created_at=query_time + timedelta(minutes=5),
            )
            session.add(feedback)

    session.commit()
    print(f"  ✅ Created {num_queries} queries with messages and feedback")


def create_sample_documents(session, num_docs=10):
    """Create sample documents for knowledge base"""
    print(f"\n📝 Creating {num_docs} sample documents...")

    categories = ["Luật chính", "Nghị định", "Thông tư", "Quyết định", "Mẫu báo cáo"]
    doc_types = ["pdf", "docx", "txt"]
    statuses = [
        "active",
        "active",
        "active",
        "pending",
        "archived",
    ]  # Weighted toward active

    for i in range(num_docs):
        doc = Document(
            id=uuid.uuid4(),
            document_name=f"Test Document {i+1}",
            filepath=f"/data/test/doc_{i+1}.pdf",
            filename=f"doc_{i+1}.pdf",
            document_type=random.choice(doc_types),
            category=random.choice(categories),
            status=random.choice(statuses),
            total_chunks=random.randint(10, 100),
            file_size_bytes=random.randint(10000, 1000000),
            created_at=datetime.utcnow() - timedelta(days=random.randint(0, 90)),
        )
        session.add(doc)

    session.commit()
    print(f"  ✅ Created {num_docs} documents")


def create_usage_metrics(session, admin_user, regular_user):
    """Create aggregated usage metrics"""
    print("\n📝 Creating usage metrics...")

    users = [admin_user, regular_user]

    for user in users:
        # Create metrics for last 30 days
        for days_ago in range(30):
            date = datetime.utcnow().date() - timedelta(days=days_ago)

            # Not every day has activity
            if random.random() > 0.3:
                continue

            input_tokens = random.randint(1000, 10000)
            output_tokens = random.randint(2000, 20000)
            total_tokens = input_tokens + output_tokens

            metric = UserUsageMetric(
                id=uuid.uuid4(),
                user_id=user.id,
                date=date,
                total_queries=random.randint(5, 50),
                total_tokens=total_tokens,
                total_input_tokens=input_tokens,
                total_output_tokens=output_tokens,
                total_cost_usd=Decimal(str(round(total_tokens * 0.00001, 6))),
            )
            session.add(metric)

    session.commit()
    print("  ✅ Created usage metrics")


def main():
    """Main setup function"""
    print("=" * 60)
    print("🔧 ANALYTICS INTEGRATION TEST DATA SETUP")
    print("=" * 60)

    # Create database connection
    print(f"\n📌 Connecting to database...")
    print(f"   URL: {settings.database_url[:50]}...")

    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Create test users
        admin, user = create_test_users(session)

        # Create sample data
        create_sample_queries(session, admin, user, num_queries=30)
        create_sample_documents(session, num_docs=15)
        create_usage_metrics(session, admin, user)

        print("\n" + "=" * 60)
        print("✅ SETUP COMPLETE!")
        print("=" * 60)
        print("\nTest credentials:")
        print("  Admin: admin@test.com / admin123456")
        print("  User:  user@test.com / user123456")
        print("\nNext steps:")
        print("  1. Start the server: ./start_server.sh")
        print("  2. Run integration tests:")
        print("     pytest tests/integration/test_analytics_real.py -v")

    except Exception as e:
        session.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
