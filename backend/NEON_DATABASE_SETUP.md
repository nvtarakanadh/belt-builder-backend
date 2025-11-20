# Neon PostgreSQL Database Setup

This guide explains how to connect your Django backend to Neon PostgreSQL database.

## Database Connection String

Your Neon database connection string:
```
postgresql://neondb_owner:npg_tf6QEDv4NnSz@ep-lucky-glitter-a4hwevbe-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require
```

## Setup Methods

### Method 1: Using .env file (Recommended)

1. Create a `.env` file in the `backend` directory:
```bash
# backend/.env
DATABASE_URL=postgresql://neondb_owner:npg_tf6QEDv4NnSz@ep-lucky-glitter-a4hwevbe-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require
```

2. The app will automatically load the `.env` file using `python-dotenv`

### Method 2: Using Environment Variable (PowerShell)

For the current session:
```powershell
$env:DATABASE_URL="postgresql://neondb_owner:npg_tf6QEDv4NnSz@ep-lucky-glitter-a4hwevbe-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"
```

To make it permanent (Windows):
1. Open System Properties → Environment Variables
2. Add new System Variable:
   - Name: `DATABASE_URL`
   - Value: `postgresql://neondb_owner:npg_tf6QEDv4NnSz@ep-lucky-glitter-a4hwevbe-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require`

### Method 3: Using the Setup Script

Run the PowerShell script:
```powershell
.\setup_neon_db.ps1
```

## Running Migrations

After setting the DATABASE_URL, run migrations:

```bash
python manage.py migrate
```

Migrations have already been run successfully! Your database is ready to use.

## Verifying Connection

Test the database connection:

```bash
python manage.py dbshell
```

Or check if tables exist:
```bash
python manage.py dbshell -c "\dt"
```

## Creating a Superuser

To access Django admin:

```bash
python manage.py createsuperuser
```

## Database Status

✅ **Database Connected**: Neon PostgreSQL  
✅ **Migrations Applied**: All migrations have been run  
✅ **Tables Created**: All required tables are in place

## Notes

- The database uses SSL (sslmode=require) for secure connections
- Connection pooling is enabled via the pooler endpoint
- The database is hosted on AWS us-east-1 region
- All data is now stored in Neon PostgreSQL instead of SQLite

## Troubleshooting

### Connection Errors

If you see connection errors:
1. Verify the DATABASE_URL is set correctly
2. Check your internet connection
3. Ensure Neon database is active (check Neon dashboard)
4. Verify SSL is enabled (sslmode=require)

### Migration Errors

If migrations fail:
```bash
# Check migration status
python manage.py showmigrations

# Run specific migration
python manage.py migrate <app_name> <migration_number>
```

### Environment Variable Not Loading

If .env file is not loading:
1. Ensure `python-dotenv` is installed: `pip install python-dotenv`
2. Check that .env file is in the `backend` directory
3. Verify .env file format (no spaces around =)

