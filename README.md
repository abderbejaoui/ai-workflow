# AI Workflow Orchestrator

A production-grade LangGraph orchestration system for natural language to SQL queries with intelligent routing and conversation handling.

## 🎯 Overview

This system implements a sophisticated AI workflow that:
- Routes queries intelligently between conversation, SQL generation, and fallback paths
- Maintains <5 second end-to-end latency
- Uses cached schema metadata (no runtime lookups)
- Follows clean architecture with reusable components
- Enforces strict SQL validation and safety

## 🏗 Architecture

### Workflow Paths

```
START → Supervisor (Intent Classification)
         ↓
    ┌────┴────────────┐
    ↓         ↓        ↓
Conversation  |    Databricks Path
    ↓         ↓        ↓
   END    Fallback   Schema Check → SQL Gen → Validate → Execute → Summarize
             ↓                                                         ↓
            END                                                       END
```

### Components

**Supervisor Node** (`nodes/supervisor.py`)
- Lightweight intent classification
- Single fast LLM call (gpt-4o-mini)
- Outputs: intent + confidence score
- No database access

**Conversation Node** (`nodes/conversation.py`)
- Handles general chat
- Minimal token usage
- Single LLM call

**Fallback Node** (`nodes/fallback.py`)
- Clarifying questions
- Handles ambiguous queries
- No database access

**Databricks Path** (5 sequential nodes):
1. `SchemaFeasibilityChecker` - Validates against cached schema
2. `SQLGenerator` - Generates safe SQL
3. `SQLValidator` - Enforces guardrails
4. `DatabricksExecutor` - Executes with timeout
5. `ResultSummarizer` - Concise natural language summary

## 🚀 Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp env.template .env
# Edit .env with your API keys and Databricks credentials
```

### Configuration

Required in `.env`:
```bash
OPENAI_API_KEY=sk-...
DATABRICKS_SERVER_HOSTNAME=your-workspace.cloud.databricks.com
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/...
DATABRICKS_ACCESS_TOKEN=dapi...
```

### Usage

**Single Query:**
```bash
python main.py --mock --query "Show me all customers"
```

**Interactive Mode:**
```bash
python main.py --mock --interactive
```

**Programmatic Usage:**
```python
from main import AIWorkflowOrchestrator

# Initialize
orchestrator = AIWorkflowOrchestrator(use_mock_schema=False)

# Execute query
result = orchestrator.query("What are total sales by country?")
print(result['response'])
print(f"Took {result['execution_time']:.2f}s")
```

## 📦 Project Structure

```
ai-workflow/
├── main.py                 # Entry point & orchestrator
├── workflow.py             # LangGraph construction & routing
├── state.py               # State schema & types
├── config.py              # Configuration management
├── utils.py               # Utilities & helpers
├── schema_loader.py       # Schema caching system
├── nodes/
│   ├── __init__.py
│   ├── supervisor.py      # Intent classification
│   ├── conversation.py    # General chat handler
│   ├── fallback.py        # Clarification handler
│   ├── schema_feasibility.py  # Schema validation
│   ├── sql_generator.py   # SQL generation
│   ├── sql_validator.py   # SQL safety checks
│   ├── databricks_executor.py  # Query execution
│   └── result_summarizer.py    # Result formatting
├── requirements.txt
└── env.template
```

## 🔒 Safety Features

### SQL Validation
- No `SELECT *` allowed
- No DDL/DML operations (DROP, CREATE, etc.)
- Table existence verification
- Column validation
- Multiple statement blocking
- LIMIT clause enforcement

### Performance
- Schema pre-caching (no runtime discovery)
- Connection pooling
- Query timeout (2s default)
- Result size limits (1000 rows max)
- Minimal prompt sizes

### Logging
- **Comprehensive logging** at all levels (DEBUG, INFO, WARNING, ERROR)
- **Request ID tracking** - correlate logs across nodes
- **Structured logging** - JSON output for log aggregation tools
- **Performance metrics** - execution time tracking
- **Detailed routing logs** - see every decision made
- **File and console output** - configurable via environment

See [LOGGING.md](LOGGING.md) for complete logging documentation.

### Routing Logic
```python
if intent == "databricks" and confidence >= 0.75:
    → Databricks Path
elif confidence < 0.75:
    → Fallback (clarification)
elif intent == "conversation":
    → Conversation Path
else:
    → Fallback
```

## 🧪 Testing with Mock Schema

The system includes a mock schema for testing:
```python
# Tables: customers, orders, products
# Try queries like:
- "Show me all customers"
- "What are the total sales?"
- "List products by category"
```

## ⚙️ Configuration Options

Key settings in `config.py`:

| Setting | Default | Purpose |
|---------|---------|---------|
| `SUPERVISOR_MODEL` | gpt-4o-mini | Fast, cheap model for routing |
| `MAIN_MODEL` | gpt-4o | Quality model for generation |
| `DATABRICKS_QUERY_TIMEOUT` | 2s | Query execution limit |
| `MAX_RESULT_ROWS` | 1000 | Result size cap |
| `CONVERSATION_HISTORY_LIMIT` | 5 | Context window size |
| `DATABRICKS_CONFIDENCE_THRESHOLD` | 0.75 | Routing threshold |
| `LOG_LEVEL` | INFO | Logging verbosity |
| `LOG_TO_FILE` | true | Enable file logging |
| `LOG_STRUCTURED` | false | Use JSON logging |

## 📊 Performance Targets

- **End-to-end latency:** ≤ 5 seconds
- **Supervisor classification:** < 0.5s
- **SQL generation:** < 1s
- **Query execution:** ≤ 2s
- **Result summarization:** < 1s

## 🔧 Extending the System

### Adding New Nodes

1. Create node class in `nodes/`
2. Implement `__call__(state: WorkflowState) -> Dict[str, Any]`
3. Add to `nodes/__init__.py`
4. Update routing in `workflow.py`

### Custom Schema Loader

```python
from schema_loader import SchemaLoader

loader = SchemaLoader()
loader.load_from_json("my_schema.json")
```

### Custom Routing Logic

Modify routing functions in `workflow.py`:
```python
def route_from_supervisor(state: WorkflowState) -> str:
    # Your custom logic
    pass
```

## 📝 Example Queries

**Conversation:**
- "Hello, how are you?"
- "What can you help me with?"

**Data Queries:**
- "Show me top 10 customers by revenue"
- "What's the average order value?"
- "List all products in Electronics category"

**Fallback:**
- "Show me that thing from yesterday"
- "Give me the data"

## 🐛 Troubleshooting

**Schema not loading:**
```bash
# Use mock schema for testing
python main.py --mock --interactive
```

**API key errors:**
```bash
# Verify .env configuration
cat .env | grep API_KEY
```

**Import errors:**
```bash
# Ensure all dependencies installed
pip install -r requirements.txt --upgrade
```

## 📄 License

MIT License - feel free to use in your projects

## 🤝 Contributing

This is a production-ready template. Customize for your needs:
- Add authentication
- Implement result caching
- Add monitoring/logging
- Extend with more specialized nodes

---

**Built with:** LangGraph, LangChain, OpenAI, Databricks

