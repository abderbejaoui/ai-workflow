"""
Supervisor Node - The routing intelligence of the workflow.

This lightweight node classifies intent and determines confidence,
routing requests to the appropriate execution path.

Key requirements:
- Fast keyword-based classification (no LLM needed for data queries)
- Always routes data queries to databricks path
- Only uses conversation for pure greetings
"""
from typing import Dict, Any
import re
import time

try:
    from ..state import WorkflowState, SupervisorOutput
    from ..logging_config import get_logger, log_node_entry, log_node_exit
except ImportError:
    from state import WorkflowState, SupervisorOutput
    from logging_config import get_logger, log_node_entry, log_node_exit


class SupervisorNode:
    """
    Lightweight intent classifier and router.
    
    Analyzes user input and decides which execution path to take:
    - conversation: ONLY pure greetings (hi, hello, thanks)
    - databricks: ALL data queries (default for anything unclear)
    """
    
    def __init__(self):
        self.logger = get_logger("ai_workflow.supervisor")
        
        # Data-related keywords - if ANY of these appear, route to databricks
        self.data_keywords = [
            'show', 'list', 'get', 'find', 'display', 'give', 'select', 'query',
            'employee', 'employees', 'staff', 'worker',
            'customer', 'customers', 'client', 'user',
            'transaction', 'transactions', 'payment', 'deposit', 'withdrawal',
            'shift', 'shifts', 'schedule',
            'session', 'sessions', 'game', 'gaming', 'bet', 'gambling',
            'equipment', 'machine', 'table',
            'revenue', 'salary', 'income', 'money', 'amount', 'expenditure',
            'risk', 'high-risk', 'problem', 'behavior', 'behaviors',
            'how many', 'count', 'total', 'sum', 'average', 'avg', 'top',
            'highest', 'lowest', 'first', 'last', 'best', 'worst',
            'region', 'department', 'age', 'gender',
            'online', 'offline', 'monthly', 'spending'
        ]
        
        # ONLY pure conversation patterns - very restrictive
        self.conversation_patterns = [
            r'^hello$', r'^hi$', r'^hey$', r'^thanks?$', r'^thank you$',
            r'^bye$', r'^goodbye$', r'^how are you$'
        ]
    
    def __call__(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Main entry point for the supervisor node.
        """
        log_node_entry(self.logger, "Supervisor", state)
        start_time = time.time()
        
        user_input = state.get("user_input", "")
        
        self.logger.info(f"Classifying intent for query: '{user_input[:100]}...'")
        
        # FAST PATH: Direct keyword classification (no LLM needed)
        result = self._classify_by_keywords(user_input)
        
        execution_time = time.time() - start_time
        self.logger.info(
            f"Intent: {result.intent} (confidence: {result.confidence:.2f}) - {result.reasoning}"
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
        
        Defaults to databricks for anything that could be a data query.
        """
        user_lower = user_input.lower().strip()
        
        # Check if it's PURE conversation (exact match only)
        for pattern in self.conversation_patterns:
            if re.match(pattern, user_lower):
                return SupervisorOutput(
                    intent="conversation",
                    confidence=0.95,
                    reasoning=f"Pure conversation pattern: '{pattern}'"
                )
        
        # Check for ANY data keywords - if found, route to databricks
        matched_keywords = []
        for keyword in self.data_keywords:
            if ' ' in keyword:
                # Phrase match
                if keyword in user_lower:
                    matched_keywords.append(keyword)
            else:
                # Word boundary match
                if re.search(rf'\b{re.escape(keyword)}\b', user_lower):
                    matched_keywords.append(keyword)
        
        if matched_keywords:
            return SupervisorOutput(
                intent="databricks",
                confidence=0.98,
                reasoning=f"Data keywords detected: {matched_keywords[:5]}"
            )
        
        # Check for question patterns
        question_patterns = [
            r'^how\s+many', r'^what\s+is', r'^who\s+', r'^which\s+',
            r'^where\s+', r'^when\s+', r'^show\s+me', r'^find\s+',
            r'^list\s+', r'^get\s+', r'^top\s+\d+', r'^\d+\s+\w+'
        ]
        
        for pattern in question_patterns:
            if re.search(pattern, user_lower):
                return SupervisorOutput(
                    intent="databricks",
                    confidence=0.95,
                    reasoning=f"Question pattern detected"
                )
        
        # DEFAULT: Route to databricks for anything unclear
        # This ensures we try to answer data queries rather than asking questions
        return SupervisorOutput(
            intent="databricks",
            confidence=0.8,
            reasoning="Default routing to databricks for potential data query"
        )


# Convenience function for LangGraph
def supervisor_node(state: WorkflowState) -> Dict[str, Any]:
    """LangGraph node function for the supervisor."""
    node = SupervisorNode()
    return node(state)
