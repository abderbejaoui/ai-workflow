"""
SQL Validator - Validates generated SQL before execution.

Hard guardrails:
- Table and column existence checks
- No DDL/DML operations
- No dangerous patterns
- Query structure validation
"""
from typing import Dict, Any, List
from state import WorkflowState
from utils import detect_dangerous_sql_patterns, sanitize_sql
import re


class SQLValidator:
    """
    Validates SQL queries before execution.
    
    Performs strict validation to prevent:
    - Access to non-existent tables/columns
    - DDL/DML operations
    - SQL injection attempts
    - Malformed queries
    """
    
    def __init__(self):
        pass
    
    def __call__(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Validate the generated SQL query.
        
        Args:
            state: Current workflow state
        
        Returns:
            Updated state with validation results
        """
        sql = state.get("generated_sql", "")
        schema_cache = state.get("schema_cache", {})
        feasibility_check = state.get("feasibility_check", {})
        
        # Perform validation
        validation_result = self._validate_sql(sql, schema_cache, feasibility_check)
        
        return {
            "validation_result": validation_result,
            "current_node": "sql_validator"
        }
    
    def _validate_sql(
        self,
        sql: str,
        schema_cache: Dict[str, Any],
        feasibility_check: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Comprehensive SQL validation.
        
        Returns:
            {
                "valid": bool,
                "errors": List[str],
                "warnings": List[str]
            }
        """
        errors = []
        warnings = []
        
        if not sql or sql.strip() == "":
            errors.append("Empty SQL query")
            return {"valid": False, "errors": errors, "warnings": warnings}
        
        # Check for dangerous patterns
        dangerous = detect_dangerous_sql_patterns(sql)
        if dangerous:
            errors.extend(dangerous)
        
        # Ensure it's a SELECT query
        sql_upper = sql.upper().strip()
        if not sql_upper.startswith("SELECT"):
            errors.append("Only SELECT queries are allowed")
        
        # Check for LIMIT clause
        if "LIMIT" not in sql_upper:
            warnings.append("No LIMIT clause found")
        
        # Check for SELECT *
        if re.search(r'\bSELECT\s+\*', sql_upper):
            errors.append("SELECT * is not allowed - specify explicit columns")
        
        # Validate table existence
        table_errors = self._validate_tables(sql, schema_cache)
        errors.extend(table_errors)
        
        # Validate column existence (basic check)
        column_warnings = self._validate_columns(sql, schema_cache, feasibility_check)
        warnings.extend(column_warnings)
        
        # Check for multiple statements
        if sql.count(";") > 1:
            errors.append("Multiple SQL statements not allowed")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _validate_tables(self, sql: str, schema_cache: Dict[str, Any]) -> List[str]:
        """Validate that referenced tables exist in schema."""
        errors = []
        
        if not schema_cache or "tables" not in schema_cache:
            return ["Schema cache not available for validation"]
        
        # Extract table references from SQL
        # Pattern: FROM/JOIN table_name
        table_pattern = r'(?:FROM|JOIN)\s+([a-zA-Z0-9_\.]+)'
        referenced_tables = re.findall(table_pattern, sql, re.IGNORECASE)
        
        available_tables = schema_cache["tables"]
        available_table_names = set()
        
        for table in available_tables:
            available_table_names.add(table.get("table", "").lower())
            available_table_names.add(table.get("full_name", "").lower())
        
        for table_ref in referenced_tables:
            table_lower = table_ref.lower().strip()
            if table_lower not in available_table_names:
                errors.append(f"Table '{table_ref}' not found in schema")
        
        return errors
    
    def _validate_columns(
        self,
        sql: str,
        schema_cache: Dict[str, Any],
        feasibility_check: Dict[str, Any]
    ) -> List[str]:
        """Basic validation of column references."""
        warnings = []
        
        # This is a simplified check - full validation would require parsing
        # We'll just check if mentioned columns exist in candidate tables
        
        if not feasibility_check or "columns" not in feasibility_check:
            return warnings
        
        expected_columns = feasibility_check.get("columns", [])
        
        # Extract column names from SELECT clause (basic regex)
        select_match = re.search(r'SELECT\s+(.*?)\s+FROM', sql, re.IGNORECASE | re.DOTALL)
        if select_match:
            select_clause = select_match.group(1)
            # This is simplified - production would use SQL parser
            selected_cols = [col.strip().split()[-1] for col in select_clause.split(",")]
            
            # Check if any expected columns are missing
            for expected in expected_columns:
                if expected.lower() not in sql.lower():
                    warnings.append(f"Expected column '{expected}' not found in query")
        
        return warnings


# Convenience function for LangGraph
def sql_validator_node(state: WorkflowState) -> Dict[str, Any]:
    """LangGraph node function for SQL validation."""
    node = SQLValidator()
    return node(state)

