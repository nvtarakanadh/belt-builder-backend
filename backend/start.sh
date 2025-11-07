#!/bin/bash
set -e

echo "🚀 Starting CAD Builder Backend..."
echo "📍 Working directory: $(pwd)"
echo "🔧 Python version: $(python --version)"
echo "🌐 PORT: ${PORT:-8000}"

# Check database connection (non-blocking)
echo "🔍 Checking database connection..."
python wait_for_db.py || echo "⚠️  Database check failed, continuing..."

# Run migrations
echo "📦 Running database migrations..."
python manage.py migrate --noinput || {
    echo "⚠️  Migration failed, but continuing..."
}

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput || {
    echo "⚠️  Collectstatic failed, but continuing..."
}

# Start gunicorn
echo "🎯 Starting Gunicorn server on port ${PORT:-8000}..."
exec gunicorn cadbuilder.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 2 \
    --timeout 120 \
    --keep-alive 5 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    --preload

