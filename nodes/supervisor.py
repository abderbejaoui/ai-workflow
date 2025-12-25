"""
Supervisor Node - The routing intelligence of the workflow.

This lightweight node classifies intent and determines confidence,
routing requests to the appropriate execution path.

Key requirements:
- Single fast LLM call (gpt-4o-mini)
- No database access
- Returns intent + confidence score
"""
from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage
from state import WorkflowState, SupervisorOutput
from utils import (
    get_supervisor_llm,
    format_conversation_history,
    truncate_history,
    extract_json_from_text,
    format_schema_for_prompt
)
from casino_schema import get_casino_schema_description
from logging_config import get_logger, log_node_entry, log_node_exit, log_llm_call
import json
import time


class SupervisorNode:
    """
    Lightweight intent classifier and router.
    
    Analyzes user input and decides which execution path to take:
    - conversation: General chat
    - databricks: SQL query request
    - fallback: Ambiguous/unclear request
    """
    
    def __init__(self):
        self.llm = get_supervisor_llm()
        self.logger = get_logger("ai_workflow.supervisor")
    
    def __call__(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Main entry point for the supervisor node.
        
        Args:
            state: Current workflow state
        
        Returns:
            Updated state with intent and confidence
        """
        log_node_entry(self.logger, "Supervisor", state)
        start_time = time.time()
        
        user_input = state.get("user_input", "")
        conversation_history = state.get("conversation_history", [])
        schema_cache = state.get("schema_cache", {})
        
        self.logger.info(f"Classifying intent for query: '{user_input[:100]}...'")
        
        # Truncate history to keep prompt small
        recent_history = truncate_history(conversation_history, max_messages=3)
        self.logger.debug(f"Using {len(recent_history)} messages from history")
        
        # Build context for classification
        context = self._build_context(user_input, recent_history, schema_cache)
        
        # Get classification from LLM
        result = self._classify_intent(context)
        
        execution_time = time.time() - start_time
        self.logger.info(
            f"Intent classified: {result.intent} (confidence: {result.confidence:.2f}) in {execution_time:.3f}s",
            extra={
                'intent': result.intent,
                'confidence': result.confidence,
                'execution_time': execution_time
            }
        )
        
        updates = {
            "intent": result.intent,
            "confidence": result.confidence,
            "current_node": "supervisor"
        }
        
        log_node_exit(self.logger, "Supervisor", updates)
        return updates
    
    def _build_context(
        self, 
        user_input: str, 
        history: list,
        schema_cache: Dict[str, Any]
    ) -> str:
        """Build minimal context for intent classification."""
        context_parts = []
        
        # Add recent history if present
        if history:
            history_str = "\n".join([
                f"{msg['role']}: {msg['content']}" 
                for msg in history[-2:]  # Only last 2 messages
            ])
            context_parts.append(f"Recent conversation:\n{history_str}")
        
        # Add available tables (just names, not full schema)
        if schema_cache and "tables" in schema_cache:
            tables = schema_cache["tables"]
            if tables:
                table_names = [t.get("table", t.get("full_name", "")) for t in tables[:15]]
                context_parts.append(f"Available tables: {', '.join(table_names)}")
        
        # Current query
        context_parts.append(f"Current query: {user_input}")
        
        return "\n\n".join(context_parts)
    
    def _classify_intent(self, context: str) -> SupervisorOutput:
        """
        Classify intent using keyword matching first, then LLM as fallback.
        
        Returns intent and confidence score.
        """
        # FAST PATH: Keyword-based classification for obvious data queries
        data_keywords = [
            'show', 'list', 'get', 'find', 'display', 'give', 'select',
            'employe',  # Catches employee, employees
            'customer', 'transaction', 'shift', 'session',
            'equipment', 'revenue', 'salary', 'risk', 'how many',
            'what is', 'average', 'total', 'count', 'sum', 'top',
            'highest', 'lowest', 'first', 'last', 'region', 'department',
            'gambling', 'behavior', 'game', 'bet', 'win', 'loss'
        ]
        
        context_lower = context.lower()
        matching_keywords = [kw for kw in data_keywords if kw in context_lower]
        
        if len(matching_keywords) >= 1:
            # Direct classification - skip LLM
            return SupervisorOutput(
                intent="databricks",
                confidence=0.95,
                reasoning=f"Matched data keywords: {matching_keywords[:3]}"
            )
        
        # Check for obvious conversation patterns
        conversation_patterns = ['hello', 'hi', 'hey', 'thank', 'bye', 'help', 'how are you']
        if any(pattern in context_lower for pattern in conversation_patterns):
            return SupervisorOutput(
                intent="conversation",
                confidence=0.9,
                reasoning="Matched conversation pattern"
            )
        
        # SLOW PATH: Use LLM for ambiguous queries
        system_prompt = """You are an intent classifier for a casino data analytics system.

CLASSIFY the user's request into ONE of three categories:

1. **databricks** - User wants to query casino data, run analytics, or get insights from tables
   Examples: "Show me customer data", "What's the total revenue?", "List high-risk customers", "Show employees"
   
   Available tables: employees, customer, customer_behaviors, transactions, game_sessions, gaming_equipment, shifts

2. **conversation** - ONLY for greetings or meta questions about the system
   - "Hello", "Hi", "Hey"
   - "How are you?"
   - "What can you do?"
   - "Thank you", "Thanks"
   - "Help"

3. **fallback** - ONLY if truly nonsensical or unrelated
   - "asdfgh"
   - "What's the weather?"

IMPORTANT: If the query mentions ANY data term (employees, customers, show, list, get, find, how many), classify as **databricks** with HIGH confidence (0.9+).

Respond with JSON only:
{"intent": "databricks", "confidence": 0.95, "reasoning": "mentions employees"}"""
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=context)
            ]
            
            log_llm_call(self.logger, "gpt-4o-mini (supervisor)")
            response = self.llm.invoke(messages)
            response_text = response.content
            
            # Parse JSON response
            result = extract_json_from_text(response_text)
            
            if not result:
                # Fallback if JSON parsing fails
                return SupervisorOutput(
                    intent="fallback",
                    confidence=0.3,
                    reasoning="Failed to parse supervisor response"
                )
            
            intent = result.get("intent", "fallback")
            confidence = float(result.get("confidence", 0.5))
            reasoning = result.get("reasoning", "")
            
            # Validate intent
            if intent not in ["conversation", "databricks", "fallback"]:
                intent = "fallback"
                confidence = 0.3
            
            # Clamp confidence to [0, 1]
            confidence = max(0.0, min(1.0, confidence))
            
            return SupervisorOutput(
                intent=intent,
                confidence=confidence,
                reasoning=reasoning
            )
            
        except Exception as e:
            # On any error, default to fallback
            return SupervisorOutput(
                intent="fallback",
                confidence=0.2,
                reasoning=f"Error in classification: {str(e)}"
            )
    
    def get_routing_decision(self, intent: str, confidence: float) -> str:
        """
        Determine which node to route to based on intent and confidence.
        
        Routing logic:
        - databricks + confidence >= 0.5 → databricks_path (lowered threshold)
        - conversation → conversation_path
        - fallback only for truly ambiguous queries
        """
        if intent == "databricks" and confidence >= 0.5:
            return "databricks_path"
        elif intent == "conversation":
            return "conversation_path"
        elif confidence < 0.4:
            return "fallback"
        else:
            # Default to databricks for data-related queries
            return "databricks_path"


# Convenience function for LangGraph
def supervisor_node(state: WorkflowState) -> Dict[str, Any]:
    """LangGraph node function for the supervisor."""
    node = SupervisorNode()