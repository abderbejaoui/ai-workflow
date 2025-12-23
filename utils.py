"""
Utility functions for the AI workflow system.
Includes LLM helpers, formatting, and common operations.
"""
from typing import List, Dict, Optional
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from config import config
import json
import re


def get_supervisor_llm():
    """
    Get a lightweight, fast LLM for the supervisor node.
    Uses gpt-4o-mini by default for speed and cost efficiency.
    """
    return ChatOpenAI(
        model=config.SUPERVISOR_MODEL,
        temperature=config.SUPERVISOR_TEMPERATURE,
        max_tokens=config.SUPERVISOR_MAX_TOKENS,
        api_key=config.OPENAI_API_KEY,
    )


def get_main_llm():
    """
    Get the main LLM for conversation and complex tasks.
    Uses gpt-4o or Claude for better quality.
    """
    if config.OPENAI_API_KEY:
        return ChatOpenAI(
            model=config.MAIN_MODEL,
            temperature=config.MAIN_TEMPERATURE,
            max_tokens=config.MAIN_MAX_TOKENS,
            api_key=config.OPENAI_API_KEY,
        )
    elif config.ANTHROPIC_API_KEY:
        return ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            temperature=config.MAIN_TEMPERATURE,
            max_tokens=config.MAIN_MAX_TOKENS,
            api_key=config.ANTHROPIC_API_KEY,
        )
    else:
        raise ValueError("No LLM API key configured")


def format_conversation_history(
    history: List[Dict[str, str]], 
    limit: Optional[int] = None
) -> List:
    """
    Format conversation history for LLM context.
    
    Args:
        history: List of message dicts with 'role' and 'content'
        limit: Optional limit on number of messages (keeps most recent)
    
    Returns:
        List of LangChain message objects
    """
    if limit:
        history = history[-limit:]
    
    messages = []
    for msg in history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
    
    return messages


def truncate_history(
    history: List[Dict[str, str]], 
    max_messages: int = None
) -> List[Dict[str, str]]:
    """
    Truncate conversation history to most recent N messages.
    Keeps context minimal for performance.
    """
    if max_messages is None:
        max_messages = config.CONVERSATION_HISTORY_LIMIT
    
    return history[-max_messages:] if len(history) > max_messages else history


def extract_json_from_text(text: str) -> Optional[Dict]:
    """
    Extract JSON from LLM response that might contain markdown or extra text.
    Handles ```json``` blocks and raw JSON.
    """
    # Try to find JSON in code blocks first
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Try to find raw JSON
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass
    
    return None


def format_schema_for_prompt(tables: List[Dict[str, any]], max_tables: int = 10) -> str:
    """
    Format schema metadata for inclusion in prompts.
    Keep it concise to minimize token usage.
    """
    lines = []
    for i, table in enumerate(tables[:max_tables]):
        full_name = table.get('full_name', table.get('table', 'unknown'))
        columns = table.get('columns', [])
        
        # Show first 8 columns to keep prompt small
        col_preview = ', '.join(columns[:8])
        if len(columns) > 8:
            col_preview += f", ... ({len(columns)} total)"
        
        lines.append(f"- {full_name}: [{col_preview}]")
    
    if len(tables) > max_tables:
        lines.append(f"... and {len(tables) - max_tables} more tables")
    
    return "\n".join(lines)


def sanitize_sql(sql: str) -> str:
    """
    Basic SQL sanitization - remove comments and normalize whitespace.
    """
    # Remove single-line comments
    sql = re.sub(r'--[^\n]*', '', sql)
    # Remove multi-line comments
    sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
    # Normalize whitespace
    sql = ' '.join(sql.split())
    return sql.strip()


def format_query_result(
    results: List[Dict[str, any]], 
    max_rows: int = 10
) -> str:
    """
    Format query results for display or summarization.
    Truncates to avoid token bloat.
    """
    if not results:
        return "No results returned."
    
    num_rows = len(results)
    display_rows = results[:max_rows]
    
    # Get column names
    columns = list(display_rows[0].keys()) if display_rows else []
    
    # Format as simple table
    lines = [f"Columns: {', '.join(columns)}"]
    lines.append(f"Rows: {num_rows}")
    lines.append("")
    
    for row in display_rows:
        row_str = " | ".join(str(v) for v in row.values())
        lines.append(row_str)
    
    if num_rows > max_rows:
        lines.append(f"... ({num_rows - max_rows} more rows)")
    
    return "\n".join(lines)


def detect_dangerous_sql_patterns(sql: str) -> List[str]:
    """
    Detect dangerous SQL patterns that should be blocked.
    
    Returns:
        List of issues found (empty if safe)
    """
    issues = []
    sql_upper = sql.upper()
    
    # Check for DDL operations
    ddl_keywords = ['DROP', 'CREATE', 'ALTER', 'TRUNCATE', 'DELETE', 'INSERT', 'UPDATE']
    for keyword in ddl_keywords:
        if re.search(rf'\b{keyword}\b', sql_upper):
            issues.append(f"Dangerous operation detected: {keyword}")
    
    # Check for system tables/functions
    if 'INFORMATION_SCHEMA' in sql_upper:
        issues.append("Access to INFORMATION_SCHEMA not allowed")
    
    # Check for multiple statements
    if sql.count(';') > 1:
        issues.append("Multiple SQL statements not allowed")
    
    return issues

