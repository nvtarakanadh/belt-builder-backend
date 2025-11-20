# Deployment Guide

This guide explains how to deploy the Conveyor Belt Builder application.

## Prerequisites

- Python 3.10+ (backend)
- Node.js 18+ (frontend)
- PostgreSQL database (Neon, Railway, or self-hosted)
- Git

## Environment Setup

### Backend Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in your values:

```bash
cp backend/.env.example backend/.env
```

Required variables:
- `SECRET_KEY` - Django secret key (generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`)
- `DATABASE_URL` - PostgreSQL connection string (from Neon, Railway, etc.)
- `ALLOWED_HOSTS` - Comma-separated list of allowed hosts
- `FRONTEND_URL` - Frontend URL for CORS

Optional variables:
- `CLOUDCONVERT_API_KEY` - For STEP file conversion
- `FREECAD_DOCKER_URL` - For FreeCAD-based STEP conversion
- `USE_S3` - Set to `True` to use AWS S3 for file storage
- `CELERY_BROKER_URL` - Redis URL for Celery tasks

### Frontend Environment Variables

Create `frontend/.env`:

```env
VITE_API_BASE=http://localhost:8000
```

For production:
```env
VITE_API_BASE=https://your-api-domain.com
```

## Database Setup

### Using Neon PostgreSQL

1. Create a Neon database at https://neon.tech
2. Copy the connection string
3. Set `DATABASE_URL` in your `.env` file
4. Run migrations:

```bash
cd backend
python manage.py migrate
python manage.py createsuperuser
```

See `backend/NEON_DATABASE_SETUP.md` for detailed instructions.

## Local Development

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Production Deployment

### Railway Deployment (Recommended)

1. **Install Railway CLI:**
   ```bash
   npm i -g @railway/cli
   railway login
   ```

2. **Initialize Railway project:**
   ```bash
   railway init
   ```

3. **Add PostgreSQL database:**
   - In Railway dashboard: New → Database → Add PostgreSQL
   - Railway automatically sets `DATABASE_URL`

4. **Set environment variables:**
   ```bash
   railway variables set SECRET_KEY=your-secret-key
   railway variables set ALLOWED_HOSTS=your-domain.com
   railway variables set FRONTEND_URL=https://your-frontend.com
   ```

5. **Deploy:**
   ```bash
   railway up
   ```

See `backend/README_RAILWAY.md` for detailed Railway deployment instructions.

### Docker Deployment

1. **Build and run:**
   ```bash
   docker-compose up -d
   ```

2. **Run migrations:**
   ```bash
   docker-compose exec web python manage.py migrate
   docker-compose exec web python manage.py createsuperuser
   ```

### Manual Server Deployment

1. **Install dependencies:**
   ```bash
   # Backend
   cd backend
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   pip install gunicorn

   # Frontend
   cd frontend
   npm install
   npm run build
   ```

2. **Configure web server (Nginx example):**
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }

       location /static/ {
           alias /path/to/backend/staticfiles/;
       }

       location /media/ {
           alias /path/to/backend/media/;
       }
   }
   ```

3. **Run with Gunicorn:**
   ```bash
   cd backend
   gunicorn cadbuilder.wsgi:application --bind 0.0.0.0:8000 --workers 4
   ```

## Frontend Deployment

### Vercel (Recommended)

1. **Install Vercel CLI:**
   ```bash
   npm i -g vercel
   ```

2. **Deploy:**
   ```bash
   cd frontend
   vercel
   ```

3. **Set environment variables in Vercel dashboard:**
   - `VITE_API_BASE` - Your backend API URL

### Netlify

1. **Build command:** `npm run build`
2. **Publish directory:** `dist`
3. **Environment variables:**
   - `VITE_API_BASE` - Your backend API URL

## Security Checklist

- [ ] Change `SECRET_KEY` to a secure random value
- [ ] Set `DEBUG=False` in production
- [ ] Configure `ALLOWED_HOSTS` with your domain
- [ ] Use HTTPS in production
- [ ] Set secure database credentials
- [ ] Configure CORS properly
- [ ] Use environment variables for all secrets
- [ ] Enable database SSL (sslmode=require)
- [ ] Set up proper file permissions
- [ ] Configure backup strategy

## Monitoring

### Health Check Endpoint

The API provides a health check at `/api/health/` (if implemented).

### Logs

- Railway: Check logs in Railway dashboard
- Docker: `docker-compose logs -f`
- Manual: Check application logs and web server logs

## Troubleshooting

### Database Connection Issues

- Verify `DATABASE_URL` is correct
- Check database is accessible from your deployment
- Ensure SSL is enabled (sslmode=require for Neon)
- Check firewall rules

### CORS Issues

- Verify `FRONTEND_URL` matches your frontend domain
- Check `CORS_ALLOWED_ORIGINS` in settings
- Ensure credentials are allowed if using cookies

### Static Files Not Loading

- Run `python manage.py collectstatic`
- Check `STATIC_ROOT` and `STATIC_URL` settings
- Verify web server configuration

See `backend/RAILWAY_TROUBLESHOOTING.md` for Railway-specific issues.

## Backup

### Database Backup

```bash
# Export data
python manage.py dumpdata > backup.json

# Import data
python manage.py loaddata backup.json
```

### Media Files Backup

Backup the `media/` directory regularly, or use S3 for automatic backups.

## Updates

1. Pull latest changes: `git pull`
2. Install/update dependencies
3. Run migrations: `python manage.py migrate`
4. Collect static files: `python manage.py collectstatic`
5. Restart application

