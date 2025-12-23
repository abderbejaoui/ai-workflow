# Quick Start Guide

Get up and running with the AI Workflow Orchestrator in 5 minutes.

## Prerequisites

- Python 3.9 or higher
- OpenAI API key (or Anthropic API key)
- Databricks workspace (optional for testing - can use mock schema)

## Installation

### 1. Clone or Download

```bash
cd ai-workflow
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- LangGraph & LangChain
- OpenAI/Anthropic SDKs
- Databricks SQL connector
- Supporting libraries

### 3. Configure Environment

```bash
cp env.template .env
```

Edit `.env` with your credentials:

```bash
# Required
OPENAI_API_KEY=sk-your-key-here

# Optional (for production)
DATABRICKS_SERVER_HOSTNAME=your-workspace.cloud.databricks.com
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/your-warehouse-id
DATABRICKS_ACCESS_TOKEN=dapi-your-token-here
```

**For quick testing**: You only need the OpenAI API key. The system will use a mock schema.

## Testing the System

### Option 1: Single Query (Fastest)

```bash
python main.py --mock --query "Show me all customers"
```

Output:
```
============================================================
AI WORKFLOW ORCHESTRATOR
============================================================
Loading schema metadata...
✓ Mock schema loaded

System ready:
  - Tables cached: 3
  - Confidence threshold: 0.75
  - Query timeout: 2s

============================================================
Query: Show me all customers
============================================================

Intent: databricks (confidence: 0.95)
Path: result_summarizer
SQL: SELECT customer_id, name, email, signup_date, country FROM main.analytics.customers LIMIT 100;
Execution time: 3.421s

Response: The query returned all customer records from the database...
============================================================
```

### Option 2: Interactive Mode (Recommended)

```bash
python main.py --mock --interactive
```

Example session:
```
You: Hello!
Assistant: Hello! I'm here to help you query and analyze data. What would you like to know?
[0.82s | conversation]

You: Show me all customers from USA
Assistant: I found 42 customers from USA in the database. The results include customer details such as ID, name, email...
[3.15s | result_summarizer]

You: What about orders?
Assistant: Could you please be more specific? Would you like to see all orders, orders for specific customers, or orders filtered by date or status?
[0.94s | fallback]
```

Type `exit` to quit, `reset` to clear conversation history.

### Option 3: Run Test Suite

```bash
python examples.py
```

This runs comprehensive tests for all three paths:
- Conversation path
- Fallback path  
- Databricks query path
- Performance benchmarks

## Understanding the Output

### Execution Metadata

Each query returns:
```python
{
    "response": "The natural language answer",
    "execution_time": 2.34,  # seconds
    "path_taken": "result_summarizer",  # last node
    "intent": "databricks",
    "confidence": 0.87,
    "sql": "SELECT ...",  # if SQL was generated
}
```

### Path Indicators

- `conversation` - General chat handled
- `fallback` - Clarification needed
- `result_summarizer` - Databricks query executed successfully
- `error` - Something went wrong

## Example Queries to Try

### Conversation Queries
```
"Hello, how are you?"
"What can you help me with?"
"Thank you!"
```

### Data Queries (with mock schema)
```
"Show me all customers"
"How many customers are there?"
"List customers from USA"
"What are the top 5 orders by amount?"
"Show me products in Electronics category"
"What's the average order value?"
```

### Ambiguous Queries (triggers fallback)
```
"Show me that thing from yesterday"
"Give me the data"
"What about those records?"
```

## Using with Real Databricks

### 1. Get Databricks Credentials

From your Databricks workspace:
- Server hostname: Settings → Advanced → JDBC/ODBC
- HTTP path: SQL Warehouses → Your warehouse → Connection details
- Access token: User Settings → Access Tokens → Generate new token

### 2. Update .env

```bash
DATABRICKS_SERVER_HOSTNAME=your-company.cloud.databricks.com
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/abc123def456
DATABRICKS_ACCESS_TOKEN=dapi-1234567890abcdef...
```

### 3. Run Without Mock Schema

```bash
python main.py --interactive
```

This will load your actual Databricks schema at startup.

## Programmatic Usage

```python
from main import AIWorkflowOrchestrator

# Initialize (loads schema)
orchestrator = AIWorkflowOrchestrator(use_mock_schema=True)

# Execute query
result = orchestrator.query("Show me all customers")

# Access results
print(result['response'])
print(f"Took {result['execution_time']:.2f}s via {result['path_taken']}")

if result.get('sql'):
    print(f"SQL: {result['sql']}")

# Multi-turn conversation
result1 = orchestrator.query("Show me customers")
result2 = orchestrator.query("How many are there?")  # Uses context

# Reset conversation
orchestrator.reset_conversation()
```

## Visualizing the Workflow

```bash
python visualize.py
```

This prints:
- ASCII workflow diagram
- Detailed node information
- Performance characteristics

## Customization

### Change Models

Edit `config.py`:
```python
SUPERVISOR_MODEL = "gpt-4o-mini"  # Fast routing
MAIN_MODEL = "gpt-4o"              # Quality responses
```

Or via environment:
```bash
export SUPERVISOR_MODEL=gpt-4o-mini
export MAIN_MODEL=gpt-4o
```

### Adjust Thresholds

```bash
# Require higher confidence for Databricks path
export DATABRICKS_CONFIDENCE_THRESHOLD=0.85

# Allow longer queries
export DATABRICKS_QUERY_TIMEOUT=5
```

### Change Result Limits

```python
# In config.py
MAX_RESULT_ROWS = 1000
CONVERSATION_HISTORY_LIMIT = 5
RESULT_SUMMARY_MAX_TOKENS = 150
```

## Troubleshooting

### "No API key configured"
- Ensure `.env` file exists in project root
- Check `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` is set
- Try: `python -c "from config import config; print(config.OPENAI_API_KEY)"`

### "Failed to connect to Databricks"
- Verify credentials in `.env`
- Test connection: `python -c "from databricks import sql; print('OK')"`
- Use mock schema for testing: `--mock` flag

### "Module not found"
- Ensure virtual environment activated
- Reinstall: `pip install -r requirements.txt --upgrade`

### "Query timeout"
- Query too complex or warehouse cold
- Increase timeout: `export DATABRICKS_QUERY_TIMEOUT=5`
- Check warehouse is running

### High Latency
- First query always slower (cold start)
- Check network latency to OpenAI/Databricks
- Monitor with: `result['execution_time']`

## Next Steps

1. **Read the Architecture**: See `ARCHITECTURE.md` for deep dive
2. **Customize Nodes**: Extend nodes in `nodes/` directory
3. **Add Monitoring**: Integrate logging and metrics
4. **Deploy**: Wrap in FastAPI/Flask for production
5. **Scale**: Use Redis for schema cache, horizontal scaling

## Getting Help

- Review `README.md` for full documentation
- Check `ARCHITECTURE.md` for design details
- Run `python examples.py` for working examples
- Examine `nodes/` for implementation details

## Quick Reference

```bash
# Test with mock data
python main.py --mock --interactive

# Single query
python main.py --mock --query "your question"

# Real Databricks
python main.py --interactive

# Run tests
python examples.py

# Visualize
python visualize.py
```

---

**You're ready to go!** Start with `--mock --interactive` and explore the system.

