"""
Conversation Node - Handles general chat interactions.

Optimized for:
- Low latency
- Minimal token usage
- Stateless beyond necessary context
- Single LLM call
"""
from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage
from state import WorkflowState
from utils import get_main_llm, format_conversation_history, truncate_history
from config import config


class ConversationResponder:
    """
    Handles general conversational queries.
    
    This node is for non-data queries like greetings, 
    questions about capabilities, or general chat.
    """
    
    def __init__(self):
        self.llm = get_main_llm()
    
    def __call__(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Generate a conversational response.
        
        Args:
            state: Current workflow state
        
        Returns:
            Updated state with response
        """
        user_input = state.get("user_input", "")
        conversation_history = state.get("conversation_history", [])
        
        # Use limited history to minimize tokens
        recent_history = truncate_history(
            conversation_history,
            max_messages=config.CONVERSATION_HISTORY_LIMIT
        )
        
        # Generate response
        response = self._generate_response(user_input, recent_history)
        
        return {
            "response": response,
            "current_node": "conversation"
        }
    
    def _generate_response(self, user_input: str, history: list) -> str:
        """Generate a conversational response using the LLM."""
        system_prompt = """You are a helpful AI assistant for a data analytics platform.

You help users with:
- General questions and conversation
- Explaining what you can do
- Guiding them on how to query data

Keep responses:
- Concise (2-3 sentences max)
- Friendly and professional
- Actionable

If users want to query data, encourage them to ask specific questions about the data they want to see."""
        
        try:
            messages = [SystemMessage(content=system_prompt)]
            
            # Add conversation history
            if history:
                messages.extend(format_conversation_history(history))
            
            # Add current query
            messages.append(HumanMessage(content=user_input))
            
            response = self.llm.invoke(messages)
            return response.content.strip()
            
        except Exception as e:
            return f"I apologize, but I encountered an error: {str(e)}. Please try again."


# Convenience function for LangGraph
def conversation_node(state: WorkflowState) -> Dict[str, Any]:
    """LangGraph node function for conversation."""
    node = ConversationResponder()
    return node(state)

