#!/usr/bin/env python
"""
Wait for database to be ready before starting the application.
This is useful for Railway deployment where the database might take a moment to start.
"""
import time
import sys
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cadbuilder.settings')

try:
    import django
    django.setup()
    
    from django.db import connection
    from django.db.utils import OperationalError, DatabaseError
except Exception as e:
    print(f"⚠️  Warning: Could not import Django: {e}")
    print("   Continuing anyway - database check will be skipped")
    sys.exit(0)  # Don't fail if Django isn't available yet

def wait_for_db(max_attempts=10, delay=2):
    """Wait for database connection to be available"""
    # Check if DATABASE_URL is set
    if not os.environ.get('DATABASE_URL') and os.environ.get('USE_POSTGRES', 'False') != 'True':
        print("ℹ️  No PostgreSQL configured, using SQLite (skip database check)")
        return True
    
    attempt = 0
    
    while attempt < max_attempts:
        try:
            connection.ensure_connection()
            print("✓ Database connection successful!")
            return True
        except (OperationalError, DatabaseError) as e:
            attempt += 1
            if attempt >= max_attempts:
                print(f"✗ ERROR: Could not connect to database after {max_attempts} attempts")
                print(f"   Last error: {e}")
                print("   Continuing anyway - app may work if database becomes available later")
                return False  # Don't fail startup, let the app try to connect later
            print(f"⏳ Attempt {attempt}/{max_attempts}: Database not ready, waiting {delay} seconds...")
            time.sleep(delay)
        except Exception as e:
            print(f"⚠️  Unexpected error checking database: {e}")
            print("   Continuing anyway")
            return True
    
    return False

if __name__ == '__main__':
    try:
        if not wait_for_db():
            print("⚠️  Database check failed, but continuing startup")
    except Exception as e:
        print(f"⚠️  Error in database check: {e}")
        print("   Continuing startup anyway")
    
    # Always exit successfully so the app can start
    sys.exit(0)

