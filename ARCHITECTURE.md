# Architecture Documentation

## System Overview

This is a production-grade AI orchestration system built with LangGraph that intelligently routes natural language queries through three distinct execution paths: conversation, fallback, and Databricks SQL query generation.

## Design Principles

1. **Performance First**: Target <5s end-to-end latency
2. **Safety**: Strict SQL validation and guardrails
3. **Efficiency**: Minimal LLM calls, cached metadata
4. **Maintainability**: Clean separation of concerns, reusable components
5. **Production-Ready**: Error handling, connection pooling, monitoring

## Core Architecture

### State Management

The entire workflow operates on a shared state schema (`WorkflowState`) that contains:

- **Input**: `user_input`, `conversation_history`
- **Cached Data**: `schema_cache` (read-only)
- **Routing**: `intent`, `confidence`
- **Databricks Path**: `feasibility_check`, `generated_sql`, `validation_result`, `query_result`
- **Output**: `response`
- **Metadata**: `current_node`, `error_message`

State mutations are minimal and intentional - each node only updates what it needs.

### Three Execution Paths

#### 1. Conversation Path (Simple)
```
Supervisor → Conversation → END
```
- **Trigger**: `intent == "conversation"`
- **Use Case**: Greetings, system questions, general chat
- **Latency**: ~1.5s
- **LLM Calls**: 2 (supervisor + conversation)

#### 2. Fallback Path (Clarification)
```
Supervisor → Fallback → END
```
- **Trigger**: `confidence < 0.75` OR validation failures
- **Use Case**: Ambiguous queries, errors, unclear intent
- **Latency**: ~1.5s
- **LLM Calls**: 2 (supervisor + fallback)

#### 3. Databricks Path (Complex)
```
Supervisor → Schema Feasibility → SQL Generator → SQL Validator → 
Databricks Executor → Result Summarizer → END
```
- **Trigger**: `intent == "databricks" AND confidence >= 0.75`
- **Use Case**: Data queries requiring SQL execution
- **Latency**: ~5s (worst case)
- **LLM Calls**: 4 (supervisor + feasibility + generator + summarizer)

### Routing Logic

Implemented in `workflow.py` with conditional edges:

```python
def route_from_supervisor(state):
    if intent == "databricks" and confidence >= 0.75:
        return "schema_feasibility"
    elif confidence < 0.75:
        return "fallback"
    elif intent == "conversation":
        return "conversation"
    else:
        return "fallback"
```

Each critical decision point has a routing function that examines state and returns the next node name.

## Node Implementations

### 1. Supervisor Node
**File**: `nodes/supervisor.py`
**Class**: `SupervisorNode`

**Responsibility**: Intent classification and confidence scoring

**Architecture**:
- Uses lightweight model (gpt-4o-mini) for speed
- Single LLM call with structured JSON output
- No database access
- Processes minimal context (last 2-3 messages)

**Output**:
```json
{
  "intent": "conversation" | "databricks" | "fallback",
  "confidence": 0.85,
  "reasoning": "User is asking for data analysis"
}
```

**Performance**: ~300-500ms

### 2. Conversation Node
**File**: `nodes/conversation.py`
**Class**: `ConversationResponder`

**Responsibility**: Handle general chat

**Architecture**:
- Uses main LLM (gpt-4o)
- Stateless beyond minimal history
- Single LLM call
- Token-optimized prompts

**Performance**: ~1s

### 3. Fallback Node
**File**: `nodes/fallback.py`
**Class**: `FallbackClarifier`

**Responsibility**: Ask clarifying questions

**Architecture**:
- Analyzes why fallback was triggered
- Provides context-aware clarification
- Suggests available tables
- No database access

**Triggers**:
- Low confidence score
- Validation failures
- Infeasible queries
- Execution errors

**Performance**: ~1s

### 4. Schema Feasibility Checker
**File**: `nodes/schema_feasibility.py`
**Class**: `SchemaFeasibilityChecker`

**Responsibility**: Validate query against cached schema

**Architecture**:
- Uses ONLY pre-cached schema (no DB calls)
- LLM-based analysis of query vs available tables
- Identifies candidate tables and columns
- Rejects if tables/columns don't exist

**Output**:
```json
{
  "feasible": true,
  "tables": ["main.analytics.customers"],
  "columns": ["customer_id", "name", "email"],
  "reason": "All required tables and columns available"
}
```

**Performance**: ~500ms

### 5. SQL Generator
**File**: `nodes/sql_generator.py`
**Class**: `SQLGenerator`

**Responsibility**: Generate safe, high-precision SQL

**Architecture**:
- Generates SQL with strict rules
- Uses schema subset for relevant tables only
- Post-processing for safety

**Rules Enforced**:
- ✓ No `SELECT *` - explicit columns only
- ✓ Fully qualified table names
- ✓ LIMIT clause required
- ✓ Only SELECT statements
- ✓ Proper JOIN syntax

**Performance**: ~1s

### 6. SQL Validator
**File**: `nodes/sql_validator.py`
**Class**: `SQLValidator`

**Responsibility**: Enforce safety guardrails

**Architecture**:
- Rule-based validation (no LLM)
- Pattern matching for dangerous operations
- Schema existence checks

**Checks**:
- ✗ No DDL (DROP, CREATE, ALTER, TRUNCATE)
- ✗ No DML (DELETE, INSERT, UPDATE)
- ✗ No multiple statements
- ✗ No system schema access
- ✓ Tables exist in schema
- ✓ LIMIT clause present

**Output**:
```json
{
  "valid": true,
  "errors": [],
  "warnings": ["No explicit column types"]
}
```

**Performance**: <100ms

### 7. Databricks Executor
**File**: `nodes/databricks_executor.py`
**Class**: `DatabricksExecutor`

**Responsibility**: Execute validated SQL

**Architecture**:
- Connection pooling for performance
- Strict timeout enforcement (2s default)
- Result size limits (1000 rows max)
- Error handling with context

**Features**:
- Automatic reconnection
- Transaction safety
- Timeout at socket level
- Memory-efficient result fetching

**Performance**: ≤2s (enforced)

### 8. Result Summarizer
**File**: `nodes/result_summarizer.py`
**Class**: `ResultSummarizer`

**Responsibility**: Generate natural language summaries

**Architecture**:
- Summarizes results, not raw dumps
- Token-efficient (≤150 tokens)
- Highlights key insights

**Performance**: ~1s

## Performance Optimization Strategies

### 1. Schema Caching
**Problem**: Querying `information_schema` on every request is slow
**Solution**: Load schema once at startup, cache in memory

```python
# At startup
schema_loader = SchemaLoader()
schema_cache = schema_loader.load_from_databricks()

# On every request (fast)
state["schema_cache"] = schema_cache
```

### 2. Lightweight Routing
**Problem**: Heavy models for routing adds latency
**Solution**: Use gpt-4o-mini for supervisor, reserve gpt-4o for generation

```python
SUPERVISOR_MODEL = "gpt-4o-mini"  # Fast, cheap
MAIN_MODEL = "gpt-4o"             # Quality when needed
```

### 3. Connection Pooling
**Problem**: Creating DB connections is expensive
**Solution**: Reuse connections across requests

```python
class DatabricksExecutor:
    def __init__(self):
        self.connection = None  # Reused across calls
```

### 4. Early Short-Circuiting
**Problem**: Running full pipeline when it will fail
**Solution**: Validate early, fail fast

```
Supervisor → [confidence < 0.75] → Fallback (END)
            [no matching tables] → Fallback (END)
            [invalid SQL] → Fallback (END)
```

### 5. Minimal Context
**Problem**: Large prompts = high latency + cost
**Solution**: Truncate history, only send relevant schema

```python
recent_history = history[-5:]  # Only last 5 messages
relevant_tables = [t for t in tables if t in query]  # Only needed tables
```

## Error Handling

### Failure Modes

1. **LLM Failures**: Default to fallback path
2. **Database Connection**: Return error via fallback
3. **Query Timeout**: Caught and reported
4. **Invalid SQL**: Blocked by validator, routed to fallback
5. **No Results**: Handled gracefully in summarizer

### Recovery Strategies

- All errors route to Fallback node
- Fallback explains what went wrong
- User can rephrase and retry
- No crashes, always graceful degradation

## Scalability Considerations

### Horizontal Scaling
- Stateless nodes (can run in parallel)
- Schema cache can be shared (Redis)
- Connection pooling per instance

### Vertical Scaling
- Async LLM calls possible
- Batch processing support
- Result streaming for large datasets

### Production Enhancements
```python
# Add monitoring
from prometheus_client import Counter, Histogram

query_counter = Counter('queries_total', 'Total queries')
latency_histogram = Histogram('query_latency', 'Query latency')

# Add caching
from redis import Redis

redis_client = Redis(host='localhost', port=6379)
cache_key = f"query:{hash(user_input)}"
cached_result = redis_client.get(cache_key)

# Add rate limiting
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@limiter.limit("10/minute")
def query_endpoint():
    ...
```

## Testing Strategy

### Unit Tests
Test individual nodes in isolation:
```python
def test_supervisor_classification():
    node = SupervisorNode()
    state = {"user_input": "Show me customers"}
    result = node(state)
    assert result["intent"] == "databricks"
    assert result["confidence"] > 0.75
```

### Integration Tests
Test complete paths:
```python
def test_databricks_path():
    orchestrator = AIWorkflowOrchestrator(use_mock_schema=True)
    result = orchestrator.query("Show me all customers")
    assert "response" in result
    assert result["path_taken"] == "result_summarizer"
```

### Performance Tests
Validate latency requirements:
```python
def test_latency():
    orchestrator = AIWorkflowOrchestrator()
    start = time.time()
    result = orchestrator.query("What are total sales?")
    elapsed = time.time() - start
    assert elapsed < 5.0  # Must meet SLA
```

## Security Considerations

### SQL Injection Prevention
- All SQL generated by LLM
- Strict validation before execution
- Pattern matching for dangerous operations
- No user input directly in SQL

### Access Control
- Databricks token authentication
- Schema-level access control
- No system table access
- Read-only operations only

### Data Protection
- No sensitive data in logs
- Result size limits
- Query timeouts
- Error messages sanitized

## Monitoring & Observability

### Key Metrics
- Query latency by path
- Intent classification accuracy
- SQL validation failure rate
- Database query execution time
- LLM token usage
- Error rates by node

### Logging
```python
import logging

logger.info(f"Query: {user_input}")
logger.info(f"Intent: {intent}, Confidence: {confidence}")
logger.info(f"Path: {path_taken}, Latency: {latency}s")
logger.error(f"Error in {node}: {error}")
```

### Tracing
- Request ID through entire flow
- Node execution order
- Decision points logged
- State transitions tracked

## Future Enhancements

### Phase 2 Features
1. **Query Caching**: Cache frequent queries
2. **Streaming Results**: Stream large result sets
3. **Multi-table Joins**: Advanced join logic
4. **Natural Language Explanations**: Explain SQL to users
5. **Query Optimization**: Suggest better queries

### Phase 3 Features
1. **Feedback Loop**: Learn from corrections
2. **Custom Functions**: Support UDFs
3. **Visualization**: Auto-generate charts
4. **Scheduled Queries**: Recurring reports
5. **Collaboration**: Share queries between users

## Conclusion

This architecture provides:
- ✅ Sub-5s latency
- ✅ High safety guarantees
- ✅ Clean, maintainable code
- ✅ Production-ready error handling
- ✅ Scalable design
- ✅ Extensible for future needs

The system is ready for production deployment with proper configuration and monitoring.

