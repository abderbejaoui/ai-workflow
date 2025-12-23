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
        Classify intent using a single LLM call.
        
        Returns intent and confidence score.
        """
        system_prompt = """You are an intent classifier for a casino data analytics system.

Your job: Analyze the user's request and classify it into ONE of three categories:

1. **databricks** - User wants to query casino data, run analytics, or get insights from tables
   Examples: "Show me customer data", "What's the total revenue?", "List high-risk customers"
   
   Available Casino Tables:
   - customers (7,678 records) - Customer profiles, demographics, risk scores
   - customer_behaviors (1,993 records) - Gambling patterns, problem gambling indicators
   - transactions (586,781 records) - Payment transactions, deposits, withdrawals
   - game_sessions (3,000 records) - Gaming sessions, bets, wins, duration
   - gaming_equipment (20 records) - Tables, machines, equipment status
   - shifts (100 records) - Employee shifts, performance metrics
   - employees (50 records) - Staff directory, departments, salaries

2. **conversation** - General chat, greetings, system questions (not about data)
   Examples: "Hello", "How are you?", "What can you do?", "Thank you"

3. **fallback** - Unclear, ambiguous, or needs clarification
   Examples: "Show me that thing", "What about yesterday?", "Give me the data"

Also provide a confidence score (0.0 to 1.0):
- 0.9-1.0: Very clear intent
- 0.75-0.89: Clear intent
- 0.5-0.74: Somewhat clear
- 0.0-0.49: Ambiguous

Respond ONLY with JSON:
{
  "intent": "databricks" | "conversation" | "fallback",
  "confidence": 0.85,
  "reasoning": "brief explanation"
}"""
        
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
        - databricks + confidence >= 0.75 → databricks_path
        - confidence < 0.75 → fallback
        - conversation → conversation_path
        """
        if intent == "databricks" and confidence >= 0.75:
            return "databricks_path"
        elif confidence < 0.75:
            return "fallback"
        elif intent == "conversation":
            return "conversation_path"
        else:
            return "fallback"


# Convenience function for LangGraph
def supervisor_node(state: WorkflowState) -> Dict[str, Any]:
    """LangGraph node function for the supervisor."""
    node = SupervisorNode()
    return node(state)

