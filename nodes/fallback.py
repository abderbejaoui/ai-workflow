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
from state import WorkflowState
from utils import get_main_llm, format_conversation_history, truncate_history
from config import config


class FallbackClarifier:
    """
    Asks clarifying questions when intent is unclear.
    
    This node helps users refine their queries without
    accessing the database or generating SQL.
    """
    
    def __init__(self):
        self.llm = get_main_llm()
    
    def __call__(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Generate a clarifying question or helpful suggestion.
        
        Args:
            state: Current workflow state
        
        Returns:
            Updated state with clarification response
        """
        user_input = state.get("user_input", "")
        conversation_history = state.get("conversation_history", [])
        schema_cache = state.get("schema_cache", {})
        error_message = state.get("error_message", "")
        
        # Determine why we're in fallback
        reason = self._determine_fallback_reason(state)
        
        # Generate appropriate response
        response = self._generate_clarification(
            user_input=user_input,
            reason=reason,
            error_message=error_message,
            schema_cache=schema_cache,
            history=truncate_history(conversation_history, max_messages=2)
        )
        
        return {
            "response": response,
            "current_node": "fallback"
        }
    
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
        
        # Build context based on why we're asking for clarification
        context_info = []
        
        if error_message:
            context_info.append(f"Error encountered: {error_message}")
        
        if reason == "infeasible_query":
            context_info.append("The requested query cannot be fulfilled with available tables.")
        
        # Get available tables for suggestions
        available_tables = []
        if schema_cache and "tables" in schema_cache:
            tables = schema_cache["tables"]
            available_tables = [t.get("table", "") for t in tables[:10]]
        
        if available_tables:
            context_info.append(f"Available tables: {', '.join(available_tables)}")
        
        system_prompt = f"""You are a helpful assistant that asks clarifying questions.

The user's query was unclear or couldn't be processed.

Reason: {reason}

Your task:
1. Ask ONE specific clarifying question, OR
2. Suggest a rephrased version of their query

Be helpful and guide them toward a successful query.

Context:
{chr(10).join(context_info) if context_info else 'None'}

Keep your response concise (2-3 sentences)."""
        
        try:
            messages = [SystemMessage(content=system_prompt)]
            
            # Add minimal history
            if history:
                messages.extend(format_conversation_history(history))
            
            # Add current query
            messages.append(HumanMessage(content=f"User query: {user_input}"))
            
            response = self.llm.invoke(messages)
            return response.content.strip()
            
        except Exception as e:
            # Fallback to generic clarification
            return self._generic_clarification(user_input, available_tables)
    
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

