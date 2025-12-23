# AI Workflow API

Natural language to SQL query API for casino database operations.

## 🚀 Quick Start

### Deploy to Vercel

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/yourusername/ai-workflow)

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp env.template .env
# Edit .env with your API keys

# Run API locally
uvicorn api.index:app --reload --port 8000

# Visit http://localhost:8000/docs for API documentation
```

## 📡 API Endpoints

### `GET /` - Root
Health check endpoint

### `GET /health` - Health Check
```json
{
  "status": "healthy",
  "tables_cached": 7
}
```

### `GET /schema` - Get Database Schema
Returns all available tables with columns and descriptions.

### `POST /query` - Execute Query
Execute a natural language query against the casino database.

**Request:**
```json
{
  "query": "Which employees generated the highest revenue per shift?",
  "conversation_history": []
}
```

**Response:**
```json
{
  "response": "Query returned 3 employees with Michael Miller having the highest average revenue per shift at $2,450...",
  "sql": "SELECT e.employee_id, e.first_name, e.last_name, AVG(s.total_revenue)...",
  "results": [...],
  "execution_time": 2.5,
  "path_taken": "result_summarizer",
  "error": null
}
```

### `GET /examples` - Get Example Queries
Returns categorized example queries users can try.

## 🗄️ Database Schema

The API works with a casino operations database with 7 tables:

- **hr_casino.employees** - Employee directory
- **marketing_casino.customers** - Customer profiles
- **marketing_casino.customer_behaviors** - Customer gambling patterns
- **operations_casino.game_sessions** - Gaming session data
- **operations_casino.gaming_equipment** - Equipment inventory
- **operations_casino.shifts** - Employee shift tracking
- **finance_casino.transactions** - Transaction history

## 🔧 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | ✅ | OpenAI API key |
| `CASINO_API_URL` | ✅ | Casino database API endpoint |
| `LOG_LEVEL` | ❌ | Logging level (default: INFO) |
| `MAIN_MODEL` | ❌ | OpenAI model (default: gpt-4o) |

## 📚 Documentation

- [Vercel Deployment Guide](VERCEL_DEPLOYMENT.md)
- [Project Overview](PROJECTSUMMARY.md)
- [SQL Generator Improvements](SQL_GENERATOR_IMPROVEMENTS.md)

## 🧪 Example Queries

**Simple:**
- "Show me the first 5 employees"
- "How many customers are there?"
- "List all active employees"

**Analytical:**
- "Which employees generated the highest revenue per shift?"
- "What is the average transaction amount per customer?"
- "How many customers are in each region?"

**Complex:**
- "Show high-risk customers who lost more than $5000 in game sessions"
- "Find customers with the highest problem gambling scores by region"

## 🏗️ Architecture

The system uses LangGraph to orchestrate a multi-node workflow:

1. **Supervisor** - Classifies user intent (conversation/databricks/fallback)
2. **Schema Feasibility** - Checks if query is answerable with available schema
3. **SQL Generator** - Generates optimized SQL from natural language
4. **SQL Validator** - Validates SQL for safety and correctness
5. **API Executor** - Executes query against database
6. **Result Summarizer** - Formats results in natural language

## 🛡️ Security

- No direct database access (uses API layer)
- SQL injection prevention through validation
- Read-only operations (SELECT only)
- Rate limiting recommended for production

## 📄 License

MIT

## 🤝 Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

