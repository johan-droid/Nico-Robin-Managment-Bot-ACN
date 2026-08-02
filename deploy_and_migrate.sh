#!/bin/bash
set -e

echo "Committing recent database fixes..."
git add backend/src/handlers/mod.rs backend/src/db/*.rs
git commit -m "Fix database foreign key constraints and update UPSERT logic" || true

echo "Pushing to remote..."
git push

echo "Migration script for cloud database."
if [ -z "$DATABASE_URL" ]; then
    echo "Error: DATABASE_URL environment variable is not set."
    echo "Please set it before running this script."
    echo "Example: export DATABASE_URL='postgresql://user:pass@host:port/dbname'"
    exit 1
fi

echo "Running migrations against the cloud database..."

# Go to backend migrations directory
cd backend/migrations

# Apply all migrations in order
for file in $(ls *.sql | sort -n); do
    echo "Applying $file..."
    psql "$DATABASE_URL" -f "$file"
done

echo "Cloud migration complete!"
