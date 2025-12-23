"""
SQL Generator - Generates high-precision SQL queries.

Takes the user's query and schema information to generate
safe, optimized SQL that follows strict rules.
"""
from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage
from state import WorkflowState
from utils import get_main_llm, extract_json_from_text, sanitize_sql
from logging_config import get_logger, log_node_entry, log_node_exit, log_llm_call
import re
import time


class SQLGenerator:
    """
    Generates production-ready SQL from natural language queries.
    
    Enforces strict rules:
    - No SELECT *
    - Explicit column names
    - LIMIT enforced
    - Fully qualified table names
    """
    
    def __init__(self):
        self.llm = get_main_llm()
        self.logger = get_logger("ai_workflow.sql_generator")
    
    def __call__(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Generate SQL from user query and feasibility check.
        
        Args:
            state: Current workflow state
        
        Returns:
            Updated state with generated SQL
        """
        log_node_entry(self.logger, "SQLGenerator", state)
        start_time = time.time()
        
        user_input = state.get("user_input", "")
        feasibility_check = state.get("feasibility_check", {})
        schema_cache = state.get("schema_cache", {})
        
        candidate_tables = feasibility_check.get("tables", [])
        self.logger.info(f"Generating SQL for query: '{user_input[:100]}...'")
        self.logger.debug(f"Candidate tables: {candidate_tables}")
        
        # Generate SQL
        sql = self._generate_sql(user_input, feasibility_check, schema_cache)
        
        execution_time = time.time() - start_time
        self.logger.info(
            f"SQL generated in {execution_time:.3f}s",
            extra={
                'sql': sql[:200],
                'execution_time': execution_time
            }
        )
        self.logger.debug(f"Full SQL: {sql}")
        
        updates = {
            "generated_sql": sql,
            "current_node": "sql_generator"
        }
        
        log_node_exit(self.logger, "SQLGenerator", updates)
        return updates
    
    def _generate_sql(
        self,
        user_input: str,
        feasibility_check: Dict[str, Any],
        schema_cache: Dict[str, Any]
    ) -> str:
        """Generate SQL query using LLM."""
        
        # Extract relevant schema information
        candidate_tables = feasibility_check.get("tables", [])
        schema_subset = self._get_relevant_schema(candidate_tables, schema_cache)
        
        system_prompt = """You are an expert SQL generator for Databricks.

Generate a SQL query following these STRICT rules:

1. NO SELECT * - Always specify explicit column names
2. Use fully qualified table names (catalog.schema.table)
3. ALWAYS include LIMIT clause (default 100, max 1000)
4. Use proper JOIN syntax if multiple tables
5. Add WHERE clauses for filtering
6. Only read operations (SELECT) - no DDL/DML

Output format:
```sql
SELECT column1, column2
FROM catalog.schema.table
WHERE condition
LIMIT 100
```

Return ONLY the SQL query, nothing else."""
        
        user_message = f"""Schema:
{schema_subset}

User request: {user_input}

Generate the SQL query."""
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_message)
            ]
            
            log_llm_call(self.logger, "gpt-4o (SQL generation)")
            response = self.llm.invoke(messages)
            sql = self._extract_sql(response.content)
            
            # Post-process SQL
            sql = self._post_process_sql(sql)
            
            return sql
            
        except Exception as e:
            return f"-- Error generating SQL: {str(e)}"
    
    def _get_relevant_schema(
        self,
        table_names: List[str],
        schema_cache: Dict[str, Any]
    ) -> str:
        """Extract schema info for relevant tables only."""
        if not schema_cache or "tables" not in schema_cache:
            return "No schema available"
        
        all_tables = schema_cache["tables"]
        relevant_tables = []
        
        for table_name in table_names:
            for table in all_tables:
                if (table_name.lower() in table.get("table", "").lower() or
                    table_name.lower() in table.get("full_name", "").lower()):
                    relevant_tables.append(table)
                    break
        
        # Format schema info
        lines = []
        for table in relevant_tables:
            full_name = table.get("full_name", table.get("table", ""))
            columns = table.get("columns", [])
            col_types = table.get("column_types", {})
            
            lines.append(f"\nTable: {full_name}")
            lines.append("Columns:")
            
            for col in columns:
                col_type = col_types.get(col, "unknown")
                lines.append(f"  - {col} ({col_type})")
        
        return "\n".join(lines) if lines else "No matching tables found"
    
    def _extract_sql(self, text: str) -> str:
        """Extract SQL from LLM response."""
        # Try to find SQL in code blocks
        sql_match = re.search(r'```sql\s*(.*?)\s*```', text, re.DOTALL | re.IGNORECASE)
        if sql_match:
            return sql_match.group(1).strip()
        
        # Try to find SQL in generic code blocks
        code_match = re.search(r'```\s*(.*?)\s*```', text, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()
        
        # If no code block, assume entire response is SQL
        return text.strip()
    
    def _post_process_sql(self, sql: str) -> str:
        """Clean and validate generated SQL."""
        # Sanitize
        sql = sanitize_sql(sql)
        
        # Ensure LIMIT clause exists
        if "LIMIT" not in sql.upper():
            sql = sql.rstrip(";") + " LIMIT 100"
        
        # Ensure it ends with semicolon
        if not sql.endswith(";"):
            sql += ";"
        
        return sql


# Convenience function for LangGraph
def sql_generator_node(state: WorkflowState) -> Dict[str, Any]:
    """LangGraph node function for SQL generation."""
    node = SQLGenerator()
    return node(state)

