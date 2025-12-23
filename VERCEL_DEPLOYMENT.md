# Vercel Deployment Guide

## Prerequisites

1. **Vercel Account**: Sign up at https://vercel.com
2. **Vercel CLI**: Install globally
   ```bash
   npm install -g vercel
   ```

3. **Environment Variables**: Have your API keys ready
   - `OPENAI_API_KEY`
   - `CASINO_API_URL`

## Deployment Steps

### Step 1: Login to Vercel

```bash
vercel login
```

### Step 2: Set Environment Variables

In your Vercel project dashboard (or via CLI):

```bash
# Add OpenAI API key
vercel env add OPENAI_API_KEY

# Add Casino API URL
vercel env add CASINO_API_URL

# Add Log Level (optional)
vercel env add LOG_LEVEL
```

When prompted:
- Select: **Production, Preview, and Development**
- Paste your API key/URL

### Step 3: Deploy

From the project root directory:

```bash
# First deployment
vercel

# Follow the prompts:
# - Set up and deploy? Yes
# - Which scope? (your account)
# - Link to existing project? No
# - Project name? ai-workflow-api
# - Directory? ./
# - Override settings? No

# Production deployment
vercel --prod
```

### Step 4: Verify Deployment

Your API will be available at:
```
https://ai-workflow-api-[your-username].vercel.app
```

Test the endpoints:

```bash
# Health check
curl https://your-deployment-url.vercel.app/health

# Get schema
curl https://your-deployment-url.vercel.app/schema

# Execute query
curl -X POST https://your-deployment-url.vercel.app/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Show me the first 5 employees"}'
```

## API Endpoints

### 1. Health Check
```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "tables_cached": 7
}
```

### 2. Get Schema
```
GET /schema
```

Returns list of all tables with columns and descriptions.

### 3. Execute Query
```
POST /query
```

Request body:
```json
{
  "query": "Which employees generated the highest revenue per shift?",
  "conversation_history": []
}
```

Response:
```json
{
  "response": "Query returned 3 employees...",
  "sql": "SELECT e.employee_id, ...",
  "results": [...],
  "execution_time": 2.5,
  "path_taken": "result_summarizer",
  "error": null
}
```

### 4. Get Examples
```
GET /examples
```

Returns example queries users can try.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key for GPT-4 |
| `CASINO_API_URL` | Yes | Casino database API endpoint |
| `LOG_LEVEL` | No | Logging level (default: INFO) |
| `MAIN_MODEL` | No | OpenAI model (default: gpt-4o) |
| `QUERY_TIMEOUT` | No | Query timeout in seconds (default: 5) |

## Troubleshooting

### Issue: Import Errors

**Problem**: Module not found errors during build

**Solution**: Make sure all dependencies are in `api/requirements.txt`

### Issue: Environment Variables Not Working

**Problem**: API keys not recognized

**Solution**: 
1. Check environment variables in Vercel dashboard
2. Redeploy after adding variables
3. Make sure they're set for all environments

### Issue: Timeout Errors

**Problem**: Function execution timeout

**Solution**:
1. Vercel free tier has 10s timeout for serverless functions
2. Upgrade to Pro for 60s timeout
3. Or optimize queries to run faster

### Issue: Cold Start

**Problem**: First request takes long time

**Solution**: This is normal for serverless functions. Consider:
1. Using Vercel Edge Functions for faster cold starts
2. Implementing a warm-up ping
3. Using Vercel Pro for better performance

## Local Testing

Test the API locally before deploying:

```bash
# Install dependencies
cd api
pip install -r requirements.txt

# Run locally with uvicorn
cd ..
uvicorn api.index:app --reload --port 8000

# Test
curl http://localhost:8000/health
```

## Updating Deployment

To update your deployment:

```bash
# Make your changes
git add .
git commit -m "Update API"

# Deploy
vercel --prod
```

## Monitoring

1. **View Logs**: Vercel Dashboard → Your Project → Logs
2. **Check Performance**: Vercel Dashboard → Analytics
3. **Monitor Errors**: Vercel Dashboard → Error Tracking

## Cost Considerations

**Vercel Free Tier includes:**
- 100GB bandwidth
- 100GB-hrs serverless function execution
- 10s function timeout

**Upgrade to Pro ($20/month) for:**
- 1TB bandwidth
- 1000GB-hrs execution
- 60s function timeout
- Better performance

## Security Best Practices

1. **Never commit** `.env` file
2. **Always use** environment variables for secrets
3. **Enable CORS** only for trusted domains in production
4. **Rate limit** API endpoints if needed
5. **Monitor usage** to detect anomalies

## Next Steps

1. ✅ Deploy to Vercel
2. ✅ Test all endpoints
3. ✅ Set up custom domain (optional)
4. ✅ Enable Vercel Analytics
5. ✅ Set up monitoring/alerts
6. ✅ Create frontend to consume API

