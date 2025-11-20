# Setup script for Neon PostgreSQL Database
# Run this script to set the DATABASE_URL environment variable

$env:DATABASE_URL = "postgresql://neondb_owner:npg_tf6QEDv4NnSz@ep-lucky-glitter-a4hwevbe-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"

Write-Host "DATABASE_URL environment variable set for this session."
Write-Host "To make it permanent, add it to your system environment variables or use a .env file."
Write-Host ""
Write-Host "Running migrations..."

python manage.py migrate

Write-Host ""
Write-Host "Database setup complete!"

