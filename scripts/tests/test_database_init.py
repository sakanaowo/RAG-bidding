"""
Simple test to check if async database initialization works.
"""

import asyncio
from src.config.database import init_database, startup_database, get_db_config
from sqlalchemy import text


async def test_database():
    """Test database connectivity."""
    print("1️⃣ Initializing database...")
    init_database()

    print("2️⃣ Starting database pool...")
    await startup_database()

    print("3️⃣ Getting database config...")
    db_config = get_db_config()

    print("4️⃣ Testing query...")
    async with db_config.get_session() as session:
        result = await session.execute(
            text("SELECT COUNT(*) FROM langchain_pg_embedding")
        )
        count = result.scalar()
        print(f"✅ Found {count} documents in database")

    print("5️⃣ Getting pool status...")
    status = await db_config.get_pool_status()
    print(f"Pool: {status['pool_metrics']}")

    print("✅ Database test PASSED")


if __name__ == "__main__":
    asyncio.run(test_database())
