"""
SQL Generator - Generates high-precision SQL queries.

Takes the user's query and schema information to generate
safe, optimized SQL that follows strict rules.
"""
from typing import Dict, Any, List
import re
import time
import os
import requests
import json

try:
    from ..state import WorkflowState
    from ..utils import sanitize_sql
    from ..logging_config import get_logger, log_node_entry, log_node_exit
    from ..config import config
except ImportError:
    from state import WorkflowState
    from utils import sanitize_sql
    from logging_config import get_logger, log_node_entry, log_node_exit
    from config import config


# Full schema reference for the LLM
CASINO_SCHEMA = """
TABLES:
1. hr_casino.employees (employee_id, first_name, last_name, department, position, salary, is_active)
2. marketing_casino.customer (customer_id, customer_name, gender, age, region, risk_score)
3. marketing_casino.customer_behaviors (behavior_id, customer_id, problem_gambling_score, risk_level)
4. finance_casino.transactions (transaction_id, customer_id, transaction_amount, status)
5. operations_casino.game_sessions (session_id, customer_id, total_bets, total_wins, net_result)
6. operations_casino.gaming_equipment (equipment_id, equipment_name, status)
7. operations_casino.shifts (shift_id, employee_id, total_revenue)
"""


class SQLGenerator:
    """
    Generates production-ready SQL from natural language queries.
    """
    
    def __init__(self):
        self.logger = get_logger("ai_workflow.sql_generator")
        # Strip any whitespace/newlines from API key
        api_key = config.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY", "")
        self.api_key = api_key.strip() if api_key else ""
    
    def __call__(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Generate SQL from user query.
        """
        log_node_entry(self.logger, "SQLGenerator", state)
        start_time = time.time()
        
        user_input = state.get("user_input", "")
        
        self.logger.info(f"Generating SQL for: '{user_input}'")
        
        # Generate SQL
        sql = self._generate_sql(user_input)
        
        execution_time = time.time() - start_time
        self.logger.info(f"Generated SQL in {execution_time:.3f}s: {sql[:200]}...")
        
        updates = {
            "generated_sql": sql,
            "current_node": "sql_generator"
        }
        
        log_node_exit(self.logger, "SQLGenerator", updates)
        return updates
    
    def _generate_sql(self, user_input: str) -> str:
        """Generate SQL query using OpenAI API via requests."""
        
        system_prompt = f"""You are an SQL generator for PostgreSQL. Generate ONLY the SQL query.

Rules:
1. Use schema.table format (e.g., hr_casino.employees)
2. No SELECT * - list columns
3. Include LIMIT

{CASINO_SCHEMA}"""
        
        try:
            self.logger.info(f"Calling OpenAI API with key: {self.api_key[:15]}...")
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Generate SQL for: {user_input}"}
                    ],
                    "max_tokens": 500,
                    "temperature": 0.3
                },
                timeout=30
            )
            
            self.logger.info(f"OpenAI response status: {response.status_code}")
            
            if response.status_code != 200:
                error_text = response.text
                self.logger.error(f"OpenAI API error: {error_text}")
                return f"-- Error: OpenAI API returned {response.status_code}: {error_text[:200]}"
            
            data = response.json()
            sql = data["choices"][0]["message"]["content"].strip()
            
            self.logger.info(f"OpenAI response: {sql[:100]}...")
            
            # Extract SQL from markdown if present
            sql = self._extract_sql(sql)
            
            # Post-process
            sql = self._post_process_sql(sql)
            
            return sql
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request error: {e}")
            return f"-- Error: Request failed: {str(e)}"
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            self.logger.error(f"Error: {e}\n{error_details}")
            return f"-- Error generating SQL: {type(e).__name__}: {str(e)}"
    
    def _extract_sql(self, text: str) -> str:
        """Extract SQL from response."""
        sql_match = re.search(r'```sql\s*(.*?)\s*```', text, re.DOTALL | re.IGNORECASE)
        if sql_match:
            return sql_match.group(1).strip()
        
        code_match = re.search(r'```\s*(.*?)\s*```', text, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()
        
        return text.strip()
    
    def _post_process_sql(self, sql: str) -> str:
        """Clean SQL."""
        sql = sanitize_sql(sql)
        
        if "LIMIT" not in sql.upper():
            sql = sql.rstrip(";") + " LIMIT 100"
        
        if not sql.endswith(";"):
            sql += ";"
        
        return sql


# Convenience function for LangGraph
def sql_generator_node(state: WorkflowState) -> Dict[str, Any]:
    """LangGraph node function for SQL generation."""
    node = SQLGenerator()
    return node(state)
