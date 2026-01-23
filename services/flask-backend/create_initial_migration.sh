#!/bin/bash
# Create initial Alembic migration

set -e

cd "$(dirname "$0")"

echo "Creating initial Alembic migration..."

# Create initial migration
alembic revision --autogenerate -m "Initial schema"

echo "Initial migration created successfully!"
echo "To apply the migration, run: alembic upgrade head"
