# Vercel Deployment Checklist

## Pre-Deployment

- [ ] Install Vercel CLI: `npm install -g vercel`
- [ ] Have OpenAI API key ready
- [ ] Have Casino API URL ready
- [ ] Test locally first: `uvicorn api.index:app --reload`
- [ ] Verify all dependencies in `api/requirements.txt`
- [ ] Check `.gitignore` and `.vercelignore` files
- [ ] Commit all changes to git

## Deployment Steps

### 1. Login to Vercel
```bash
vercel login
```

### 2. Deploy to Preview
```bash
cd /Users/abderrahmenbejaoui/Desktop/ai-workflow
vercel
```

Follow prompts:
- Set up and deploy? **Yes**
- Which scope? **(your account)**
- Link to existing project? **No**
- Project name? **ai-workflow-api**
- Directory? **./ai-workflow**
- Override settings? **No**

### 3. Set Environment Variables

In Vercel Dashboard or via CLI:

```bash
# OpenAI API Key
vercel env add OPENAI_API_KEY
# Paste your key, select all environments

# Casino API URL  
vercel env add CASINO_API_URL
# Paste: http://44.251.222.149:8000/api/sql/execute-query
# Select all environments

# Optional: Log Level
vercel env add LOG_LEVEL
# Enter: INFO
# Select all environments
```

### 4. Deploy to Production
```bash
vercel --prod
```

### 5. Test Deployment

```bash
# Replace YOUR_URL with your actual Vercel URL
export API_URL="https://your-project.vercel.app"

# Test health
curl $API_URL/health

# Test schema
curl $API_URL/schema

# Test query
curl -X POST $API_URL/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Show me 5 employees"}'
```

## Post-Deployment

- [ ] Verify all endpoints work
- [ ] Test with example queries
- [ ] Check logs in Vercel Dashboard
- [ ] Set up custom domain (optional)
- [ ] Enable Vercel Analytics
- [ ] Set up monitoring/alerts
- [ ] Document API URL for frontend team

## Troubleshooting

### Build Fails

**Check:**
- All imports are correct
- Dependencies are in `api/requirements.txt`
- No circular imports
- Python version compatibility

**Fix:**
```bash
# Test locally first
cd api
pip install -r requirements.txt
cd ..
python -c "from api.index import app; print('OK')"
```

### Environment Variables Not Working

**Check:**
- Variables are set in Vercel Dashboard
- Variables are set for all environments (Production, Preview, Development)
- Variable names match exactly (case-sensitive)

**Fix:**
```bash
# List current variables
vercel env ls

# Remove and re-add if needed
vercel env rm OPENAI_API_KEY
vercel env add OPENAI_API_KEY
```

### Function Timeout

**Issue:** Serverless function times out (10s limit on free tier)

**Solutions:**
1. Upgrade to Vercel Pro ($20/month) for 60s timeout
2. Optimize query generation
3. Cache schema in memory
4. Use edge functions for faster performance

### Import Errors

**Issue:** Module not found

**Fix:**
- Ensure all files are in correct locations
- Check `sys.path.insert` in `api/index.py`
- Verify `__init__.py` files exist in all packages

## Production Checklist

- [ ] All tests passing
- [ ] Environment variables set
- [ ] API endpoints documented
- [ ] Error handling tested
- [ ] Logging configured
- [ ] CORS configured properly
- [ ] Rate limiting considered
- [ ] Monitoring set up
- [ ] Backup plan for downtime
- [ ] Team notified of API URL

## Monitoring

### Vercel Dashboard
- **Logs**: View function execution logs
- **Analytics**: Track API usage and performance
- **Errors**: Monitor and debug errors

### Set Up Alerts
1. Go to Vercel Dashboard → Your Project → Settings
2. Enable email notifications for:
   - Deployment failures
   - High error rates
   - Performance issues

## Updating

To update your deployment:

```bash
# Make changes
git add .
git commit -m "Update: description of changes"

# Deploy to preview first
vercel

# Test preview deployment
# If everything works, deploy to production
vercel --prod
```

## Rollback

If something goes wrong:

```bash
# List deployments
vercel ls

# Rollback to previous deployment
vercel rollback [deployment-url]
```

## Custom Domain (Optional)

1. Go to Vercel Dashboard → Your Project → Settings → Domains
2. Add your custom domain
3. Update DNS records as instructed
4. Wait for SSL certificate

## Support

- Vercel Documentation: https://vercel.com/docs
- Vercel Support: https://vercel.com/support
- GitHub Issues: (your repo)/issues

