#!/bin/bash
# Script to initialize database with migrations and seed data

echo "Running database migrations..."
alembic upgrade head

echo "Seeding database with initial data..."
python -m app.core.seed

echo "Database initialization complete!"

