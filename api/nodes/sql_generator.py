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


# Complete schema reference for the LLM
CASINO_SCHEMA = """
COMPLETE DATABASE SCHEMA:

1. hr_casino.employees
   Columns:
   - employee_id (INTEGER) - Primary key
   - first_name, last_name (VARCHAR) - Employee name
   - department (VARCHAR) - finance/marketing/operations/security
   - position (VARCHAR) - Job title
   - hire_date (DATE) - When hired
   - salary (DECIMAL) - Annual salary
   - is_active (INTEGER) - 1 = active, 0 = inactive

2. marketing_casino.customer
   Columns:
   - customer_id (TEXT/VARCHAR) - Primary key
   - customer_name (VARCHAR) - Full name
   - gender (TEXT) - Male/Female
   - age (REAL) - Age in years
   - region (TEXT) - North, Center, Lisbon, Alentejo, Algarve, Azores, Madeira
   - marital_status (TEXT) - Single, Married, Divorced, Widowed
   - employment_status (TEXT) - Employee, Self-employed, Unemployed, Student, Other
   - education_level (TEXT) - Primary, Secondary, Bachelor, Master, PhD
   - registration_date (TIMESTAMP) - When registered
   - risk_score (BIGINT) - Risk score 0-100

3. marketing_casino.customer_behaviors
   Columns:
   - behavior_id (BIGINT) - Primary key
   - customer_id (TEXT) - Foreign key to customer
   - ever_bet_money (BIGINT) - 1 = yes, 0 = no
   - offline_gambling_participation (BIGINT) - 1 = participated, 0 = not
   - online_gambling_participation (BIGINT) - 1 = participated, 0 = not
   - monthly_gambling_expenditure_offline (REAL) - Monthly offline spending
   - monthly_gambling_expenditure_online (REAL) - Monthly online spending
   - problem_gambling_score (REAL) - Problem gambling score
   - risk_level (TEXT) - 'low', 'medium', or 'high'

4. finance_casino.transactions
   Columns:
   - transaction_id (INTEGER) - Primary key
   - customer_id (VARCHAR) - Foreign key to customer
   - req_time_utc (TIMESTAMP) - Transaction time
   - transaction_type (VARCHAR) - Type of transaction
   - transaction_amount (TEXT) - MUST CAST to DECIMAL before math operations
   - status (VARCHAR) - 'APPROVED' or 'DECLINED'
   - direction (VARCHAR) - 'IN' or 'OUT'

5. operations_casino.game_sessions
   Columns:
   - session_id (INTEGER) - Primary key
   - game_id (INTEGER) - Game type
   - customer_id (VARCHAR) - Foreign key to customer
   - session_start_time (TIMESTAMP) - When session started
   - total_bets (DECIMAL) - Total bets placed
   - total_wins (DECIMAL) - Total wins
   - net_result (DECIMAL) - total_wins - total_bets (negative = loss, positive = win)
   - session_duration_minutes (INTEGER) - Duration in minutes

6. operations_casino.gaming_equipment
   Columns:
   - equipment_id (INTEGER) - Primary key
   - equipment_name (VARCHAR) - Equipment name
   - equipment_type (VARCHAR) - table/machine/terminal
   - status (VARCHAR) - active/maintenance/inactive
   - hourly_revenue (DECIMAL) - Average hourly revenue

7. operations_casino.shifts
   Columns:
   - shift_id (INTEGER) - Primary key
   - employee_id (INTEGER) - Foreign key to employees
   - equipment_id (INTEGER) - Foreign key to gaming_equipment
   - shift_start (TIMESTAMP) - Shift start time
   - total_revenue (DECIMAL) - Revenue during shift
   - total_transactions (INTEGER) - Number of transactions

CRITICAL RULES:
- transaction_amount is TEXT - ALWAYS use CAST(transaction_amount AS DECIMAL) before SUM/AVG/MAX/MIN
- net_result is DECIMAL - negative values = losses, positive = wins
- monthly_gambling_expenditure columns are REAL - NO CAST needed
- risk_level values: 'low', 'medium', 'high' (use single quotes)
- participation columns: 1 = yes, 0 = no
- NEVER nest aggregations like AVG(SUM(...)) - this is INVALID SQL
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
        
        system_prompt = f"""You are an expert PostgreSQL SQL generator. Generate ONLY the SQL query, nothing else.

ABSOLUTE RULES:
1. Use schema.table format: hr_casino.employees, marketing_casino.customer, etc.
2. NO SELECT * - always list explicit columns
3. ALWAYS include LIMIT (default 100, max 1000)
4. transaction_amount is TEXT - MUST use: CAST(transaction_amount AS DECIMAL) before any math
5. NEVER nest aggregations: AVG(SUM(...)) is INVALID! Use AVG directly on values
6. CRITICAL: WHERE vs HAVING:
   - WHERE: Use for filtering individual rows (age, risk_level, participation flags, etc.)
   - HAVING: Use ONLY for filtering aggregated results (SUM(...) > X, COUNT(...) >= Y, etc.)
   - NEVER put non-aggregated columns in HAVING unless they're in GROUP BY
   - Example: "risk_level = 'high'" goes in WHERE, NOT HAVING
7. For multiple WHERE conditions, use AND/OR properly

{CASINO_SCHEMA}

QUERY PATTERNS AND EXAMPLES:

Pattern 1: Simple queries
"Show me 5 employees" →
SELECT employee_id, first_name, last_name, department, position, salary
FROM hr_casino.employees
LIMIT 5;

Pattern 2: Aggregations with HAVING
"Find customers with transactions > $10,000" →
SELECT c.customer_name, SUM(CAST(t.transaction_amount AS DECIMAL)) AS total_transactions
FROM marketing_casino.customer c
JOIN finance_casino.transactions t ON c.customer_id = t.customer_id
GROUP BY c.customer_name
HAVING SUM(CAST(t.transaction_amount AS DECIMAL)) > 10000
ORDER BY total_transactions DESC
LIMIT 100;

Pattern 3: Multiple conditions with aggregations
"Find high-risk customers with transactions > $10,000 and losses > $5,000" →
SELECT c.customer_name, c.region, cb.problem_gambling_score,
       SUM(CAST(t.transaction_amount AS DECIMAL)) AS total_transaction_amount,
       SUM(gs.net_result) AS total_net_losses
   FROM marketing_casino.customer c
   JOIN marketing_casino.customer_behaviors cb ON c.customer_id = cb.customer_id
JOIN finance_casino.transactions t ON c.customer_id = t.customer_id
JOIN operations_casino.game_sessions gs ON c.customer_id = gs.customer_id
   WHERE cb.risk_level = 'high'
GROUP BY c.customer_name, c.region, cb.problem_gambling_score
HAVING SUM(CAST(t.transaction_amount AS DECIMAL)) > 10000 
   AND SUM(gs.net_result) < -5000
ORDER BY total_net_losses DESC
   LIMIT 100;

Pattern 4: Average calculations with WHERE filters (NO nested aggregations!)
"Top regions by average monthly gambling expenditure for customers 25-35 with both online and offline" →
SELECT c.region,
       AVG(cb.monthly_gambling_expenditure_offline + cb.monthly_gambling_expenditure_online) AS average_expenditure,
       COUNT(DISTINCT c.customer_id) AS customer_count
FROM marketing_casino.customer c
JOIN marketing_casino.customer_behaviors cb ON c.customer_id = cb.customer_id
WHERE c.age BETWEEN 25 AND 35
  AND cb.online_gambling_participation = 1
  AND cb.offline_gambling_participation = 1
GROUP BY c.region
ORDER BY average_expenditure DESC
LIMIT 5;

Pattern 4b: WHERE for non-aggregated filters, HAVING for aggregated filters
"Top 3 regions where customers aged 20-30 have highest average monthly gambling expenditure (online + offline), 
with both online/offline participation, at least 5 transactions, and risk_level = 'high'" →
SELECT c.region,
       AVG(cb.monthly_gambling_expenditure_offline + cb.monthly_gambling_expenditure_online) AS average_expenditure,
       COUNT(DISTINCT c.customer_id) AS customer_count,
       AVG(cb.problem_gambling_score) AS average_problem_gambling_score
FROM marketing_casino.customer c
JOIN marketing_casino.customer_behaviors cb ON c.customer_id = cb.customer_id
JOIN finance_casino.transactions t ON c.customer_id = t.customer_id
WHERE c.age BETWEEN 20 AND 30
  AND cb.online_gambling_participation = 1
  AND cb.offline_gambling_participation = 1
  AND cb.risk_level = 'high'
GROUP BY c.region
HAVING COUNT(t.transaction_id) >= 5
ORDER BY average_expenditure DESC
LIMIT 3;

IMPORTANT COLUMN NOTES:
- For "average monthly gambling expenditure" use: AVG(cb.monthly_gambling_expenditure_offline + cb.monthly_gambling_expenditure_online)
- NEVER use "total_expenditure" - this column does NOT exist
- NEVER use "ft.total_expenditure" - this column does NOT exist  
- Monthly expenditure columns are in customer_behaviors table (cb), NOT in transactions table (ft/t)
- The finance_casino.transactions table has: transaction_id, customer_id, transaction_amount, status, direction
- Use COUNT(t.transaction_id) >= N for "at least N transactions"

Pattern 5: Time-based filtering
"Employees with highest revenue per shift in last month" →
SELECT e.employee_id, e.first_name, e.last_name,
       AVG(s.total_revenue) AS avg_revenue_per_shift,
       COUNT(s.shift_id) AS total_shifts
   FROM hr_casino.employees e
   JOIN operations_casino.shifts s ON e.employee_id = s.employee_id
WHERE s.shift_start >= CURRENT_DATE - INTERVAL '1 month'
   GROUP BY e.employee_id, e.first_name, e.last_name
   ORDER BY avg_revenue_per_shift DESC
   LIMIT 10;

KEY MAPPINGS:
- "high-risk" = risk_level = 'high' OR risk_score > 70
- "participated in both online and offline" = online_gambling_participation = 1 AND offline_gambling_participation = 1
- "aged X-Y" = age BETWEEN X AND Y
- "lost more than $X" = net_result < -X (net_result is already negative for losses)
- "totaling more than $X" = SUM(CAST(transaction_amount AS DECIMAL)) > X
- "average monthly expenditure" = AVG(monthly_gambling_expenditure_offline + monthly_gambling_expenditure_online)
- "top N" = ORDER BY ... DESC LIMIT N
- "per X" = GROUP BY X

CRITICAL RULES FOR WHERE vs HAVING:
- WHERE clause: Filter individual rows BEFORE grouping
  - Use for: age, risk_level, participation flags, status, etc.
  - Example: WHERE cb.risk_level = 'high' AND c.age BETWEEN 20 AND 30
- HAVING clause: Filter aggregated results AFTER grouping
  - Use ONLY for: SUM(...) > X, COUNT(...) >= Y, AVG(...) > Z
  - Example: HAVING SUM(CAST(t.transaction_amount AS DECIMAL)) > 15000
- NEVER put non-aggregated columns in HAVING unless they're also in GROUP BY
- If you need to filter by risk_level, age, participation, etc., use WHERE, NOT HAVING!

OTHER CRITICAL RULES:
- NEVER use AVG(SUM(...)) - this is INVALID SQL
- Always CAST transaction_amount to DECIMAL before SUM/AVG
- monthly_gambling_expenditure columns are REAL - no CAST needed
- Use proper JOIN syntax with table aliases

Generate the SQL query now:"""
        
        try:
            self.logger.info(f"Calling OpenAI API...")
            
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
                    "max_tokens": 600,
                    "temperature": 0.2
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
            
            self.logger.info(f"OpenAI response: {sql[:150]}...")
            
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
        """Clean and validate SQL, fixing common issues."""
        sql = sanitize_sql(sql)
        
        # Fix common issues
        # Remove nested aggregations if present
        if re.search(r'AVG\s*\(\s*SUM\s*\(', sql, re.IGNORECASE):
            self.logger.warning("Detected invalid nested aggregation AVG(SUM(...)), attempting to fix...")
            sql = re.sub(r'AVG\s*\(\s*SUM\s*\(([^)]+)\)\s*\)', r'AVG(\1)', sql, flags=re.IGNORECASE)
        
        # Fix: Move non-aggregated column filters from HAVING to WHERE
        # This prevents "column must appear in GROUP BY" errors
        sql_before = sql
        sql = self._fix_having_clause(sql)
        if sql != sql_before:
            self.logger.info(f"✅ Fixed HAVING clause issue")
        
        # Ensure LIMIT clause exists
        if "LIMIT" not in sql.upper():
            sql = sql.rstrip(";") + " LIMIT 100"
        
        # Ensure it ends with semicolon
        if not sql.endswith(";"):
            sql += ";"
        
        return sql
    
    def _fix_having_clause(self, sql: str) -> str:
        """
        Fix HAVING clause by moving non-aggregated column filters to WHERE.
        
        Detects patterns like:
        - HAVING ... AND cb.risk_level = 'high' (should be in WHERE)
        - HAVING ... AND c.age BETWEEN X AND Y (should be in WHERE)
        """
        sql_upper = sql.upper()
        
        # Only process if there's a HAVING clause
        if "HAVING" not in sql_upper:
            return sql
        
        having_match = re.search(r'\bHAVING\b', sql_upper)
        if not having_match:
            return sql
        
        # Find WHERE and GROUP BY positions
        where_match = re.search(r'\bWHERE\b', sql_upper)
        group_by_match = re.search(r'\bGROUP\s+BY\b', sql_upper)
        
        if not where_match or not group_by_match:
            return sql
        
        # Extract HAVING clause content
        having_start = having_match.end()
        having_content = sql[having_start:]
        
        # Find where HAVING clause ends
        order_by_match = re.search(r'\bORDER\s+BY\b', having_content, re.IGNORECASE)
        limit_match = re.search(r'\bLIMIT\b', having_content, re.IGNORECASE)
        if order_by_match:
            having_end = having_start + order_by_match.start()
        elif limit_match:
            having_end = having_start + limit_match.start()
        else:
            having_end = len(sql.rstrip(';'))
        
        having_clause = sql[having_start:having_end].strip()
        
        # Patterns to find and move to WHERE
        patterns_to_move = [
            (r'\s+AND\s+(\w+\.risk_level\s*=\s*[\'"][^\'"]+[\'"])', 'risk_level'),
            (r'\s+AND\s+(\w+\.age\s+BETWEEN\s+\d+\s+AND\s+\d+)', 'age'),
            (r'\s+AND\s+(\w+\.(online|offline)_gambling_participation\s*=\s*\d+)', 'participation'),
        ]
        
        moved_conditions = []
        
        for pattern, condition_type in patterns_to_move:
            match = re.search(pattern, having_clause, re.IGNORECASE)
            if match:
                condition = match.group(1)
                # Check it's not inside an aggregate function
                before = having_clause[:match.start()]
                if not re.search(r'\b(SUM|COUNT|AVG|MAX|MIN)\s*\([^)]*$', before, re.IGNORECASE):
                    moved_conditions.append((condition, match.start(), match.end()))
                    self.logger.warning(f"🔧 Found {condition_type} condition in HAVING: {condition}")
        
        # Remove conditions from HAVING (in reverse order to preserve indices)
        if moved_conditions:
            new_having = having_clause
            for condition, start, end in reversed(moved_conditions):
                # Remove the condition and its leading AND
                new_having = new_having[:start] + new_having[end:].strip()
                # Clean up any double AND/OR
                new_having = re.sub(r'\s+AND\s+AND\s+', ' AND ', new_having, flags=re.IGNORECASE)
                new_having = re.sub(r'^\s+AND\s+', '', new_having, flags=re.IGNORECASE)
            
            # Reconstruct SQL with fixed HAVING
            sql = sql[:having_start] + new_having + sql[having_end:]
            
            # Add conditions to WHERE
            where_end_pos = group_by_match.start()
            conditions_str = " AND ".join([cond for cond, _, _ in moved_conditions])
            sql = sql[:where_end_pos].rstrip() + f" AND {conditions_str} " + sql[where_end_pos:]
            self.logger.warning(f"✅ Moved {len(moved_conditions)} condition(s) from HAVING to WHERE")
            return sql
        
        # No conditions to move, return original SQL
        return sql


# Convenience function for LangGraph
def sql_generator_node(state: WorkflowState) -> Dict[str, Any]:
    """LangGraph node function for SQL generation."""
    node = SQLGenerator()
    return node(state)
