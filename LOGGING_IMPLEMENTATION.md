# 📋 Logging System - Complete Implementation

## What Was Added

I've implemented a **comprehensive, production-ready logging system** throughout the entire AI Workflow. Here's what you now have:

## ✅ New Features

### 1. **Logging Configuration Module** (`logging_config.py`)
- **Multiple formatters**: Console (colored) and Structured JSON
- **Flexible configuration**: Environment variable based
- **Request ID tracking**: Correlate logs across the entire workflow
- **Helper functions**: Easy logging of common events
- **File and console output**: Dual logging support

### 2. **Logging Added to All Nodes**
Every node now has comprehensive logging:
- ✅ **Supervisor** - Intent classification, confidence scoring
- ✅ **Conversation** - Chat handling
- ✅ **Fallback** - Clarification requests
- ✅ **Schema Feasibility** - Schema validation
- ✅ **SQL Generator** - SQL generation process
- ✅ **SQL Validator** - Validation results
- ✅ **Databricks Executor** - Query execution, timing, results
- ✅ **Result Summarizer** - Summary generation

### 3. **Routing Logic Logging** (`workflow.py`)
All routing decisions are logged with:
- Source node
- Destination node
- Reason for routing decision
- Confidence scores
- Error messages (if applicable)

### 4. **Orchestrator Logging** (`main.py`)
- Request initialization with unique IDs
- Overall execution flow
- Performance metrics
- Error tracking

## 📊 What Gets Logged

### Request Tracking
```
2024-12-19 10:30:45 | INFO | ai_workflow.orchestrator | ==================================================
2024-12-19 10:30:45 | INFO | ai_workflow.orchestrator | NEW QUERY [ID: a3f8b2c1]
2024-12-19 10:30:45 | INFO | ai_workflow.orchestrator | User input: Show me all customers
```

### Node Execution
```
2024-12-19 10:30:45 | INFO | ai_workflow.supervisor | Entering node: Supervisor
2024-12-19 10:30:45 | INFO | ai_workflow.supervisor | Classifying intent for query: 'Show me all customers...'
2024-12-19 10:30:46 | INFO | ai_workflow.supervisor | Intent classified: databricks (confidence: 0.92) in 0.423s
2024-12-19 10:30:46 | INFO | ai_workflow.supervisor | Exiting node: Supervisor
```

### Routing Decisions
```
2024-12-19 10:30:46 | INFO | ai_workflow.routing | Routing: supervisor → schema_feasibility (databricks intent with high confidence (0.92))
```

### SQL Execution
```
2024-12-19 10:30:49 | INFO | ai_workflow.databricks_executor | Executing SQL query...
2024-12-19 10:30:51 | INFO | ai_workflow.databricks_executor | SQL executed in 1.234s
2024-12-19 10:30:51 | INFO | ai_workflow.databricks_executor | Query executed successfully: 42 rows returned
```

### Performance Metrics
```
2024-12-19 10:30:52 | INFO | ai_workflow.orchestrator | Query completed successfully in 3.421s
```

### Errors (with full stack traces)
```
2024-12-19 10:30:51 | ERROR | ai_workflow.databricks_executor | Error in Query execution: Connection timeout
Traceback (most recent call last):
  File "nodes/databricks_executor.py", line 89, in _execute_query
    ...
```

## 🎛️ Configuration

Add to your `.env` file:

```bash
# Logging Configuration
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_TO_FILE=true                  # Enable file logging
LOG_FILE=logs/ai_workflow.log     # Log file path
LOG_STRUCTURED=false              # Use JSON structured logging
```

### Quick Configurations

**Development (see everything):**
```bash
LOG_LEVEL=DEBUG
LOG_TO_FILE=true
LOG_STRUCTURED=false
```

**Production (structured logs for aggregation):**
```bash
LOG_LEVEL=INFO
LOG_TO_FILE=true
LOG_STRUCTURED=true
```

**Troubleshooting (maximum detail):**
```bash
LOG_LEVEL=DEBUG
LOG_TO_FILE=true
LOG_STRUCTURED=false
```

## 📁 New Files Created

1. **`logging_config.py`** - Complete logging configuration module
2. **`LOGGING.md`** - Comprehensive logging documentation
3. **`logging_example.py`** - Working example showing logging in action

## 🚀 How to Use

### Basic Usage (Automatic)

Logging is automatically initialized when you use the orchestrator:

```python
from main import AIWorkflowOrchestrator

orchestrator = AIWorkflowOrchestrator(use_mock_schema=True)
result = orchestrator.query("Show me all customers")
# Logs are automatically generated!
```

### See It in Action

```bash
# Run the logging example
python logging_example.py

# This will show you:
# - Request ID tracking
# - Node entry/exit
# - Routing decisions
# - LLM calls
# - SQL execution
# - Performance metrics
```

### View Logs

```bash
# Watch logs in real-time
tail -f logs/ai_workflow.log

# Search for errors
grep "ERROR" logs/ai_workflow.log

# Find slow queries
grep "Query completed" logs/ai_workflow.log | grep -v "in [0-4]\."

# Track a specific request
grep "a3f8b2c1" logs/ai_workflow.log
```

## 🎯 Key Features

### 1. Request ID Tracking
Every query gets a unique ID that follows it through the entire workflow:
```python
Request ID: a3f8b2c1
```

You can track this ID through all logs to see the complete execution path.

### 2. Colored Console Output
Logs are color-coded by level:
- 🔵 DEBUG - Cyan
- 🟢 INFO - Green  
- 🟡 WARNING - Yellow
- 🔴 ERROR - Red
- 🟣 CRITICAL - Magenta

### 3. Structured JSON Logging
For production environments, enable JSON logging:
```json
{
  "timestamp": "2024-12-19T10:30:45.123456",
  "level": "INFO",
  "logger": "ai_workflow.supervisor",
  "message": "Intent classified: databricks",
  "intent": "databricks",
  "confidence": 0.92,
  "execution_time": 0.423,
  "request_id": "a3f8b2c1"
}
```

Perfect for:
- Elasticsearch/Kibana
- Splunk
- Datadog
- CloudWatch
- Any log aggregation tool

### 4. Performance Tracking
Execution time is logged for:
- Overall query execution
- Each node execution
- LLM calls
- SQL execution
- Every major operation

### 5. Detailed Error Tracking
Errors include:
- Full stack traces
- Context about where the error occurred
- Request ID for correlation
- Original error type and message

## 📖 Documentation

See **`LOGGING.md`** for complete documentation including:
- Configuration options
- Log format details
- Integration with log aggregation tools
- Best practices
- Troubleshooting guide
- Example searches and queries

## 🎬 Example Output

When you run a query, you'll see logs like this:

```
2024-12-19 10:30:45 | INFO     | ai_workflow.orchestrator | ==================================================
2024-12-19 10:30:45 | INFO     | ai_workflow.orchestrator | NEW QUERY [ID: a3f8b2c1]
2024-12-19 10:30:45 | INFO     | ai_workflow.orchestrator | User input: Show me all customers
2024-12-19 10:30:45 | INFO     | ai_workflow.orchestrator | ==================================================
2024-12-19 10:30:45 | INFO     | ai_workflow.orchestrator | Starting workflow execution...
2024-12-19 10:30:45 | INFO     | ai_workflow.supervisor | Entering node: Supervisor
2024-12-19 10:30:45 | INFO     | ai_workflow.supervisor | Classifying intent for query: 'Show me all customers...'
2024-12-19 10:30:45 | DEBUG    | ai_workflow.supervisor | Using 0 messages from history
2024-12-19 10:30:46 | DEBUG    | ai_workflow.supervisor | LLM call: gpt-4o-mini (supervisor)
2024-12-19 10:30:46 | INFO     | ai_workflow.supervisor | Intent classified: databricks (confidence: 0.92) in 0.423s
2024-12-19 10:30:46 | INFO     | ai_workflow.supervisor | Exiting node: Supervisor
2024-12-19 10:30:46 | INFO     | ai_workflow.routing | Routing: supervisor → schema_feasibility (databricks intent with high confidence (0.92))
...
2024-12-19 10:30:52 | INFO     | ai_workflow.orchestrator | Query completed successfully in 3.421s
```

## 🎨 Benefits

### For Development
- **Debug easily**: See exactly what's happening at each step
- **Performance profiling**: Identify slow operations
- **Error diagnosis**: Full stack traces with context

### For Production
- **Monitoring**: Track system health
- **Alerting**: Set up alerts on errors or slow queries
- **Analytics**: Analyze query patterns, intents, performance
- **Troubleshooting**: Correlate issues across the workflow

### For Operations
- **Request tracking**: Follow queries end-to-end
- **Performance metrics**: Track latency, throughput
- **Error rates**: Monitor system reliability
- **Capacity planning**: Understand usage patterns

## 🔧 Advanced Usage

### Custom Logging in Your Code

```python
from logging_config import get_logger

logger = get_logger("my_custom_module")

logger.debug("Detailed debug info")
logger.info("Something happened", extra={'user_id': '123'})
logger.warning("Potential issue")
logger.error("Error occurred", exc_info=True)
```

### Changing Log Level at Runtime

```bash
# Set before running
export LOG_LEVEL=DEBUG
python main.py --mock --interactive

# Or in code
import os
os.environ["LOG_LEVEL"] = "DEBUG"
```

## 📈 Integration Examples

### Elasticsearch/Kibana

1. Enable JSON logging: `LOG_STRUCTURED=true`
2. Configure Filebeat
3. Visualize in Kibana with queries like:
   - `level: "ERROR"`
   - `execution_time > 5`
   - `intent: "databricks"`

### Datadog

1. Install Datadog agent
2. Enable structured logging
3. Create monitors for:
   - High error rates
   - Slow queries
   - Low confidence trends

### Splunk

```
source="ai_workflow.log" level="ERROR"
source="ai_workflow.log" execution_time>5
source="ai_workflow.log" | stats avg(execution_time) by intent
```

## ✅ Summary

You now have **enterprise-grade logging** that provides:

✅ **Complete visibility** - See everything happening in the workflow
✅ **Request tracking** - Follow queries end-to-end with unique IDs
✅ **Performance metrics** - Track execution times everywhere
✅ **Error tracking** - Full stack traces with context
✅ **Flexible configuration** - Environment-based settings
✅ **Multiple outputs** - Console and file logging
✅ **Structured logging** - JSON format for log aggregation tools
✅ **Production ready** - Suitable for monitoring and alerting

Run `python logging_example.py` to see it all in action! 🎉

