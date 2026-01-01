#!/bin/bash

################################################################################
# Database Dump Script - RAG Bidding System
# Purpose: Create comprehensive database dump for migration
# Database: rag_bidding_v2 (64 docs, 7,892 chunks, 149 MB)
# Updated: 2025-11-25
################################################################################

set -e

# Output directory
BACKUP_DIR="backup/exports"
mkdir -p "$BACKUP_DIR"

# Load environment variables
if [ -f .env ]; then
    set -a
    source .env
    set +a
else
    echo "❌ Error: .env file not found!"
    exit 1
fi

# Use direct env vars if available, otherwise parse DATABASE_URL
if [ -n "$DB_USER" ] && [ -n "$DB_PASSWORD" ] && [ -n "$DB_NAME" ]; then
    DB_HOST="${DB_HOST:-localhost}"
    DB_PORT="${DB_PORT:-5432}"
else
    # Parse DATABASE_URL as fallback
    if [ -z "$DATABASE_URL" ]; then
        echo "❌ Error: DATABASE_URL not set in .env"
        exit 1
    fi
    
    DB_URL="${DATABASE_URL#postgresql+psycopg://}"
    DB_URL="${DB_URL#postgresql://}"
    
    DB_USER=$(echo $DB_URL | cut -d':' -f1)
    DB_PASSWORD=$(echo $DB_URL | cut -d':' -f2 | cut -d'@' -f1)
    DB_HOST=$(echo $DB_URL | cut -d'@' -f2 | cut -d':' -f1)
    DB_PORT=$(echo $DB_URL | cut -d':' -f3 | cut -d'/' -f1)
    DB_NAME=$(echo $DB_URL | cut -d'/' -f2)
fi

# Timestamp for backup files
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DUMP_PREFIX="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}"

echo "════════════════════════════════════════════════════════════════"
echo "DATABASE DUMP - RAG BIDDING SYSTEM"
echo "════════════════════════════════════════════════════════════════"
echo "Database: $DB_NAME"
echo "User: $DB_USER"
echo "Host: $DB_HOST:$DB_PORT"
echo "Timestamp: $TIMESTAMP"
echo ""

# Set password for pg_dump
export PGPASSWORD="$DB_PASSWORD"

# Check connection
echo "🔍 Checking PostgreSQL connection..."
if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1" > /dev/null 2>&1; then
    echo "✅ Connection successful"
else
    echo "❌ Failed to connect to PostgreSQL"
    exit 1
fi

# Get database statistics
echo ""
echo "📊 Database Statistics:"
echo "─────────────────────────────────────────────────────────────"
TOTAL_DOCS=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM documents;" | xargs)
TOTAL_CHUNKS=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM langchain_pg_embedding;" | xargs)
DB_SIZE=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT pg_size_pretty(pg_database_size('$DB_NAME'));" | xargs)
echo "Documents: $TOTAL_DOCS"
echo "Chunks: $TOTAL_CHUNKS"
echo "Size: $DB_SIZE"
echo "─────────────────────────────────────────────────────────────"
echo ""

echo "🎯 Creating database dumps..."
echo ""

################################################################################
# OPTION 1: Custom Format Dump (Recommended - best for pg_restore)
################################################################################
echo "1️⃣ Creating custom format dump (.dump)..."
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    -F c \
    --verbose \
    -f "${DUMP_PREFIX}.dump" 2>&1 | grep -E "(dumping|completed)" || true

if [ -f "${DUMP_PREFIX}.dump" ]; then
    SIZE=$(du -h "${DUMP_PREFIX}.dump" | cut -f1)
    echo "   ✅ Created: ${DUMP_PREFIX}.dump ($SIZE)"
else
    echo "   ❌ Failed"
fi
echo ""

################################################################################
# OPTION 2: Plain SQL Dump (Human-readable, compressed)
################################################################################
echo "2️⃣ Creating SQL dump (.sql.gz)..."
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --format=plain \
    --no-owner \
    --no-acl \
    --verbose \
    -f "${DUMP_PREFIX}.sql" 2>&1 | grep -E "(dumping|completed)" || true

if [ -f "${DUMP_PREFIX}.sql" ]; then
    gzip -f "${DUMP_PREFIX}.sql"
    SIZE=$(du -h "${DUMP_PREFIX}.sql.gz" | cut -f1)
    echo "   ✅ Created: ${DUMP_PREFIX}.sql.gz ($SIZE)"
else
    echo "   ❌ Failed"
fi
echo ""

################################################################################
# OPTION 3: Schema-Only Dump (For reference)
################################################################################
echo "3️⃣ Creating schema-only dump..."
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --schema-only \
    --no-owner \
    --no-acl \
    -f "${DUMP_PREFIX}_schema.sql" 2>&1 | grep -E "(dumping|completed)" || true

if [ -f "${DUMP_PREFIX}_schema.sql" ]; then
    SIZE=$(du -h "${DUMP_PREFIX}_schema.sql" | cut -f1)
    echo "   ✅ Created: ${DUMP_PREFIX}_schema.sql ($SIZE)"
else
    echo "   ❌ Failed"
fi
echo ""

################################################################################
# Create Metadata File
################################################################################
echo "4️⃣ Creating metadata file..."
METADATA_FILE="${DUMP_PREFIX}_README.txt"

cat > "$METADATA_FILE" << EOF
================================================================================
DATABASE DUMP - RAG BIDDING SYSTEM
================================================================================
Created: $(date '+%Y-%m-%d %H:%M:%S')
Database: $DB_NAME
Host: $DB_HOST:$DB_PORT

STATISTICS:
  Documents: $TOTAL_DOCS
  Chunks: $TOTAL_CHUNKS
  Size: $DB_SIZE

POSTGRESQL VERSION:
$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT version();" | xargs)

EXTENSIONS:
$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "\dx")

TABLES:
  • documents (PRIMARY - 64 documents)
  • langchain_pg_embedding (7,892 chunks)
  • langchain_pg_collection (internal)

FILES CREATED:
$(ls -lh ${DUMP_PREFIX}* | awk '{print "  "$9" ("$5")"}')

================================================================================
RESTORATION ON TARGET MACHINE
================================================================================

PREREQUISITES:
1. PostgreSQL 18+ installed
2. pgvector extension: sudo apt install postgresql-18-pgvector

METHOD 1: Restore from .dump (RECOMMENDED)
───────────────────────────────────────────
# Create database
createdb -U postgres $DB_NAME

# Restore dump
pg_restore -U postgres -d $DB_NAME -v ${DUMP_PREFIX##*/}.dump

# Grant permissions
psql -U postgres -d $DB_NAME << 'SQL'
GRANT ALL ON DATABASE $DB_NAME TO sakana;
GRANT ALL ON SCHEMA public TO sakana;
GRANT ALL ON ALL TABLES IN SCHEMA public TO sakana;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO sakana;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO sakana;
SQL

METHOD 2: Restore from .sql.gz
───────────────────────────────────────────
# Decompress and restore
gunzip -c ${DUMP_PREFIX##*/}.sql.gz | psql -U postgres -d $DB_NAME

VERIFY RESTORATION:
───────────────────────────────────────────
psql -U postgres -d $DB_NAME << 'SQL'
-- Check extensions
\dx

-- Check tables
\dt

-- Check data
SELECT COUNT(*) FROM documents;
SELECT COUNT(*) FROM langchain_pg_embedding;
SELECT pg_size_pretty(pg_database_size('$DB_NAME'));
SQL

TRANSFER TO TARGET:
───────────────────────────────────────────
# Using SCP
scp ${DUMP_PREFIX##*/}.dump user@target:/path/

# Using rsync (resumable)
rsync -avz --progress ${DUMP_PREFIX##*/}.dump user@target:/path/

# Or create archive
tar -czf backup_${TIMESTAMP}.tar.gz ${DUMP_PREFIX##*/}*

ENVIRONMENT SETUP ON TARGET:
───────────────────────────────────────────
Update .env file with:
  DATABASE_URL=postgresql+psycopg://sakana:password@localhost:5432/$DB_NAME
  DB_NAME=$DB_NAME
  DB_USER=sakana
  DB_HOST=localhost
  DB_PORT=5432

Then run:
  conda activate venv
  python scripts/bootstrap_db.py  # If needed
  ./start_server.sh

================================================================================
EOF

echo "   ✅ Created: $METADATA_FILE"
echo ""

# Unset password
unset PGPASSWORD

################################################################################
# Summary
################################################################################
echo "════════════════════════════════════════════════════════════════"
echo "✅ DUMP COMPLETED"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "📁 Files in $BACKUP_DIR:"
ls -lh ${DUMP_PREFIX}* 2>/dev/null | awk '{printf "   %s  %s\n", $5, $9}' || echo "   (No files found)"
echo ""
echo "💡 Recommended for migration:"
echo "   ${DUMP_PREFIX}.dump"
echo ""
echo "📖 See restoration instructions:"
echo "   ${METADATA_FILE}"
echo ""
echo "════════════════════════════════════════════════════════════════"
