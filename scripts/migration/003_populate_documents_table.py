"""
Populate Documents Table - Simple Version
Load extracted metadata into PostgreSQL documents table
"""

import json
import asyncio
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from datetime import datetime
import os


# Get database URL from environment or use default
DATABASE_URL = os.getenv(
    "DATABASE_URL_ASYNC",
    "postgresql+asyncpg://sakana:sakana123@localhost/rag_bidding_v2",
)


async def create_documents_table(engine):
    """Create documents table if not exists using psql command"""

    print("📊 Creating documents table...")

    # Use psql command to execute SQL file directly
    # This handles complex SQL like functions with $$ properly
    schema_file = Path("scripts/migration/001_simple_documents_schema.sql")

    # Build psql command with proper authentication
    import subprocess
    from urllib.parse import urlparse

    # Get database connection info from engine URL
    # Format: postgresql+asyncpg://user:password@host/database
    url_str = str(engine.url)

    # Parse URL to extract components
    parsed = urlparse(url_str.replace("postgresql+asyncpg://", "postgresql://"))

    # Build psql connection string WITHOUT password (will use env var)
    psql_url = f"postgresql://{parsed.username}@{parsed.hostname}:{parsed.port or 5432}{parsed.path}"

    # Set PGPASSWORD environment variable for psql authentication
    env = os.environ.copy()
    if parsed.password:
        env["PGPASSWORD"] = parsed.password

    try:
        # Execute SQL file using psql with proper authentication
        result = subprocess.run(
            ["psql", psql_url, "-f", str(schema_file)],
            capture_output=True,
            text=True,
            check=False,
            env=env,  # Pass environment with PGPASSWORD
        )

        if result.returncode == 0:
            print("   ✅ Schema created successfully via psql")
        else:
            # Check if errors are just "already exists" warnings
            stderr = result.stderr.lower()
            if "already exists" in stderr or "duplicate" in stderr:
                print("   ✅ Schema already exists (idempotent)")
            else:
                print(f"   ⚠️  psql failed: {result.stderr}")
                print("   📝 Trying fallback method...")
                raise RuntimeError("psql execution failed")  # Trigger fallback

    except (FileNotFoundError, RuntimeError) as e:
        print(f"   ⚠️  psql not available or failed: {e}")
        print("   📝 Falling back to direct SQL execution...")

        # Fallback: Split SQL into individual statements and execute one by one
        # asyncpg cannot execute multiple commands in a prepared statement
        async with engine.begin() as conn:
            with open(schema_file, "r") as f:
                sql = f.read()

            # Split SQL by semicolons BUT preserve function bodies with $$
            statements = []
            current = ""
            in_function = False

            for line in sql.split("\n"):
                current += line + "\n"

                # Track if we're inside a function definition
                if "$$" in line:
                    in_function = not in_function

                # Split on semicolon only if NOT inside function
                if ";" in line and not in_function:
                    # Clean up statement
                    stmt = current.strip()
                    if stmt and not stmt.startswith("--"):
                        statements.append(stmt)
                    current = ""

            # Add last statement if exists
            if current.strip():
                statements.append(current.strip())

            print(f"   📝 Executing {len(statements)} SQL statements...")

            # Execute each statement
            for i, stmt in enumerate(statements, 1):
                try:
                    # Skip comments and empty statements
                    if not stmt or stmt.startswith("--"):
                        continue

                    await conn.execute(text(stmt))

                    if i % 5 == 0:
                        print(f"      ✅ Executed {i}/{len(statements)} statements...")

                except Exception as e:
                    error_msg = str(e).lower()
                    if "already exists" in error_msg or "duplicate" in error_msg:
                        # Ignore "already exists" errors - idempotent
                        continue
                    else:
                        print(f"   ❌ Error executing statement {i}: {e}")
                        print(f"      Statement: {stmt[:100]}...")
                        raise

            print("   ✅ Schema created via fallback method")

    print("✅ Documents table created")


async def populate_documents(engine, documents: list):
    """Insert documents into table"""

    print(f"\n📥 Inserting {len(documents)} documents...")

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        inserted = 0
        skipped = 0

        for doc in documents:
            try:
                # Check if exists
                result = await session.execute(
                    text("SELECT id FROM documents WHERE document_id = :doc_id"),
                    {"doc_id": doc["document_id"]},
                )
                existing = result.fetchone()

                if existing:
                    print(f"   ⏭️  Skipped (exists): {doc['document_id']}")
                    skipped += 1
                    continue

                # Insert new document
                await session.execute(
                    text(
                        """
                        INSERT INTO documents (
                            document_id, document_name, category, document_type,
                            source_file, file_name, total_chunks, status
                        ) VALUES (
                            :document_id, :document_name, :category, :document_type,
                            :source_file, :file_name, :total_chunks, :status
                        )
                    """
                    ),
                    {
                        "document_id": doc["document_id"],
                        "document_name": doc["document_name"],
                        "category": doc["category"],
                        "document_type": doc["document_type"],
                        "source_file": doc["source_file"],
                        "file_name": doc["file_name"],
                        "total_chunks": doc.get("total_chunks", 0),
                        "status": doc.get("status", "active"),
                    },
                )

                inserted += 1

                if inserted % 10 == 0:
                    print(f"   ✅ Inserted {inserted}/{len(documents)}...")

            except Exception as e:
                print(f"   ❌ Error inserting {doc['document_id']}: {e}")

        await session.commit()

        print(f"\n{'='*60}")
        print(f"✅ Inserted: {inserted} documents")
        print(f"⏭️  Skipped: {skipped} documents")
        print(f"📊 Total: {inserted + skipped} documents in database")


async def verify_documents(engine):
    """Verify documents were inserted correctly"""

    print(f"\n🔍 Verifying documents table...")

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Count total
        result = await session.execute(text("SELECT COUNT(*) FROM documents"))
        total = result.scalar()

        print(f"📊 Total documents: {total}")

        # Count by category
        result = await session.execute(
            text(
                """
            SELECT category, COUNT(*) as count
            FROM documents
            GROUP BY category
            ORDER BY count DESC
        """
            )
        )

        print(f"\n📁 Documents by category:")
        for row in result.fetchall():
            print(f"   {row[0]}: {row[1]} documents")

        # Show sample documents
        result = await session.execute(
            text(
                """
            SELECT document_id, document_name, category
            FROM documents
            LIMIT 5
        """
            )
        )

        print(f"\n📄 Sample documents:")
        for row in result.fetchall():
            print(f"   {row[0]}: {row[1][:50]}... ({row[2]})")


async def main():
    """Main migration function"""

    print("🚀 Starting Documents Table Population\n")

    # Load extracted metadata
    metadata_file = Path("data/processed/documents_metadata.json")

    if not metadata_file.exists():
        print(f"❌ Metadata file not found: {metadata_file}")
        print("Run 002_extract_simple_metadata.py first!")
        return

    with open(metadata_file, "r", encoding="utf-8") as f:
        documents = json.load(f)

    print(f"📂 Loaded {len(documents)} documents from metadata file\n")

    # Create engine
    engine = create_async_engine(DATABASE_URL, echo=False)

    try:
        # Step 1: Create table
        await create_documents_table(engine)

        # Step 2: Populate documents
        await populate_documents(engine, documents)

        # Step 3: Verify
        await verify_documents(engine)

        print(f"\n{'='*60}")
        print("✅ Migration completed successfully!")

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
