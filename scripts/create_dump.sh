#!/bin/bash

# Script to create PostgreSQL database dump
# Reads connection info from .env file

set -e

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "❌ Error: .env file not found!"
    exit 1
fi

# Parse DATABASE_URL (format: postgresql+psycopg://user:password@host:port/dbname)
if [ -z "$DATABASE_URL" ]; then
    echo "❌ Error: DATABASE_URL not set in .env"
    exit 1
fi

# Extract connection parameters
DB_URL="${DATABASE_URL#postgresql+psycopg://}"
DB_URL="${DB_URL#postgresql://}"

# Parse user:password@host:port/dbname
DB_USER=$(echo $DB_URL | cut -d':' -f1)
DB_PASS=$(echo $DB_URL | cut -d':' -f2 | cut -d'@' -f1)
DB_HOST=$(echo $DB_URL | cut -d'@' -f2 | cut -d':' -f1)
DB_PORT=$(echo $DB_URL | cut -d':' -f3 | cut -d'/' -f1)
DB_NAME=$(echo $DB_URL | cut -d'/' -f2)

# Generate dump filename with timestamp
DUMP_FILE="ragdb_dump_$(date +%Y%m%d_%H%M%S).pg"

echo "📊 Creating PostgreSQL dump..."
echo "   Database: $DB_NAME"
echo "   Host: $DB_HOST:$DB_PORT"
echo "   User: $DB_USER"
echo "   Output: $DUMP_FILE"
echo ""

# Set password for pg_dump (avoid password prompt)
export PGPASSWORD="$DB_PASS"

# Create dump (plain SQL format)
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    -F p \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges \
    -f "$DUMP_FILE"

# Unset password
unset PGPASSWORD

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Dump created successfully!"
    echo "📁 File: $DUMP_FILE"
    
    # Show file size
    FILE_SIZE=$(du -h "$DUMP_FILE" | cut -f1)
    echo "💾 Size: $FILE_SIZE"
    
    # Count lines
    LINE_COUNT=$(wc -l < "$DUMP_FILE")
    echo "📝 Lines: $LINE_COUNT"
    
    echo ""
    echo "💡 To restore this dump:"
    echo "   psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME < $DUMP_FILE"
else
    echo ""
    echo "❌ Dump failed!"
    exit 1
fi
