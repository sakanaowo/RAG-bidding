#!/bin/bash
# =============================================================================
# Cloud SQL Setup Script for RAG-bidding Backend
# =============================================================================
#
# This script sets up the Cloud SQL database with all required tables and 
# extensions for the RAG-bidding application.
#
# Prerequisites:
#   - psql client installed
#   - Cloud SQL instance with pgvector extension enabled
#   - Network access to Cloud SQL (public IP or Cloud SQL Auth Proxy)
#
# Usage:
#   ./scripts/setup_cloud_sql.sh           # Normal run
#   ./scripts/setup_cloud_sql.sh --dry-run # Dry run (show what would be done)
#   ./scripts/setup_cloud_sql.sh -n        # Dry run (short flag)
#
# Environment Variables (load from .env or set manually):
#   CLOUD_DB_CONNECTION_PUBLICIP - Cloud SQL public IP
#   CLOUD_DB_USER               - Database username
#   CLOUD_DB_PASSWORD           - Database password
#   CLOUD_INSTANCE_DB           - Database name
# =============================================================================

set -e

# Parse arguments
DRY_RUN=false
for arg in "$@"; do
    case $arg in
        --dry-run|-n)
            DRY_RUN=true
            shift
            ;;
    esac
done

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE} Cloud SQL Setup for RAG-bidding       ${NC}"
echo -e "${BLUE}========================================${NC}"

if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}🔍 DRY RUN MODE - No changes will be made${NC}"
    echo ""
fi

# Load .env file if exists
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"

if [ -f "$ENV_FILE" ]; then
    echo -e "${GREEN}Loading .env file...${NC}"
    # Load .env safely, only valid KEY=VALUE lines
    while IFS='=' read -r key value; do
        # Skip empty lines and comments
        if [[ -n "$key" ]] && [[ ! "$key" =~ ^[[:space:]]*# ]]; then
            # Remove inline comments from value
            value="${value%%#*}"
            # Trim whitespace
            value="${value%"${value##*[![:space:]]}"}"
            # Strip surrounding quotes (single or double)
            value="${value#\'}"
            value="${value%\'}"
            value="${value#\"}"
            value="${value%\"}"
            # Export the variable
            export "$key=$value"
        fi
    done < <(grep -E '^[A-Za-z_][A-Za-z0-9_]*=' "$ENV_FILE")
else
    echo -e "${YELLOW}No .env file found. Using environment variables.${NC}"
fi

# Configuration
DB_HOST="${CLOUD_DB_CONNECTION_PUBLICIP:-}"
DB_USER="${CLOUD_DB_USER:-}"
DB_PASSWORD="${CLOUD_DB_PASSWORD:-}"
DB_NAME="${CLOUD_INSTANCE_DB:-}"

# Validate required variables
if [ -z "$DB_HOST" ] || [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ] || [ -z "$DB_NAME" ]; then
    echo -e "${RED}Error: Missing required environment variables${NC}"
    echo "Required: CLOUD_DB_CONNECTION_PUBLICIP, CLOUD_DB_USER, CLOUD_DB_PASSWORD, CLOUD_INSTANCE_DB"
    exit 1
fi

echo -e "${GREEN}Configuration:${NC}"
echo "  Host: $DB_HOST"
echo "  User: $DB_USER"
echo "  Database: $DB_NAME"
echo ""

# Export password for psql
export PGPASSWORD="$DB_PASSWORD"

# Function to run SQL
run_sql() {
    if [ "$DRY_RUN" = true ]; then
        echo -e "${BLUE}[DRY RUN] Would execute SQL:${NC} $1"
        return 0
    fi
    psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "$1"
}

# Function to run SQL file
run_sql_file() {
    if [ "$DRY_RUN" = true ]; then
        echo -e "${BLUE}[DRY RUN] Would execute SQL file:${NC} $1"
        return 0
    fi
    psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -f "$1"
}

# Test connection
echo -e "${YELLOW}Testing connection...${NC}"
if [ "$DRY_RUN" = true ]; then
    echo -e "${BLUE}[DRY RUN] Would test connection to:${NC} $DB_HOST as $DB_USER"
    echo -e "${GREEN}✅ Connection test skipped (dry run)${NC}"
else
    if run_sql "SELECT 1 as test;" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Connection successful!${NC}"
    else
        echo -e "${RED}❌ Connection failed. Check your credentials and network access.${NC}"
        exit 1
    fi
fi

# Check pgvector extension
echo -e "${YELLOW}Checking pgvector extension...${NC}"
if [ "$DRY_RUN" = true ]; then
    echo -e "${BLUE}[DRY RUN] Would check if pgvector extension exists${NC}"
    echo -e "${BLUE}[DRY RUN] Would run:${NC} CREATE EXTENSION IF NOT EXISTS vector;"
    echo -e "${GREEN}✅ pgvector check skipped (dry run)${NC}"
else
    PGVECTOR_EXISTS=$(run_sql "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector');" -t | tr -d ' ')

    if [ "$PGVECTOR_EXISTS" = "t" ]; then
        echo -e "${GREEN}✅ pgvector extension is enabled${NC}"
    else
        echo -e "${YELLOW}⚠ pgvector extension not found. Attempting to enable...${NC}"
        run_sql "CREATE EXTENSION IF NOT EXISTS vector;" || {
            echo -e "${RED}❌ Failed to enable pgvector. Contact Cloud SQL admin.${NC}"
            exit 1
        }
        echo -e "${GREEN}✅ pgvector extension enabled${NC}"
    fi
fi

# Check uuid-ossp extension
echo -e "${YELLOW}Checking uuid-ossp extension...${NC}"
if [ "$DRY_RUN" = true ]; then
    echo -e "${BLUE}[DRY RUN] Would run:${NC} CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"
    echo -e "${GREEN}✅ uuid-ossp check skipped (dry run)${NC}"
else
    run_sql "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";" > /dev/null 2>&1 || true
    echo -e "${GREEN}✅ uuid-ossp extension ready${NC}"
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE} Running Alembic Migrations            ${NC}"
echo -e "${BLUE}========================================${NC}"

# Change to project directory
cd "$SCRIPT_DIR/.."

# Set database URL for Alembic
export DATABASE_URL="postgresql+psycopg://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:5432/${DB_NAME}"

# Activate virtual environment if using conda
if command -v conda &> /dev/null; then
    source ~/.bashrc 2>/dev/null || true
    conda activate venv 2>/dev/null || true
fi

# Run Alembic migrations
echo -e "${YELLOW}Running Alembic migrations...${NC}"

if [ "$DRY_RUN" = true ]; then
    echo -e "${BLUE}[DRY RUN] Would run:${NC} alembic upgrade head"
    echo -e "${BLUE}[DRY RUN] Database URL:${NC} postgresql+psycopg://${DB_USER}:****@${DB_HOST}:5432/${DB_NAME}"
    
    # Show pending migrations
    echo -e "${YELLOW}Checking pending migrations...${NC}"
    if command -v alembic &> /dev/null; then
        echo -e "${BLUE}[DRY RUN] Pending migrations:${NC}"
        alembic history --indicate-current 2>/dev/null | head -20 || echo "  (Could not retrieve migration history)"
    fi
    echo -e "${GREEN}✅ Migration skipped (dry run)${NC}"
else
    if alembic upgrade head; then
        echo -e "${GREEN}✅ All migrations applied successfully!${NC}"
    else
        echo -e "${RED}❌ Migration failed. Check the error above.${NC}"
        exit 1
    fi
fi

# Verify tables created
echo ""
echo -e "${YELLOW}Verifying tables...${NC}"
if [ "$DRY_RUN" = true ]; then
    echo -e "${BLUE}[DRY RUN] Would query:${NC} SELECT tablename FROM pg_tables WHERE schemaname = 'public';"
    echo -e "${GREEN}✅ Table verification skipped (dry run)${NC}"
else
    TABLES=$(psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;")

    echo -e "${GREEN}Tables in database:${NC}"
    echo "$TABLES" | sed 's/^/  /'
fi

echo ""
echo -e "${GREEN}========================================${NC}"
if [ "$DRY_RUN" = true ]; then
    echo -e "${GREEN} Dry Run Complete!                     ${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "This was a dry run. No changes were made."
    echo "Run without --dry-run to apply changes."
else
    echo -e "${GREEN} Setup Complete!                       ${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "Cloud SQL database is ready for use."
    echo "Set USE_CLOUD_DB=true in .env to use Cloud SQL."
fi
