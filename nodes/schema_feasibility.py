"""
Schema Feasibility Checker - Validates query feasibility against cached schema.

This node uses ONLY the pre-cached schema metadata to determine:
- If the query is feasible
- Which tables are needed
- If required columns exist

NO database access happens here.
"""
from typing import Dict, Any, List, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from state import WorkflowState, SchemaTable
from utils import get_main_llm, extract_json_from_text
from logging_config import get_logger, log_node_entry, log_node_exit
import json
import time


class SchemaFeasibilityChecker:
    """
    Checks if a query is feasible using only cached schema.
    
    Rejects queries with:
    - Unknown tables
    - Missing required columns
    - Ambiguous table references
    """
    
    def __init__(self):
        self.llm = get_main_llm()
        self.logger = get_logger("ai_workflow.schema_feasibility")
    
    def __call__(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Check if the user's query is feasible against the schema.
        
        Args:
            state: Current workflow state
        
        Returns:
            Updated state with feasibility check results
        """
        log_node_entry(self.logger, "SchemaFeasibilityChecker", state)
        start_time = time.time()
        
        user_input = state.get("user_input", "")
        schema_cache = state.get("schema_cache", {})
        
        self.logger.info(f"Checking feasibility for query: '{user_input[:100]}...'")
        
        # Perform feasibility check
        result = self._check_feasibility(user_input, schema_cache)
        
        execution_time = time.time() - start_time
        
        if result.get("feasible"):
            self.logger.info(
                f"✓ Query is feasible (tables: {result.get('tables', [])}) in {execution_time:.3f}s"
            )
        else:
            self.logger.warning(
                f"✗ Query not feasible: {result.get('reason', 'Unknown')} in {execution_time:.3f}s"
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
        Analyze if query is feasible with available schema.
        
        Returns:
            {
                "feasible": bool,
                "tables": List[str],  # Candidate tables
                "columns": List[str],  # Candidate columns
                "reason": str
            }
        """
        if not schema_cache or "tables" not in schema_cache:
            return {
                "feasible": False,
                "tables": [],
                "columns": [],
                "reason": "No schema metadata available"
            }
        
        tables = schema_cache["tables"]
        
        # Build concise schema description
        schema_description = self._format_schema_for_analysis(tables)
        
        # Use LLM to determine feasibility
        system_prompt = """You are a schema analyst. Analyze if a user's query can be answered using the available database schema.

Your task:
1. Identify which tables are needed
2. Check if required columns likely exist
3. Determine if the query is feasible

Respond with JSON:
{
  "feasible": true/false,
  "tables": ["table1", "table2"],
  "columns": ["col1", "col2"],
  "reason": "explanation"
}

Mark as NOT feasible if:
- Required tables don't exist
- Column names are too ambiguous
- Query requires joins that don't make sense"""
        
        user_message = f"""Available schema:
{schema_description}

User query: {user_input}

Can this query be answered with the available schema?"""
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_message)
            ]
            
            response = self.llm.invoke(messages)
            result = extract_json_from_text(response.content)
            
            if not result:
                return {
                    "feasible": False,
                    "tables": [],
                    "columns": [],
                    "reason": "Failed to parse feasibility check"
                }
            
            return {
                "feasible": result.get("feasible", False),
                "tables": result.get("tables", []),
                "columns": result.get("columns", []),
                "reason": result.get("reason", "")
            }
            
        except Exception as e:
            return {
                "feasible": False,
                "tables": [],
                "columns": [],
                "reason": f"Error during feasibility check: {str(e)}"
            }
    
    def _format_schema_for_analysis(self, tables: List[Dict[str, Any]]) -> str:
        """Format schema in a compact way for the LLM."""
        lines = []
        
        for table in tables[:20]:  # Limit to first 20 tables to save tokens
            table_name = table.get("full_name") or table.get("table", "unknown")
            columns = table.get("columns", [])
            column_types = table.get("column_types", {})
            
            # Format: table_name (col1: type1, col2: type2, ...)
            col_info = []
            for col in columns[:10]:  # First 10 columns
                col_type = column_types.get(col, "unknown")
                col_info.append(f"{col}: {col_type}")
            
            col_str = ", ".join(col_info)
            if len(columns) > 10:
                col_str += f" ... (+{len(columns) - 10} more)"
            
            lines.append(f"- {table_name} ({col_str})")
        
        if len(tables) > 20:
            lines.append(f"... and {len(tables) - 20} more tables")
        
        return "\n".join(lines)


# Convenience function for LangGraph
def schema_feasibility_node(state: WorkflowState) -> Dict[str, Any]:
    """LangGraph node function for schema feasibility checking."""
    node = SchemaFeasibilityChecker()
    return node(state)

