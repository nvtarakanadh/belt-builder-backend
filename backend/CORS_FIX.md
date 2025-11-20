# CORS Configuration Fix

## Issue
Frontend deployed on Vercel (`https://belt-builder.vercel.app`) cannot connect to backend on Railway (`https://web-production-80919.up.railway.app/`) due to CORS errors.

## Fixes Applied

### 1. Frontend: Fixed Double Slash in URLs
- Updated `frontend/src/lib/config.ts` to remove trailing slashes from API_BASE
- Prevents URLs like `https://api.com//api/auth/user/` (double slash)

### 2. Backend: Enhanced CORS Configuration
- Added explicit CORS headers configuration
- Added CORS methods configuration
- Improved frontend URL handling (removes trailing slashes)

## Required Environment Variables on Railway

Make sure these environment variables are set in your Railway backend deployment:

1. **FRONTEND_URL** (optional but recommended):
   ```
   FRONTEND_URL=https://belt-builder.vercel.app
   ```

2. **ALLOWED_HOSTS** (required):
   ```
   ALLOWED_HOSTS=web-production-80919.up.railway.app,localhost,127.0.0.1
   ```

3. **DEBUG** (should be False in production):
   ```
   DEBUG=False
   ```

## How to Set Environment Variables in Railway

1. Go to your Railway project dashboard
2. Select your backend service
3. Go to the "Variables" tab
4. Add the following variables:
   - `FRONTEND_URL` = `https://belt-builder.vercel.app`
   - `ALLOWED_HOSTS` = `web-production-80919.up.railway.app,localhost,127.0.0.1`
   - `DEBUG` = `False`

5. Redeploy your service after adding variables

## Testing

After setting the environment variables and redeploying:

1. Check that the backend is accessible: `https://web-production-80919.up.railway.app/api/health/`
2. Try accessing from the frontend - CORS errors should be resolved
3. Check browser console for any remaining CORS errors

## Current CORS Configuration

The backend now allows:
- `https://belt-builder.vercel.app` (your Vercel frontend)
- All localhost ports for development
- Any URL specified in `FRONTEND_URL` environment variable

CORS credentials are enabled to support session-based authentication.

