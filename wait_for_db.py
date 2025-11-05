#!/usr/bin/env python
"""
Wait for database to be ready before starting the application.
This is useful for Railway deployment where the database might take a moment to start.
"""
import time
import sys
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cadbuilder.settings')

import django
django.setup()

from django.db import connection
from django.db.utils import OperationalError

def wait_for_db(max_attempts=30, delay=2):
    """Wait for database connection to be available"""
    attempt = 0
    
    while attempt < max_attempts:
        try:
            connection.ensure_connection()
            print("✓ Database connection successful!")
            return True
        except OperationalError as e:
            attempt += 1
            if attempt >= max_attempts:
                print(f"✗ ERROR: Could not connect to database after {max_attempts} attempts")
                print(f"   Last error: {e}")
                return False
            print(f"⏳ Attempt {attempt}/{max_attempts}: Database not ready, waiting {delay} seconds...")
            time.sleep(delay)
    
    return False

if __name__ == '__main__':
    if not wait_for_db():
        sys.exit(1)

