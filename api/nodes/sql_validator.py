"""
SQL Validator - Validates generated SQL before execution.

Hard guardrails:
- No DDL/DML operations
- No dangerous patterns
- Query structure validation

Lenient on:
- Table/column existence (let the database handle that)
"""
from typing import Dict, Any, List
import re

try:
    from ..state import WorkflowState
    from ..utils import detect_dangerous_sql_patterns, sanitize_sql
    from ..logging_config import get_logger
except ImportError:
    from state import WorkflowState
    from utils import detect_dangerous_sql_patterns, sanitize_sql
    from logging_config import get_logger


class SQLValidator:
    """
    Validates SQL queries before execution.
    
    Performs validation to prevent:
    - DDL/DML operations
    - SQL injection attempts
    - Malformed queries
    
    LENIENT on table/column checks - let database handle those errors.
    """
    
    def __init__(self):
        self.logger = get_logger("ai_workflow.sql_validator")
    
    def __call__(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Validate the generated SQL query.
        
        Args:
            state: Current workflow state
        
        Returns:
            Updated state with validation results
        """
        sql = state.get("generated_sql", "")
        
        # Log the SQL being validated
        self.logger.info(f"Validating SQL: {sql[:200]}...")
        
        # Perform validation
        validation_result = self._validate_sql(sql)
        
        if validation_result["valid"]:
            self.logger.info("✓ SQL validation passed")
        else:
            self.logger.warning(f"✗ SQL validation failed: {validation_result['errors']}")
        
        return {
            "validation_result": validation_result,
            "current_node": "sql_validator"
        }
    
    def _validate_sql(self, sql: str) -> Dict[str, Any]:
        """
        SQL validation focusing on safety, not schema accuracy.
        
        Returns:
            {
                "valid": bool,
                "errors": List[str],
                "warnings": List[str]
            }
        """
        errors = []
        warnings = []
        
        # Check for empty SQL
        if not sql or sql.strip() == "" or sql.startswith("-- Error"):
            errors.append("Empty or error SQL query")
            return {"valid": False, "errors": errors, "warnings": warnings}
        
        # Check for dangerous patterns
        dangerous = detect_dangerous_sql_patterns(sql)
        if dangerous:
            errors.extend(dangerous)
        
        # Ensure it's a SELECT query
        sql_upper = sql.upper().strip()
        if not sql_upper.startswith("SELECT"):
            errors.append("Only SELECT queries are allowed")
        
        # Check for LIMIT clause (warning only)
        if "LIMIT" not in sql_upper:
            warnings.append("No LIMIT clause found")
        
        # Check for SELECT * (error)
        if re.search(r'\bSELECT\s+\*\s+FROM', sql_upper):
            errors.append("SELECT * is not allowed - specify explicit columns")
        
        # Check for multiple statements (error)
        semicolon_count = sql.count(";")
        if semicolon_count > 1:
            errors.append("Multiple SQL statements not allowed")
        
        # Check for GROUP BY / HAVING issues
        if "GROUP BY" in sql_upper and "HAVING" in sql_upper:
            group_by_match = re.search(r'\bGROUP\s+BY\s+(.+?)(?:\s+HAVING|\s+ORDER|\s+LIMIT|$)', sql_upper, re.IGNORECASE | re.DOTALL)
            having_match = re.search(r'\bHAVING\s+(.+?)(?:\s+ORDER|\s+LIMIT|$)', sql_upper, re.IGNORECASE | re.DOTALL)
            
            if group_by_match and having_match:
                group_by_cols = group_by_match.group(1).strip()
                having_clause = having_match.group(1).strip()
                
                # Extract column references from HAVING that are not aggregate functions
                # Pattern: table.column or column (but not inside SUM(...), COUNT(...), etc.)
                # Note: Can't use variable-width lookbehind, so we'll use a simpler approach
                # Just check for common non-aggregated column patterns
                non_aggregate_cols = []
                # Look for patterns like: table.column = value or table.column > value
                col_pattern = r'\b([a-z_]+\.)?(risk_level|age|gender|status|is_active|participation)\b'
                matches = re.finditer(col_pattern, having_clause, re.IGNORECASE)
                for match in matches:
                    # Check if it's not inside an aggregate function by looking backwards
                    before = having_clause[:match.start()]
                    if not re.search(r'\b(SUM|COUNT|AVG|MAX|MIN|CAST)\s*\([^)]*$', before, re.IGNORECASE):
                        non_aggregate_cols.append(match.group(0))
                
                # Check if any non-aggregate columns in HAVING are not in GROUP BY
                for col_match in non_aggregate_cols:
                    col = col_match[0] if col_match[0] else ""
                    col_name = col_match[1] if len(col_match) > 1 else ""
                    if col_name:
                        full_col = (col + col_name).lower()
                        # Check if this column is in GROUP BY
                        if full_col not in group_by_cols.lower() and col_name.lower() not in ['and', 'or', 'not', 'in', 'between', 'like', 'is', 'null']:
                            # This might be an error, but be lenient - check if it's a common filter column
                            common_filter_cols = ['risk_level', 'age', 'gender', 'participation', 'status', 'is_active']
                            if any(filter_col in col_name.lower() for filter_col in common_filter_cols):
                                errors.append(
                                    f"Column '{col_name}' in HAVING clause should be in WHERE clause or GROUP BY. "
                                    f"Non-aggregated columns (like risk_level, age, participation flags) must be filtered in WHERE, not HAVING."
                                )
                                break
        
        # NOTE: We do NOT validate table/column existence here
        # Let the database return meaningful errors instead
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }


# Convenience function for LangGraph
def sql_validator_node(state: WorkflowState) -> Dict[str, Any]:
    """LangGraph node function for SQL validation."""
    node = SQLValidator()
    return node(state)
