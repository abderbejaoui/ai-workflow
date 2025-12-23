# Logging Guide

## Overview

The AI Workflow system includes comprehensive logging to track everything that happens during query execution. Logs help with debugging, monitoring, and understanding the system's behavior.

## Log Levels

The system uses standard Python logging levels:

- **DEBUG**: Detailed information for debugging (SQL details, state dumps)
- **INFO**: General information about workflow execution (default)
- **WARNING**: Warning messages (potential issues)
- **ERROR**: Error messages (actual problems)
- **CRITICAL**: Critical errors (system failures)

## Configuration

### Environment Variables

Configure logging in your `.env` file:

```bash
# Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO

# Enable/disable file logging
LOG_TO_FILE=true

# Log file path
LOG_FILE=logs/ai_workflow.log

# Use JSON structured logging
LOG_STRUCTURED=false
```

### Quick Configuration Examples

**Development (verbose):**
```bash
LOG_LEVEL=DEBUG
LOG_TO_FILE=true
LOG_STRUCTURED=false
```

**Production (standard):**
```bash
LOG_LEVEL=INFO
LOG_TO_FILE=true
LOG_STRUCTURED=true  # JSON for log aggregation tools
```

**Troubleshooting (maximum detail):**
```bash
LOG_LEVEL=DEBUG
LOG_TO_FILE=true
LOG_STRUCTURED=false
```

## What Gets Logged

### 1. Request Tracking

Each query gets a unique Request ID for correlation:

```
2024-12-19 10:30:45 | INFO     | ai_workflow.orchestrator | ==================================================
2024-12-19 10:30:45 | INFO     | ai_workflow.orchestrator | NEW QUERY [ID: a3f8b2c1]
2024-12-19 10:30:45 | INFO     | ai_workflow.orchestrator | User input: Show me all customers
2024-12-19 10:30:45 | INFO     | ai_workflow.orchestrator | ==================================================
```

### 2. Node Execution

Every node logs entry and exit:

```
2024-12-19 10:30:45 | INFO     | ai_workflow.supervisor | Entering node: Supervisor
2024-12-19 10:30:45 | INFO     | ai_workflow.supervisor | Classifying intent for query: 'Show me all customers...'
2024-12-19 10:30:46 | INFO     | ai_workflow.supervisor | Intent classified: databricks (confidence: 0.92) in 0.423s
2024-12-19 10:30:46 | INFO     | ai_workflow.supervisor | Exiting node: Supervisor
```

### 3. Routing Decisions

All routing decisions are logged with reasons:

```
2024-12-19 10:30:46 | INFO     | ai_workflow.routing | Routing: supervisor → schema_feasibility (databricks intent with high confidence (0.92))
```

### 4. LLM Calls

Every LLM call is tracked:

```
2024-12-19 10:30:46 | DEBUG    | ai_workflow.supervisor | LLM call: gpt-4o-mini (supervisor)
2024-12-19 10:30:47 | DEBUG    | ai_workflow.sql_generator | LLM call: gpt-4o (SQL generation)
```

### 5. SQL Generation and Execution

SQL queries are logged (with truncation for long queries):

```
2024-12-19 10:30:48 | INFO     | ai_workflow.sql_generator | Generating SQL for query: 'Show me all customers...'
2024-12-19 10:30:49 | INFO     | ai_workflow.sql_generator | SQL generated in 0.832s
2024-12-19 10:30:49 | DEBUG    | ai_workflow.sql_generator | Full SQL: SELECT customer_id, name, email FROM ...
2024-12-19 10:30:49 | INFO     | ai_workflow.databricks_executor | Executing SQL query...
2024-12-19 10:30:51 | INFO     | ai_workflow.databricks_executor | SQL executed in 1.234s
```

### 6. Errors and Exceptions

Errors are logged with full stack traces:

```
2024-12-19 10:30:51 | ERROR    | ai_workflow.databricks_executor | Error in Query execution: Connection timeout
Traceback (most recent call last):
  File "nodes/databricks_executor.py", line 89, in _execute_query
    cursor.execute(sql)
  ...
```

### 7. Performance Metrics

Execution times for all major operations:

```
2024-12-19 10:30:52 | INFO     | ai_workflow.orchestrator | Query completed successfully in 3.421s
```

## Log Formats

### Console Format (Default)

Colorized, human-readable format:

```
2024-12-19 10:30:45 | INFO     | ai_workflow.orchestrator | Query completed successfully
```

### Structured JSON Format

Machine-readable JSON for log aggregation tools (ELK, Splunk, etc.):

```json
{
  "timestamp": "2024-12-19T10:30:45.123456",
  "level": "INFO",
  "logger": "ai_workflow.orchestrator",
  "message": "Query completed successfully",
  "execution_time": 3.421,
  "intent": "databricks",
  "confidence": 0.92,
  "request_id": "a3f8b2c1"
}
```

Enable with: `LOG_STRUCTURED=true`

## Log Locations

### Console Output

Always displayed to stdout (can be disabled if needed).

### File Output

Default location: `logs/ai_workflow.log`

The system automatically creates the `logs/` directory if it doesn't exist.

## Example Log Flow

Here's what a complete query execution looks like in the logs:

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

2024-12-19 10:30:46 | INFO     | ai_workflow.schema_feasibility | Entering node: SchemaFeasibilityChecker
2024-12-19 10:30:47 | INFO     | ai_workflow.schema_feasibility | Query is feasible
2024-12-19 10:30:47 | INFO     | ai_workflow.schema_feasibility | Exiting node: SchemaFeasibilityChecker

2024-12-19 10:30:47 | INFO     | ai_workflow.routing | Routing: schema_feasibility → sql_generator (query is feasible)

2024-12-19 10:30:47 | INFO     | ai_workflow.sql_generator | Entering node: SQLGenerator
2024-12-19 10:30:47 | INFO     | ai_workflow.sql_generator | Generating SQL for query: 'Show me all customers...'
2024-12-19 10:30:47 | DEBUG    | ai_workflow.sql_generator | Candidate tables: ['main.analytics.customers']
2024-12-19 10:30:47 | DEBUG    | ai_workflow.sql_generator | LLM call: gpt-4o (SQL generation)
2024-12-19 10:30:48 | INFO     | ai_workflow.sql_generator | SQL generated in 0.832s
2024-12-19 10:30:48 | DEBUG    | ai_workflow.sql_generator | Full SQL: SELECT customer_id, name, email, signup_date, country FROM main.analytics.customers LIMIT 100;
2024-12-19 10:30:48 | INFO     | ai_workflow.sql_generator | Exiting node: SQLGenerator

2024-12-19 10:30:48 | INFO     | ai_workflow.sql_validator | Entering node: SQLValidator
2024-12-19 10:30:48 | INFO     | ai_workflow.sql_validator | SQL validation passed
2024-12-19 10:30:48 | INFO     | ai_workflow.sql_validator | Exiting node: SQLValidator

2024-12-19 10:30:48 | INFO     | ai_workflow.routing | Routing: sql_validator → databricks_executor (SQL is valid)

2024-12-19 10:30:49 | INFO     | ai_workflow.databricks_executor | Entering node: DatabricksExecutor
2024-12-19 10:30:49 | INFO     | ai_workflow.databricks_executor | Executing SQL query...
2024-12-19 10:30:49 | DEBUG    | ai_workflow.databricks_executor | SQL: SELECT customer_id, name, email, signup_date, country FROM main.analytics.customers LIMIT 100;
2024-12-19 10:30:49 | DEBUG    | ai_workflow.databricks_executor | Getting database cursor...
2024-12-19 10:30:49 | DEBUG    | ai_workflow.databricks_executor | Executing query with timeout: 2s
2024-12-19 10:30:51 | INFO     | ai_workflow.databricks_executor | SQL executed in 1.234s
2024-12-19 10:30:51 | INFO     | ai_workflow.databricks_executor | Query executed successfully: 42 rows returned
2024-12-19 10:30:51 | INFO     | ai_workflow.databricks_executor | Exiting node: DatabricksExecutor

2024-12-19 10:30:51 | INFO     | ai_workflow.routing | Routing: databricks_executor → result_summarizer (query executed successfully)

2024-12-19 10:30:51 | INFO     | ai_workflow.result_summarizer | Entering node: ResultSummarizer
2024-12-19 10:30:52 | INFO     | ai_workflow.result_summarizer | Results summarized
2024-12-19 10:30:52 | INFO     | ai_workflow.result_summarizer | Exiting node: ResultSummarizer

2024-12-19 10:30:52 | INFO     | ai_workflow.orchestrator | Workflow execution completed
2024-12-19 10:30:52 | INFO     | ai_workflow.orchestrator | Query completed successfully in 3.421s
```

## Programmatic Access

### Custom Logging in Your Code

```python
from logging_config import get_logger

logger = get_logger("my_module")

logger.debug("Detailed debug information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred")
```

### Adding Context to Logs

```python
logger.info(
    "Custom event",
    extra={
        'request_id': 'abc123',
        'user_id': 'user456',
        'custom_field': 'value'
    }
)
```

## Monitoring and Analysis

### Finding Errors

```bash
# Search for errors in logs
grep "ERROR" logs/ai_workflow.log

# Find slow queries (>5s)
grep "Query completed" logs/ai_workflow.log | grep -v "in [0-4]\."
```

### Performance Analysis

```bash
# Extract execution times
grep "execution_time" logs/ai_workflow.log

# Count queries by intent
grep "Intent classified" logs/ai_workflow.log | cut -d: -f4 | sort | uniq -c
```

### Request Tracking

```bash
# Follow a specific request through logs
grep "a3f8b2c1" logs/ai_workflow.log
```

## Integration with Log Aggregation Tools

### Elasticsearch/Kibana

1. Enable structured logging: `LOG_STRUCTURED=true`
2. Configure Filebeat to ship logs
3. Create Kibana dashboards for:
   - Query throughput
   - Latency percentiles
   - Error rates
   - Intent distribution

### Splunk

1. Enable structured logging
2. Configure Splunk forwarder
3. Use search queries:
   ```
   source="ai_workflow.log" level="ERROR"
   source="ai_workflow.log" execution_time>5
   source="ai_workflow.log" intent="databricks" | stats avg(execution_time)
   ```

### Datadog

1. Install Datadog agent
2. Configure log collection
3. Create monitors for:
   - High error rate
   - Slow queries
   - Low confidence scores

## Best Practices

1. **Use Appropriate Log Levels**
   - DEBUG: Only during development
   - INFO: Default for production
   - WARNING/ERROR: Always enabled

2. **Monitor Log File Size**
   ```bash
   # Rotate logs
   mv logs/ai_workflow.log logs/ai_workflow.log.1
   ```

3. **Use Request IDs**
   - Helps track queries through the system
   - Essential for debugging distributed systems

4. **Enable Structured Logging in Production**
   - Easier to parse and analyze
   - Better for log aggregation tools

5. **Set Up Alerts**
   - Alert on ERROR level logs
   - Alert on high latency (>5s)
   - Alert on low confidence trends

## Troubleshooting

### No Logs Appearing

```bash
# Check log level
echo $LOG_LEVEL

# Check file permissions
ls -la logs/

# Verify logger initialization
python -c "from logging_config import init_default_logger; init_default_logger()"
```

### Too Many Logs

```bash
# Increase log level
LOG_LEVEL=WARNING

# Disable file logging
LOG_TO_FILE=false
```

### Log File Growing Too Large

```bash
# Implement log rotation
# Add to crontab:
0 0 * * * mv /path/to/logs/ai_workflow.log /path/to/logs/ai_workflow.log.$(date +\%Y\%m\%d)
```

---

**Quick Reference:**

```bash
# Development
LOG_LEVEL=DEBUG

# Production
LOG_LEVEL=INFO LOG_STRUCTURED=true

# Troubleshooting
LOG_LEVEL=DEBUG LOG_TO_FILE=true

# View logs
tail -f logs/ai_workflow.log

# Search logs
grep "ERROR" logs/ai_workflow.log
```

