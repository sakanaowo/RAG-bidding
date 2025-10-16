#!/bin/bash

# This script sets up a PostgreSQL database with the pgvector extension.
# Please make sure you have sudo privileges to run this script.

# --- Configuration ---
# Replace with your desired database name, user, and password.
DB_NAME="ragdb"
DB_USER="superuser"
DB_PASSWORD="rag-bidding"
PG_VERSION="17" # Make sure this version is available for your system

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
sudo -u postgres psql -d $DB_NAME -c "CREATE EXTENSION vector;"

# --- Verification ---

# You can verify the setup by connecting to the database:
# psql -U your_db_user -d your_db_name
# And then running the following command inside psql:
# \dx
# You should see "vector" in the list of installed extensions.

echo "Database setup complete."
echo "Database: $DB_NAME"
echo "User: $DB_USER"
echo "Password: $DB_PASSWORD"

# dump DB
# pg_dump -h localhost -U rag -d ragdb -Fc -f ragdb_dump.pg

# restore DB
# Chuyển file ragdb_dump.pg sang server công ty (scp ragdb_dump.pg user@server:/tmp/)
# pg_restore -h localhost -U rag -d ragdb --clean --create /tmp/ragdb_dump.pg

# setup for backend
# export DATABASE_URL="postgresql+psycopg2://superuser:rag-bidding@localhost:5432/ragdb"
# export PGVECTOR_EXTENSION=True
# export VECTOR_DIMENSION=1536 # embedding dimension of model:text-embedding-3-large
