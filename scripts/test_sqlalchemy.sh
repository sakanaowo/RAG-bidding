#!/bin/bash
# Quick test script for SQLAlchemy setup

echo "=== Testing SQLAlchemy Setup ==="
echo ""

# Activate conda environment
echo "1. Activating conda environment..."
source ~/miniconda3/etc/profile.d/conda.sh
conda activate venv

# Check Python packages
echo ""
echo "2. Checking installed packages..."
python -c "
try:
    import sqlalchemy
    print(f'✅ SQLAlchemy {sqlalchemy.__version__}')
except ImportError:
    print('❌ SQLAlchemy not installed')
    print('   Install with: pip install sqlalchemy')

try:
    import psycopg
    print(f'✅ psycopg {psycopg.__version__}')
except ImportError:
    print('❌ psycopg not installed')
    print('   Install with: pip install psycopg[binary]')

try:
    import pgvector
    # pgvector doesn't expose __version__, just check import
    print(f'✅ pgvector installed')
except ImportError:
    print('❌ pgvector not installed')
    print('   Install with: pip install pgvector')

try:
    import alembic
    print(f'✅ Alembic {alembic.__version__}')
except ImportError:
    print('❌ Alembic not installed')
    print('   Install with: pip install alembic')
"

# Test database connection
echo ""
echo "3. Testing database connection..."
python -c "
import sys
sys.path.insert(0, '.')

try:
    from sqlalchemy import text
    from src.models.base import engine, SessionLocal
    with SessionLocal() as db:
        result = db.execute(text('SELECT 1')).scalar()
        if result == 1:
            print('✅ Database connection successful')
        else:
            print('❌ Unexpected result from database')
except Exception as e:
    print(f'❌ Database connection failed: {e}')
"

# Verify schema
echo ""
echo "4. Verifying database schema..."
python -c "
import sys
sys.path.insert(0, '.')

try:
    from src.models.db_utils import verify_schema
    verify_schema()
except Exception as e:
    print(f'❌ Schema verification failed: {e}')
"

# Get database stats
echo ""
echo "5. Getting database statistics..."
python -c "
import sys
sys.path.insert(0, '.')

try:
    from src.models.db_utils import get_database_stats
    import json
    stats = get_database_stats()
    print(json.dumps(stats, indent=2, default=str))
except Exception as e:
    print(f'❌ Failed to get stats: {e}')
"

echo ""
echo "=== Test Complete ==="
