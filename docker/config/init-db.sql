-- Initialize database with required extensions
CREATE EXTENSION IF NOT EXISTS vector;

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE ragdb TO superuser;
GRANT ALL PRIVILEGES ON SCHEMA public TO superuser;

-- Verify extension installation
SELECT * FROM pg_extension WHERE extname = 'vector';