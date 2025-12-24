"""
Schema Feasibility Checker - Always marks data queries as feasible.

This node is LENIENT - it almost always marks queries as feasible.
Let the SQL generator and database handle the actual validation.
"""
from typing import Dict, Any, List
import time
import re

try:
    from ..state import WorkflowState
    from ..logging_config import get_logger, log_node_entry, log_node_exit
except ImportError:
    from state import WorkflowState
    from logging_config import get_logger, log_node_entry, log_node_exit


class SchemaFeasibilityChecker:
    """
    Checks if a query is feasible using simple keyword matching.
    
    BE VERY LENIENT - almost all queries should be marked as feasible.
    """
    
    def __init__(self):
        self.logger = get_logger("ai_workflow.schema_feasibility")
        
        # Keywords that map to specific tables
        self.table_keywords = {
            "hr_casino.employees": ["employee", "staff", "worker", "hire", "salary", "department", "position"],
            "marketing_casino.customer": ["customer", "client", "member", "user", "age", "gender", "region"],
            "marketing_casino.customer_behaviors": ["behavior", "gambling", "betting", "risk", "problem", "score", "online", "offline"],
            "finance_casino.transactions": ["transaction", "payment", "deposit", "withdrawal", "amount", "money", "finance"],
            "operations_casino.game_sessions": ["session", "game", "bet", "win", "loss", "play", "gaming"],
            "operations_casino.gaming_equipment": ["equipment", "machine", "slot", "device"],
            "operations_casino.shifts": ["shift", "schedule", "revenue", "work"]
        }
    
    def __call__(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Check if the user's query is feasible.
        
        Args:
            state: Current workflow state
        
        Returns:
            Updated state with feasibility check results
        """
        log_node_entry(self.logger, "SchemaFeasibilityChecker", state)
        start_time = time.time()
        
        user_input = state.get("user_input", "")
        schema_cache = state.get("schema_cache", {})
        
        self.logger.info(f"Checking feasibility for query: '{user_input}'")
        
        # Perform feasibility check
        result = self._check_feasibility(user_input, schema_cache)
        
        execution_time = time.time() - start_time
        
        self.logger.info(
            f"Feasibility: {result.get('feasible')} (tables: {result.get('tables', [])}) in {execution_time:.3f}s"
        )
        
        updates = {
            "feasibility_check": result,
            "current_node": "schema_feasibility"
        }
        
        log_node_exit(self.logger, "SchemaFeasibilityChecker", updates)
        return updates
    
    def _check_feasibility(
        self, 
        user_input: str, 
        schema_cache: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Simple keyword-based feasibility check.
        
        BE VERY LENIENT - default to feasible.
        """
        user_input_lower = user_input.lower()
        matched_tables = []
        
        # Check each table's keywords against user input
        for table_name, keywords in self.table_keywords.items():
            for keyword in keywords:
                if keyword in user_input_lower:
                    if table_name not in matched_tables:
                        matched_tables.append(table_name)
                    break
        
        # If no specific tables matched, try to infer from generic keywords
        if not matched_tables:
            # Check for generic data keywords
            if any(kw in user_input_lower for kw in ['show', 'list', 'get', 'find', 'display']):
                # Default to employees table for generic queries
                matched_tables = ["hr_casino.employees"]
        
        # Always mark as feasible for any data-like query
        return {
            "feasible": True,
            "tables": matched_tables if matched_tables else ["hr_casino.employees"],
            "columns": [],
            "reason": f"Matched tables: {matched_tables}" if matched_tables else "Default to employees table"
        }


# Convenience function for LangGraph
def schema_feasibility_node(state: WorkflowState) -> Dict[str, Any]:
    """LangGraph node function for schema feasibility checking."""
    node = SchemaFeasibilityChecker()
    return node(state)
