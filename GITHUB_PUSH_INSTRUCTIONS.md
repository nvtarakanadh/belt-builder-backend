# GitHub Push Instructions

## Current Status

✅ **Changes committed locally**
- Neon PostgreSQL database support added
- Hardcoded secrets removed
- Deployment documentation added
- Environment variable templates created

## Push to GitHub

### If you already have a remote repository:

```bash
# Check current remote
git remote -v

# Push to GitHub
git push origin main
```

### If you need to create a new repository:

1. **Create a new repository on GitHub:**
   - Go to https://github.com/new
   - Name it (e.g., "conveyor-belt-builder")
   - Don't initialize with README, .gitignore, or license (we already have these)

2. **Add the remote and push:**
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
   git branch -M main
   git push -u origin main
   ```

### If you need to update the remote URL:

```bash
# Update remote URL
git remote set-url origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# Push
git push -u origin main
```

## Important Notes

### Before Pushing:

1. **Verify sensitive files are excluded:**
   - ✅ `.env` files are in `.gitignore`
   - ✅ `db.sqlite3` is in `.gitignore`
   - ✅ `venv/` and `node_modules/` are in `.gitignore`
   - ✅ Media files are in `.gitignore`

2. **Check for any remaining secrets:**
   ```bash
   # Search for potential secrets
   git grep -i "password\|secret\|api_key\|token" -- "*.py" "*.ts" "*.tsx" "*.js"
   ```

3. **Review what will be pushed:**
   ```bash
   git log --oneline -5
   git diff origin/main..HEAD --stat
   ```

### After Pushing:

1. **Set up GitHub Secrets** (for CI/CD):
   - Go to repository Settings → Secrets and variables → Actions
   - Add secrets:
     - `DATABASE_URL`
     - `SECRET_KEY`
     - `CLOUDCONVERT_API_KEY` (if using)

2. **Update repository description:**
   - Add description: "3D CAD-based engineering builder platform for conveyor belt systems"

3. **Add topics/tags:**
   - django
   - react
   - threejs
   - cad
   - conveyor-belt
   - 3d-modeling

## Security Checklist

Before pushing, ensure:
- [ ] No `.env` files are committed
- [ ] No hardcoded API keys or secrets
- [ ] No database credentials in code
- [ ] `.gitignore` is properly configured
- [ ] All sensitive data uses environment variables

## Next Steps After Push

1. **Set up environment variables** in your deployment platform:
   - Railway: Use Railway dashboard
   - Vercel: Use Vercel dashboard
   - Other: Follow platform-specific instructions

2. **Deploy:**
   - See `DEPLOYMENT.md` for detailed instructions
   - Backend: Deploy to Railway or your preferred platform
   - Frontend: Deploy to Vercel or Netlify

3. **Configure database:**
   - Ensure Neon database is accessible from deployment
   - Run migrations on first deploy

## Troubleshooting

### Authentication Issues

If you get authentication errors:
```bash
# Use GitHub CLI
gh auth login

# Or use SSH instead of HTTPS
git remote set-url origin git@github.com:YOUR_USERNAME/YOUR_REPO_NAME.git
```

### Large Files

If you have large files:
```bash
# Check file sizes
git ls-files | xargs ls -lh | sort -k5 -hr | head -20

# Use Git LFS for large files if needed
git lfs install
git lfs track "*.glb"
git lfs track "*.stl"
```

### Submodule Issues

If frontend is a submodule:
```bash
# Update submodule
git submodule update --init --recursive

# Push submodule changes separately
cd frontend
git push origin main
cd ..
```

