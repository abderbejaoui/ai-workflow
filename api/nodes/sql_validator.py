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
