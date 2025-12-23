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
        self.logger.info(f"Generated SQL: {sql}")
        
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
        
        system_prompt = """You are an expert SQL generator for PostgreSQL/Supabase specializing in analytical queries.

Generate a SQL query following these STRICT rules:

1. NO SELECT * - Always specify explicit column names
2. Use FULLY QUALIFIED table names (schema.table_name format):
   - hr_casino.employees for employee data
   - marketing_casino.customer for customer data (NOTE: singular 'customer' not 'customers')
   - marketing_casino.customer_behaviors for customer behavior data
   - operations_casino.game_sessions for game session data
   - operations_casino.gaming_equipment for gaming equipment data
   - operations_casino.shifts for shift data
   - finance_casino.transactions for transaction data
3. ALWAYS include LIMIT clause (default 100, max 1000)
4. Use proper JOIN syntax if multiple tables
5. Add WHERE clauses for filtering
6. Only read operations (SELECT) - no DDL/DML

CRITICAL - Understand query intent:
- "per X" or "average per X" → Use GROUP BY and AVG() or SUM()/COUNT()
- "highest/lowest/top/bottom" → Use ORDER BY with proper aggregation
- "total" → Use SUM()
- "count" or "number of" → Use COUNT()
- "each X" → Use GROUP BY X
- Time periods ("last month", "last year") → Use WHERE with date comparisons

COMMON QUERY MAPPINGS:
- "high-risk customers" → WHERE risk_level = 'high' (from customer_behaviors) OR risk_score > 70 (from customer)
- "problem gambling" → problem_gambling_score from customer_behaviors
- transaction_amount is TEXT, use CAST(transaction_amount AS DECIMAL)

EXAMPLES:

Q: "Show high-risk customers"
A: SELECT c.customer_id, c.customer_name, c.risk_score, cb.risk_level, cb.problem_gambling_score
   FROM marketing_casino.customer c
   JOIN marketing_casino.customer_behaviors cb ON c.customer_id = cb.customer_id
   WHERE cb.risk_level = 'high'
   ORDER BY cb.problem_gambling_score DESC
   LIMIT 100;

Q: "Which employees generated the highest revenue per shift?"
A: SELECT e.employee_id, e.first_name, e.last_name, 
          COUNT(s.shift_id) as total_shifts,
          AVG(s.total_revenue) as avg_revenue_per_shift
   FROM hr_casino.employees e
   JOIN operations_casino.shifts s ON e.employee_id = s.employee_id
   GROUP BY e.employee_id, e.first_name, e.last_name
   ORDER BY avg_revenue_per_shift DESC
   LIMIT 10;

Q: "How many customers from each region?"
A: SELECT region, COUNT(customer_id) as customer_count
   FROM marketing_casino.customer
   GROUP BY region
   ORDER BY customer_count DESC
   LIMIT 100;

Q: "Total transactions per customer"
A: SELECT customer_id, COUNT(transaction_id) as total_transactions, 
          SUM(CAST(transaction_amount AS DECIMAL)) as total_amount
   FROM finance_casino.transactions
   GROUP BY customer_id
   ORDER BY total_amount DESC
   LIMIT 100;

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

