#!/bin/bash
# Database initialization script for Railway deployment

set -e

echo "Starting database initialization..."

# Wait for database to be ready (Railway handles this, but good to have)
echo "Waiting for database connection..."
python << END
import time
import os
import sys
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cadbuilder.settings')
django.setup()

from django.db import connection
from django.db.utils import OperationalError

max_attempts = 30
attempt = 0

while attempt < max_attempts:
    try:
        connection.ensure_connection()
        print("Database connection successful!")
        break
    except OperationalError:
        attempt += 1
        if attempt >= max_attempts:
            print("ERROR: Could not connect to database after 30 attempts")
            sys.exit(1)
        print(f"Attempt {attempt}/{max_attempts}: Database not ready, waiting 2 seconds...")
        time.sleep(2)
END

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput || true

echo "Database initialization complete!"

