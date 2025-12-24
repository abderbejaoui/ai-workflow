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
import json
import time
import re

try:
    from ..state import WorkflowState, SupervisorOutput
    from ..utils import (
        get_supervisor_llm,
        format_conversation_history,
        truncate_history,
        extract_json_from_text,
        format_schema_for_prompt
    )
    from ..casino_schema import get_casino_schema_description
    from ..logging_config import get_logger, log_node_entry, log_node_exit, log_llm_call
except ImportError:
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
        
        # Data-related keywords that trigger databricks path
        self.data_keywords = [
            'show', 'list', 'get', 'find', 'display', 'give', 'select', 'query',
            'employee', 'employees', 'staff', 'worker',
            'customer', 'customers', 'client', 'user',
            'transaction', 'transactions', 'payment', 'deposit', 'withdrawal',
            'shift', 'shifts', 'schedule',
            'session', 'sessions', 'game', 'gaming', 'bet', 'gambling',
            'equipment', 'machine', 'table',
            'revenue', 'salary', 'income', 'money', 'amount',
            'risk', 'high-risk', 'problem',
            'how many', 'count', 'total', 'sum', 'average', 'avg',
            'top', 'highest', 'lowest', 'first', 'last', 'best', 'worst',
            'region', 'department', 'age', 'gender',
            'behavior', 'behaviors'
        ]
        
        # Pure conversation patterns
        self.conversation_patterns = [
            'hello', 'hi', 'hey', 'thank', 'thanks', 'bye', 'goodbye',
            'how are you', 'what can you do', 'help me understand',
            'who are you', 'what is this'
        ]
    
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
        
        self.logger.info(f"Classifying intent for query: '{user_input}'")
        
        # FAST PATH: Direct keyword classification (no LLM needed)
        result = self._classify_by_keywords(user_input)
        
        execution_time = time.time() - start_time
        self.logger.info(
            f"Intent classified: {result.intent} (confidence: {result.confidence:.2f}) in {execution_time:.3f}s - {result.reasoning}"
        )
        
        updates = {
            "intent": result.intent,
            "confidence": result.confidence,
            "current_node": "supervisor"
        }
        
        log_node_exit(self.logger, "Supervisor", updates)
        return updates
    
    def _classify_by_keywords(self, user_input: str) -> SupervisorOutput:
        """
        Fast keyword-based classification.
        
        This avoids LLM calls for obvious queries.
        """
        user_lower = user_input.lower().strip()
        
        # Check if it's pure conversation
        for pattern in self.conversation_patterns:
            if user_lower == pattern or user_lower.startswith(pattern + ' ') or user_lower.startswith(pattern + ','):
                return SupervisorOutput(
                    intent="conversation",
                    confidence=0.95,
                    reasoning=f"Matched conversation pattern: '{pattern}'"
                )
        
        # Check for data keywords
        matched_keywords = []
        for keyword in self.data_keywords:
            # Use word boundary matching for single words, contains for phrases
            if ' ' in keyword:
                if keyword in user_lower:
                    matched_keywords.append(keyword)
            else:
                # Match as word (not part of another word)
                if re.search(rf'\b{re.escape(keyword)}\b', user_lower):
                    matched_keywords.append(keyword)
        
        if matched_keywords:
            return SupervisorOutput(
                intent="databricks",
                confidence=0.95,
                reasoning=f"Matched data keywords: {matched_keywords[:3]}"
            )
        
        # Check for question patterns that suggest data queries
        data_question_patterns = [
            r'^how\s+many',
            r'^what\s+is\s+the',
            r'^who\s+has',
            r'^which\s+',
            r'^where\s+are',
            r'^\d+\s+\w+',  # "3 employees", "5 customers"
        ]
        
        for pattern in data_question_patterns:
            if re.search(pattern, user_lower):
                return SupervisorOutput(
                    intent="databricks",
                    confidence=0.85,
                    reasoning=f"Matched data question pattern"
                )
        
        # Default: if short and unclear, try as data query anyway
        if len(user_input.split()) <= 3:
            return SupervisorOutput(
                intent="databricks",
                confidence=0.7,
                reasoning="Short query, defaulting to data query"
            )
        
        # For longer unclear queries, use conversation
        return SupervisorOutput(
            intent="conversation",
            confidence=0.6,
            reasoning="No clear data keywords, treating as conversation"
        )


# Convenience function for LangGraph
def supervisor_node(state: WorkflowState) -> Dict[str, Any]:
    """LangGraph node function for the supervisor."""
    node = SupervisorNode()
    return node(state)
