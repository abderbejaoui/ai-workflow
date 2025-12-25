"""
Fallback Node - Handles unclear or ambiguous queries.

Triggered when:
- Intent is ambiguous
- Confidence is below threshold
- Query validation fails
- SQL generation produces invalid results
"""
from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage

try:
    from ..state import WorkflowState
    from ..utils import get_main_llm, format_conversation_history, truncate_history
    from ..config import config
    from ..logging_config import get_logger, log_node_entry, log_node_exit
except ImportError:
    from state import WorkflowState
    from utils import get_main_llm, format_conversation_history, truncate_history
    from config import config
    from logging_config import get_logger, log_node_entry, log_node_exit


class FallbackClarifier:
    """
    Asks clarifying questions when intent is unclear.
    
    This node helps users refine their queries without
    accessing the database or generating SQL.
    """
    
    def __init__(self):
        self.llm = get_main_llm()
        self.logger = get_logger("ai_workflow.fallback")
    
    def __call__(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Generate a clarifying question or helpful suggestion.
        
        Args:
            state: Current workflow state
        
        Returns:
            Updated state with clarification response
        """
        log_node_entry(self.logger, "FallbackClarifier", state)
        
        user_input = state.get("user_input", "")
        conversation_history = state.get("conversation_history", [])
        schema_cache = state.get("schema_cache", {})
        error_message = state.get("error_message", "")
        generated_sql = state.get("generated_sql", "")
        
        # Determine why we're in fallback
        reason = self._determine_fallback_reason(state)
        self.logger.info(f"Fallback triggered - reason: {reason}")
        
        if error_message:
            self.logger.warning(f"Error that triggered fallback: {error_message}")
        
        # If SQL was generated but there's an error, show the error directly
        if generated_sql and not generated_sql.startswith("-- Error"):
            if error_message:
                response = f"❌ **Query Execution Error**\n\n{error_message}\n\n**Generated SQL:**\n```sql\n{generated_sql}\n```\n\nPlease check the SQL or try rephrasing your question."
            else:
                # SQL generated but something else failed
                response = f"❌ **Query could not be executed**\n\nThe SQL was generated but couldn't be processed.\n\n**Generated SQL:**\n```sql\n{generated_sql}\n```"
        else:
            # Generate appropriate response
            response = self._generate_clarification(
                user_input=user_input,
                reason=reason,
                error_message=error_message,
                schema_cache=schema_cache,
                history=truncate_history(conversation_history, max_messages=2)
            )
        
        updates = {
            "response": response,
            "current_node": "fallback"
        }
        
        log_node_exit(self.logger, "FallbackClarifier", updates)
        return updates
    
    def _determine_fallback_reason(self, state: WorkflowState) -> str:
        """Determine why we ended up in fallback state."""
        confidence = state.get("confidence", 1.0)
        validation_result = state.get("validation_result", {})
        feasibility_check = state.get("feasibility_check", {})
        error_message = state.get("error_message", "")
        
        if error_message:
            return "error"
        elif validation_result and not validation_result.get("valid", True):
            return "invalid_sql"
        elif feasibility_check and not feasibility_check.get("feasible", True):
            return "infeasible_query"
        elif confidence < config.DATABRICKS_CONFIDENCE_THRESHOLD:
            return "low_confidence"
        else:
            return "unclear"
    
    def _generate_clarification(
        self,
        user_input: str,
        reason: str,
        error_message: str,
        schema_cache: Dict[str, Any],
        history: list
    ) -> str:
        """Generate a helpful clarification message."""
        
        # If there's an error message, show it directly instead of asking questions
        if error_message:
            return f"❌ **Error executing query:**\n\n{error_message}\n\nPlease check the SQL query or try rephrasing your question."
        
        # If SQL was generated but failed, show that
        generated_sql = ""  # We don't have access to state here, but we can check if it's a data query
        if any(kw in user_input.lower() for kw in ['show', 'find', 'list', 'get', 'customer', 'employee', 'transaction', 'region', 'average', 'top']):
            return f"❌ **Query Execution Failed**\n\nThe query couldn't be executed. This might be due to:\n- Invalid SQL syntax\n- Missing data matching your criteria\n- Database connection issues\n\n**Your query:** {user_input[:100]}...\n\nPlease try rephrasing or simplifying your question."
        
        # Only ask clarifying questions for truly unclear queries
        system_prompt = f"""You are a helpful assistant. The user's query was unclear.

Reason: {reason}

Provide a brief, helpful response (1-2 sentences) suggesting how to improve the query.
Do NOT ask multiple questions - just give one clear suggestion."""
        
        try:
            messages = [SystemMessage(content=system_prompt)]
            messages.append(HumanMessage(content=f"User query: {user_input}"))
            
            response = self.llm.invoke(messages)
            return response.content.strip()
            
        except Exception as e:
            return f"I'm not quite sure what you're looking for. Could you please be more specific? For example, you could ask about customers, employees, transactions, or game sessions."
    
    def _generic_clarification(self, user_input: str, available_tables: list) -> str:
        """Generate a generic clarification when LLM fails."""
        base_message = "I'm not quite sure what you're looking for. Could you please be more specific?"
        
        if available_tables:
            table_list = ", ".join(available_tables[:5])
            return (f"{base_message}\n\n"
                   f"For example, you could ask about data from these tables: {table_list}")
        
        return base_message


# Convenience function for LangGraph
def fallback_node(state: WorkflowState) -> Dict[str, Any]:
    """LangGraph node function for fallback."""
    node = FallbackClarifier()
    return node(state)

