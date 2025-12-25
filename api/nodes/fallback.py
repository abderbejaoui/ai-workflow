"""
Fallback Node - Handles errors and failed queries.

NEVER asks clarifying questions for data queries.
Always shows the error and SQL if available.
"""
from typing import Dict, Any

try:
    from ..state import WorkflowState
    from ..logging_config import get_logger, log_node_entry, log_node_exit
except ImportError:
    from state import WorkflowState
    from logging_config import get_logger, log_node_entry, log_node_exit


class FallbackClarifier:
    """
    Handles errors - NEVER asks clarifying questions.
    Shows the error and SQL directly to the user.
    """
    
    def __init__(self):
        self.logger = get_logger("ai_workflow.fallback")
    
    def __call__(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Generate error response - NO clarifying questions.
        """
        log_node_entry(self.logger, "FallbackClarifier", state)
        
        user_input = state.get("user_input", "")
        error_message = state.get("error_message", "")
        generated_sql = state.get("generated_sql", "")
        query_result = state.get("query_result")
        
        self.logger.info(f"Fallback triggered - error: {error_message[:100] if error_message else 'None'}")
        
        # Build response based on what we have
        if generated_sql and not generated_sql.startswith("-- Error"):
            if error_message:
                # SQL was generated but execution failed
                response = (
                    f"❌ **Query Execution Error**\n\n"
                    f"{error_message}\n\n"
                    f"**Generated SQL:**\n```sql\n{generated_sql}\n```\n\n"
                    f"The database returned an error. Please try rephrasing your question."
                )
            elif query_result is not None and len(query_result) == 0:
                # Query ran but returned no results
                response = (
                    f"📊 **No Results Found**\n\n"
                    f"The query executed successfully but returned no matching records.\n\n"
                    f"**Generated SQL:**\n```sql\n{generated_sql}\n```\n\n"
                    f"Try lowering thresholds or removing some filters."
                )
            else:
                # SQL generated but unknown issue
                response = (
                    f"❌ **Query Processing Error**\n\n"
                    f"An unexpected error occurred while processing the query.\n\n"
                    f"**Generated SQL:**\n```sql\n{generated_sql}\n```"
                )
        elif generated_sql and generated_sql.startswith("-- Error"):
            # SQL generation itself failed
            response = (
                f"❌ **SQL Generation Error**\n\n"
                f"{generated_sql}\n\n"
                f"Please try rephrasing your question."
            )
        elif error_message:
            # Generic error
            response = f"❌ **Error**\n\n{error_message}"
        else:
            # Unknown error
            response = (
                f"❌ **Unable to process query**\n\n"
                f"Your query: {user_input[:200]}\n\n"
                f"Please try rephrasing or simplifying your question."
            )
        
        updates = {
            "response": response,
            "current_node": "fallback"
        }
        
        log_node_exit(self.logger, "FallbackClarifier", updates)
        return updates


# Convenience function for LangGraph
def fallback_node(state: WorkflowState) -> Dict[str, Any]:
    """LangGraph node function for fallback."""
    node = FallbackClarifier()
    return node(state)

