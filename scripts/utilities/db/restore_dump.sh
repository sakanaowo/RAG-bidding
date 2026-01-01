#!/bin/bash

################################################################################
# Database Restore Script - RAG Bidding System
# Purpose: Restore database dump on target machine
# Usage: ./restore_dump.sh <dump_file>
################################################################################

set -e

# Check if dump file is provided
if [ -z "$1" ]; then
    echo "❌ Error: No dump file specified"
    echo ""
    echo "Usage: $0 <dump_file>"
    echo ""
    echo "Examples:"
    echo "  $0 backup/exports/rag_bidding_v2_20251125_123456.dump"
    echo "  $0 backup/exports/rag_bidding_v2_20251125_123456.sql.gz"
    echo ""
    exit 1
fi

DUMP_FILE="$1"

# Check if dump file exists
if [ ! -f "$DUMP_FILE" ]; then
    echo "❌ Error: Dump file not found: $DUMP_FILE"
    exit 1
fi

# Load environment variables
if [ -f .env ]; then
    set -a
    source .env
    set +a
    echo "✅ Loaded .env file"
else
    echo "⚠️  Warning: .env file not found"
    echo "Using default values or manual input..."
fi

# Database configuration
DB_USER="${DB_USER:-sakana}"
DB_PASSWORD="${DB_PASSWORD:-sakana123}"
DB_NAME="${DB_NAME:-rag_bidding_v2}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

echo "════════════════════════════════════════════════════════════════"
echo "DATABASE RESTORE - RAG BIDDING SYSTEM"
echo "════════════════════════════════════════════════════════════════"
echo "Database: $DB_NAME"
echo "User: $DB_USER"
echo "Host: $DB_HOST:$DB_PORT"
echo "Dump File: $DUMP_FILE"
echo ""

# Set password
export PGPASSWORD="$DB_PASSWORD"

# Detect dump file type
if [[ "$DUMP_FILE" == *.dump ]]; then
    DUMP_TYPE="custom"
elif [[ "$DUMP_FILE" == *.sql.gz ]]; then
    DUMP_TYPE="sql_compressed"
elif [[ "$DUMP_FILE" == *.sql ]]; then
    DUMP_TYPE="sql"
else
    echo "❌ Unknown dump file type"
    echo "Supported: .dump, .sql, .sql.gz"
    exit 1
fi

echo "📦 Dump Type: $DUMP_TYPE"
echo ""

################################################################################
# Pre-flight Checks
################################################################################
echo "🔍 Pre-flight checks..."

# Check PostgreSQL connection
echo "  Checking PostgreSQL connection..."
if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "SELECT 1" > /dev/null 2>&1; then
    echo "  ✅ PostgreSQL is accessible"
else
    echo "  ❌ Cannot connect to PostgreSQL"
    echo "  Please ensure PostgreSQL is running and accessible"
    echo "  Check your DB_USER and DB_PASSWORD in .env file"
    exit 1
fi

# Check pgvector extension
echo "  Checking pgvector extension..."
PGVECTOR_AVAILABLE=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -t -c "SELECT COUNT(*) FROM pg_available_extensions WHERE name = 'vector';" | xargs)
if [ "$PGVECTOR_AVAILABLE" -eq "1" ]; then
    echo "  ✅ pgvector extension is available"
else
    echo "  ❌ pgvector extension not found"
    echo "  Please install: sudo apt install postgresql-18-pgvector"
    exit 1
fi

# Check if database already exists
DB_EXISTS=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -t -c "SELECT COUNT(*) FROM pg_database WHERE datname = '$DB_NAME';" | xargs)

if [ "$DB_EXISTS" -eq "1" ]; then
    echo ""
    echo "⚠️  WARNING: Database '$DB_NAME' already exists!"
    read -p "Do you want to DROP and recreate it? (yes/no): " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        echo "❌ Restoration cancelled"
        exit 1
    fi
    
    echo "  Dropping existing database..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME;"
    echo "  ✅ Database dropped"
fi

echo ""

################################################################################
# Create Database
################################################################################
echo "📁 Creating database '$DB_NAME'..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "CREATE DATABASE $DB_NAME;"
echo "✅ Database created"
echo ""

################################################################################
# Enable Extensions
################################################################################
echo "🔌 Enabling pgvector extension..."
# Try with current user first, fallback to postgres if permission denied
if ! psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null; then
    echo "  ⚠️  Need superuser for extension, using postgres..."
    sudo -u postgres psql -d "$DB_NAME" -c "CREATE EXTENSION IF NOT EXISTS vector;"
fi
echo "✅ pgvector enabled"
echo ""

################################################################################
# Restore Data
################################################################################
echo "📥 Restoring data from dump..."
echo ""

if [ "$DUMP_TYPE" == "custom" ]; then
    # Restore from custom format (.dump)
    echo "Using pg_restore for custom format dump..."
    pg_restore -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -v "$DUMP_FILE"
    
elif [ "$DUMP_TYPE" == "sql_compressed" ]; then
    # Restore from compressed SQL (.sql.gz)
    echo "Decompressing and restoring SQL dump..."
    gunzip -c "$DUMP_FILE" | psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME"
    
elif [ "$DUMP_TYPE" == "sql" ]; then
    # Restore from plain SQL (.sql)
    echo "Restoring from SQL dump..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$DUMP_FILE"
fi

echo ""
echo "✅ Data restored"
echo ""

################################################################################
# Grant Permissions
################################################################################
echo "🔐 Ensuring permissions for user '$DB_USER'..."

# Grant permissions (user sakana is already the owner, but ensure full access)
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" << EOF
GRANT ALL ON SCHEMA public TO $DB_USER;
GRANT ALL ON ALL TABLES IN SCHEMA public TO $DB_USER;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;
EOF

echo "✅ Permissions ensured"
echo ""

################################################################################
# Verification
################################################################################
echo "🔍 Verifying restoration..."
echo ""

# Check extensions
echo "Extensions:"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "\dx" | grep -E "(vector|Name)"
echo ""

# Check tables
echo "Tables:"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "\dt" | grep -E "(documents|langchain|Name)"
echo ""

# Check data counts
DOCS_COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM documents;" 2>/dev/null | xargs || echo "0")
CHUNKS_COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM langchain_pg_embedding;" 2>/dev/null | xargs || echo "0")
DB_SIZE=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT pg_size_pretty(pg_database_size('$DB_NAME'));" | xargs)

echo "Data Counts:"
echo "  Documents: $DOCS_COUNT"
echo "  Chunks: $CHUNKS_COUNT"
echo "  Database Size: $DB_SIZE"
echo ""

# Unset password
unset PGPASSWORD

################################################################################
# Summary
################################################################################
echo "════════════════════════════════════════════════════════════════"
echo "✅ RESTORATION COMPLETED"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Database: $DB_NAME"
echo "Documents: $DOCS_COUNT"
echo "Chunks: $CHUNKS_COUNT"
echo "Size: $DB_SIZE"
echo ""
echo "📝 Next Steps:"
echo "  1. Update .env file with correct DATABASE_URL"
echo "  2. Test connection: python -c 'from src.config.models import settings; print(settings.database_url)'"
echo "  3. Start server: ./start_server.sh"
echo "  4. Test API: curl http://localhost:8000/health"
echo ""
echo "════════════════════════════════════════════════════════════════"
