# Railway Deployment Troubleshooting Guide

## Application Failed to Respond

If you see "Application failed to respond" on Railway, check the following:

### 1. Check Railway Deploy Logs

1. Go to your Railway project dashboard
2. Click on your service
3. Click on the "Deployments" tab
4. Click on the latest deployment
5. Check the logs for errors

### 2. Required Environment Variables

Make sure these are set in Railway:

**Required:**
- `SECRET_KEY` - Django secret key (generate a secure random string)
- `DEBUG` - Set to `False` for production
- `ALLOWED_HOSTS` - Your Railway domain (e.g., `web-production-80919.up.railway.app`)

**Database (Automatic if PostgreSQL added):**
- `DATABASE_URL` - Automatically set when you add PostgreSQL

**Optional but recommended:**
- `FRONTEND_URL` - Your frontend URL (e.g., `https://belt-builder.vercel.app`)

### 3. Common Issues

#### Issue: Database Connection Failed
**Symptoms:** Logs show "Could not connect to database"
**Solution:**
- Make sure you've added a PostgreSQL database in Railway
- Check that services are linked
- Verify `DATABASE_URL` is set in environment variables

#### Issue: Missing SECRET_KEY
**Symptoms:** Logs show Django errors about SECRET_KEY
**Solution:**
- Generate a secret key: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
- Add it to Railway environment variables

#### Issue: ALLOWED_HOSTS not set
**Symptoms:** 400 Bad Request errors
**Solution:**
- Add your Railway domain to `ALLOWED_HOSTS` environment variable
- Format: `web-production-80919.up.railway.app` (no http://)

#### Issue: Port not binding
**Symptoms:** Connection refused errors
**Solution:**
- Railway automatically sets `PORT` environment variable
- Make sure your CMD uses `${PORT}` or `$PORT`
- The app should bind to `0.0.0.0:$PORT`

#### Issue: Migrations failing
**Symptoms:** Logs show migration errors
**Solution:**
- Check database connection
- Verify database permissions
- Try running migrations manually via Railway shell

### 4. Testing the Deployment

Once deployed, test these URLs:

- **Health Check:** `https://your-app.railway.app/health/`
- **API Root:** `https://your-app.railway.app/`
- **API Docs:** `https://your-app.railway.app/api/docs/`
- **Admin:** `https://your-app.railway.app/admin/` (requires superuser)

### 5. Manual Database Setup

If you need to create a superuser:

1. Go to Railway project dashboard
2. Click on your service
3. Click "Shell" or use Railway CLI: `railway shell`
4. Run: `python manage.py createsuperuser`

### 6. Viewing Logs

**Via Railway Dashboard:**
1. Go to your service
2. Click "Deployments" tab
3. Click on latest deployment
4. View logs

**Via Railway CLI:**
```bash
railway logs
```

### 7. Quick Fixes

**Restart the service:**
- Go to Railway dashboard → Service → Settings → Restart

**Redeploy:**
- Push a new commit to trigger redeploy
- Or manually trigger redeploy in Railway dashboard

**Check service status:**
- Railway dashboard shows service status
- Green = running
- Red = error

### 8. Getting Help

If issues persist:
1. Check Railway documentation: https://docs.railway.app
2. Check Railway status: https://status.railway.app
3. Contact Railway support via their Help Station

