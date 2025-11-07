# Database Setup Guide

This guide explains how to set up the database for the CAD Builder backend.

## Railway Deployment (Recommended)

### Step 1: Add PostgreSQL Database

1. Go to your Railway project dashboard
2. Click **"New"** → **"Database"** → **"Add PostgreSQL"**
3. Railway will automatically:
   - Create a PostgreSQL database
   - Set the `DATABASE_URL` environment variable
   - Link it to your service

### Step 2: Verify Database Connection

The app will automatically:
- Detect the `DATABASE_URL` environment variable
- Use it to connect to the database
- Run migrations on startup (configured in Dockerfile/Procfile)

### Step 3: Check Database Status

After deployment, you can check if migrations ran successfully:
1. Go to your Railway service logs
2. Look for: `Running migrations...` and `Applying <migration_name>...`
3. If you see errors, check the logs for database connection issues

### Step 4: Create Superuser (Optional)

To access Django admin, create a superuser:

**Option A: Using Railway CLI**
```bash
railway run python manage.py createsuperuser
```

**Option B: Using Railway Shell**
1. Go to your service in Railway dashboard
2. Click "Shell" or "Deploy" → "Shell"
3. Run:
```bash
python manage.py createsuperuser
```

## Local Development

### Option 1: Using SQLite (Default)

No setup needed! The app defaults to SQLite for development:
```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Option 2: Using PostgreSQL Locally

1. Install PostgreSQL on your machine
2. Create a database:
```bash
createdb cadbuilder
```

3. Set environment variables:
```bash
export USE_POSTGRES=True
export DB_NAME=cadbuilder
export DB_USER=postgres
export DB_PASSWORD=your_password
export DB_HOST=localhost
export DB_PORT=5432
```

4. Run migrations:
```bash
python manage.py migrate
```

## Environment Variables

### For Railway (Automatic)
- `DATABASE_URL` - Automatically set by Railway when you add PostgreSQL

### For Manual PostgreSQL Setup
- `USE_POSTGRES=True` - Enable PostgreSQL
- `DB_NAME` - Database name (default: `cadbuilder`)
- `DB_USER` - Database user (default: `postgres`)
- `DB_PASSWORD` - Database password
- `DB_HOST` - Database host (default: `localhost`)
- `DB_PORT` - Database port (default: `5432`)

## Troubleshooting

### Database Connection Errors

**Error: "could not connect to server"**
- Check if PostgreSQL is running
- Verify database credentials
- Check firewall/network settings

**Error: "relation does not exist"**
- Run migrations: `python manage.py migrate`
- Check if migrations ran successfully

**Error: "database does not exist"**
- Create the database: `createdb cadbuilder`
- Or let Railway create it automatically

### Migration Issues

**Migrations not running:**
- Check Dockerfile CMD/Procfile includes: `python manage.py migrate`
- Check Railway logs for migration errors

**Migration conflicts:**
```bash
# Reset migrations (WARNING: Deletes data!)
python manage.py migrate --fake-initial
```

### Railway-Specific Issues

**DATABASE_URL not set:**
- Make sure you added PostgreSQL service
- Check that services are linked in Railway
- Restart your service after adding database

**Connection timeout:**
- Railway databases sometimes take a few seconds to start
- The app includes retry logic in startup scripts
- Check Railway database service status

## Database Models

The app uses these main models:
- `components.Component` - CAD components
- `components.ComponentCategory` - Component categories
- `projects.Project` - User projects
- `projects.AssemblyItem` - Assembly components

## Backup and Restore

### Railway Backup
Railway automatically backs up PostgreSQL databases. Check your Railway dashboard for backup options.

### Manual Backup
```bash
# Export data
python manage.py dumpdata > backup.json

# Import data
python manage.py loaddata backup.json
```

