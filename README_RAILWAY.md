# Railway Deployment Guide

This backend is configured for deployment on Railway.

## Environment Variables

Set the following environment variables in your Railway project:

### Required
- `SECRET_KEY`: Django secret key (generate a secure random string)
- `DEBUG`: Set to `False` for production
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts (e.g., `your-app.railway.app,api.yourdomain.com`)
- `FRONTEND_URL`: Your frontend URL (e.g., `https://belt-builder.vercel.app`)

### Database (Automatic)
Railway automatically provides a `DATABASE_URL` environment variable when you add a PostgreSQL service. The app will automatically use it.

### Optional
- `USE_S3`: Set to `True` if using AWS S3 for media storage
- `AWS_ACCESS_KEY_ID`: AWS access key (if using S3)
- `AWS_SECRET_ACCESS_KEY`: AWS secret key (if using S3)
- `AWS_STORAGE_BUCKET_NAME`: S3 bucket name (if using S3)
- `AWS_S3_REGION_NAME`: S3 region (default: `us-east-1`)

## Deployment Steps

1. **Create a new Railway project**
   - Go to Railway and create a new project
   - Connect your GitHub repository: `nvtarakanadh/belt-builder-backend`

2. **Add PostgreSQL Database**
   - Click "New" → "Database" → "Add PostgreSQL"
   - Railway will automatically provide the `DATABASE_URL` environment variable

3. **Configure Environment Variables**
   - Go to your service settings
   - Add the required environment variables listed above

4. **Deploy**
   - Railway will automatically detect the Dockerfile and deploy
   - The app will run migrations on startup
   - Static files will be collected automatically

## Port Configuration

Railway automatically sets the `PORT` environment variable. The Dockerfile and Procfile are configured to use this port.

## Health Checks

Railway will automatically check if your service is healthy by checking if the port is listening.

## Custom Domain

If you add a custom domain in Railway:
1. Add the domain to `ALLOWED_HOSTS` environment variable
2. Update `FRONTEND_URL` in your frontend app to point to the new domain

