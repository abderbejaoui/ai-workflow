# How People Can Test Your API

Once you deploy to Vercel, anyone can test your API in **3 easy ways**:

## 🌐 Method 1: Web Interface (Easiest)

Your deployed API will have a beautiful web interface where users can test queries visually.

**URL:** `https://your-app-name.vercel.app/`

### Features:
- ✅ **No coding required** - just type and click
- ✅ **Pre-built example queries** - one-click testing
- ✅ **Visual results** - formatted, easy to read
- ✅ **Real-time SQL generation** - see the generated SQL
- ✅ **Performance metrics** - execution time, row count

### How to use:
1. Open the URL in any browser
2. Click an example query OR type your own
3. Click "Execute"
4. See results instantly!

---

## 📚 Method 2: Interactive API Documentation (For Developers)

Vercel automatically provides Swagger UI documentation.

**URL:** `https://your-app-name.vercel.app/docs`

### Features:
- ✅ **Try it out** button on every endpoint
- ✅ **Request/response examples**
- ✅ **Auto-generated** from your code
- ✅ **No setup needed**

### How to use:
1. Open `/docs` URL
2. Click on any endpoint (e.g., POST /query)
3. Click "Try it out"
4. Enter your query in the request body
5. Click "Execute"
6. See the response

---

## 💻 Method 3: Direct API Calls (For Programmers)

### Using cURL (Command Line)

```bash
# Health check
curl https://your-app-name.vercel.app/health

# Get database schema
curl https://your-app-name.vercel.app/schema

# Execute a query
curl -X POST https://your-app-name.vercel.app/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Show me 5 employees"
  }'
```

### Using JavaScript/Fetch

```javascript
async function queryAPI(question) {
  const response = await fetch('https://your-app-name.vercel.app/query', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query: question
    })
  });
  
  const data = await response.json();
  console.log('Response:', data.response);
  console.log('SQL:', data.sql);
  console.log('Results:', data.results);
}

// Test it
queryAPI("How many customers are there?");
```

### Using Python/Requests

```python
import requests

url = "https://your-app-name.vercel.app/query"

response = requests.post(url, json={
    "query": "Show me 5 employees"
})

data = response.json()
print("Answer:", data['response'])
print("SQL:", data['sql'])
print("Results:", data['results'])
```

---

## 📋 Example Queries to Try

### Easy Queries:
- "Show me 5 employees"
- "How many customers are there?"
- "List all departments"

### Medium Queries:
- "What is the average transaction amount?"
- "How many customers are in each region?"
- "Which employees have the highest salaries?"

### Hard Queries:
- "Which employees generated the highest revenue per shift?"
- "Show high-risk customers with gambling problems"
- "Total revenue by department for the last month"

---

## 🎯 What Users Will See

### Example Response:

**Input:** "Show me 3 employees"

**Output:**
```json
{
  "response": "Here are the details for the 3 employees...",
  "sql": "SELECT employee_id, first_name, last_name FROM hr_casino.employees LIMIT 3;",
  "results": [
    {
      "employee_id": 7,
      "first_name": "Michael",
      "last_name": "Miller",
      "department": "operations",
      "position": "Floor Manager",
      "salary": 47832
    },
    ...
  ],
  "execution_time": 2.5,
  "path_taken": "result_summarizer",
  "error": null
}
```

---

## 📱 Share Your API

Once deployed, share these links:

1. **Main Interface:** `https://your-app-name.vercel.app/`
   - For non-technical users

2. **API Docs:** `https://your-app-name.vercel.app/docs`
   - For developers

3. **Example Call:**
   ```bash
   curl -X POST https://your-app-name.vercel.app/query \
     -H "Content-Type: application/json" \
     -d '{"query": "Show me 5 employees"}'
   ```

---

## 🎨 Customization

To customize the web interface:

1. Edit `/api/public/index.html`
2. Change colors, add your logo, modify examples
3. Redeploy: `vercel --prod`

---

## 📊 Monitor Usage

In Vercel Dashboard, you can see:
- ✅ Number of API calls
- ✅ Response times
- ✅ Error rates
- ✅ Geographic distribution of users

---

## 🔒 Optional: Add Authentication

If you want to restrict access:

1. Add API key requirement
2. Use Vercel's Edge Config
3. Implement rate limiting

See `VERCEL_DEPLOYMENT.md` for details.

---

## 💡 Tips for Sharing

1. **Create a demo video** showing the web interface
2. **Provide example queries** that work well
3. **Explain what data is available** (7 tables, casino operations)
4. **Share the Swagger docs link** for developers
5. **Set up a feedback form** to collect user questions

---

## 🎉 Your API is Public!

Once deployed, anyone in the world can:
- ✅ Ask questions in natural language
- ✅ Get instant SQL generation
- ✅ See query results
- ✅ All without any setup or installation

Perfect for:
- 📊 Data analysts
- 💼 Business users
- 👨‍💻 Developers
- 🎓 Students learning SQL

