#!/bin/bash

# This script sets up a PostgreSQL database with the pgvector extension.
# Please make sure you have sudo privileges to run this script.

# --- Configuration ---
# Replace with your desired database name, user, and password.
DB_NAME="rag_bidding_v2"
DB_USER="rag_user"
DB_PASSWORD="your_secure_password"
PG_VERSION="18" # Make sure this version is available for your system

# --- Installation ---

# Update package lists
sudo apt-get update

# Install PostgreSQL and contrib packages
# The -y flag automatically answers "yes" to prompts.
sudo apt-get install -y postgresql-$PG_VERSION postgresql-contrib

# Install the pgvector extension
# The package name depends on your PostgreSQL version.
sudo apt-get install -y postgresql-$PG_VERSION-pgvector

# --- Database Setup ---

# The following commands are executed as the 'postgres' user.
# Create a new database user
sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"

# Create a new database
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME;"

# Grant all privileges on the new database to the new user
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"

# --- Enable pgvector extension ---

# Connect to the new database and enable the vector extension
sudo -u postgres psql -d $DB_NAME -c "CREATE EXTENSION IF NOT EXISTS vector;"

# --- Grant Schema Permissions ---

# Grant permissions on public schema
sudo -u postgres psql -d $DB_NAME -c "GRANT ALL ON SCHEMA public TO $DB_USER;"
sudo -u postgres psql -d $DB_NAME -c "GRANT ALL ON ALL TABLES IN SCHEMA public TO $DB_USER;"
sudo -u postgres psql -d $DB_NAME -c "GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO $DB_USER;"
sudo -u postgres psql -d $DB_NAME -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;"

# --- Verification ---

echo ""
echo "✅ Database setup complete!"
echo "================================"
echo "Database: $DB_NAME"
echo "User: $DB_USER"
echo "Password: $DB_PASSWORD"
echo ""
echo "📝 Next steps:"
echo "1. Update .env file with:"
echo "   DATABASE_URL=postgresql+psycopg://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME"
echo "   LC_COLLECTION=docs"
echo ""
echo "2. Activate conda environment:"
echo "   conda activate rag-bidding"
echo ""
echo "3. Bootstrap database tables:"
echo "   python scripts/bootstrap_db.py"
echo ""
echo "4. Import data:"
echo "   python scripts/import_processed_chunks.py"
echo ""
echo "Verify setup:"
echo "   psql -U $DB_USER -d $DB_NAME -h localhost -c '\dx'"
echo ""

# --- Backup & Restore Commands (for reference) ---
# 
# Create backup:
# pg_dump -U $DB_USER -d $DB_NAME -F c -f rag_bidding_backup.dump
#
# Restore from backup:
# pg_restore -U $DB_USER -d $DB_NAME -c rag_bidding_backup.dump
#
# Export to SQL:
# pg_dump -U $DB_USER -d $DB_NAME > rag_bidding_backup.sql
#
# Current configuration for .env:
# DATABASE_URL=postgresql+psycopg://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME
# LC_COLLECTION=docs
# EMBED_MODEL=text-embedding-3-large  # 3072 dimensions (native)
# LLM_MODEL=gpt-4o-mini
