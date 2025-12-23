"""
LangGraph Workflow Construction and Routing Logic.

This module builds the complete workflow graph with all nodes and edges,
implementing the routing logic between execution paths.
"""
from typing import Literal
from langgraph.graph import StateGraph, END
from state import WorkflowState
from config import config
from logging_config import get_logger, log_routing_decision
from nodes import (
    supervisor_node,
    conversation_node,
    fallback_node,
    schema_feasibility_node,
    sql_generator_node,
    sql_validator_node,
    casino_api_executor_node,
    result_summarizer_node,
)

# Module-level logger
logger = get_logger("ai_workflow.routing")


def route_from_supervisor(state: WorkflowState) -> str:
    """
    Route from supervisor based on intent and confidence.
    
    Routing logic:
    - databricks + confidence >= 0.75 → schema_feasibility
    - confidence < 0.75 → fallback
    - conversation → conversation_node
    - otherwise → fallback
    """
    intent = state.get("intent", "fallback")
    confidence = state.get("confidence", 0.0)
    
    if intent == "databricks" and confidence >= config.DATABRICKS_CONFIDENCE_THRESHOLD:
        next_node = "schema_feasibility"
        reason = f"databricks intent with high confidence ({confidence:.2f})"
    elif confidence < config.DATABRICKS_CONFIDENCE_THRESHOLD:
        next_node = "fallback"
        reason = f"low confidence ({confidence:.2f})"
    elif intent == "conversation":
        next_node = "conversation"
        reason = "conversation intent"
    else:
        next_node = "fallback"
        reason = f"unknown intent: {intent}"
    
    log_routing_decision(logger, "supervisor", next_node, reason)
    return next_node


def route_from_feasibility(state: WorkflowState) -> str:
    """
    Route from schema feasibility check.
    
    - If feasible → sql_generator
    - If not feasible → fallback
    """
    feasibility_check = state.get("feasibility_check", {})
    is_feasible = feasibility_check.get("feasible", False)
    
    if is_feasible:
        next_node = "sql_generator"
        reason = "query is feasible"
    else:
        next_node = "fallback"
        reason = feasibility_check.get("reason", "query not feasible")
    
    log_routing_decision(logger, "schema_feasibility", next_node, reason)
    return next_node


def route_from_validator(state: WorkflowState) -> str:
    """
    Route from SQL validator.
    
    - If valid → casino_api_executor
    - If invalid → fallback
    """
    validation_result = state.get("validation_result", {})
    is_valid = validation_result.get("valid", False)
    
    if is_valid:
        next_node = "casino_api_executor"
        reason = "SQL is valid"
    else:
        next_node = "fallback"
        errors = validation_result.get("errors", [])
        reason = f"SQL validation failed: {errors[0] if errors else 'unknown'}"
    
    log_routing_decision(logger, "sql_validator", next_node, reason)
    return next_node


def route_from_executor(state: WorkflowState) -> str:
    """
    Route from Casino API executor.
    
    - If successful (no error) → result_summarizer
    - If error → fallback
    """
    error_message = state.get("error_message")
    
    if error_message:
        next_node = "fallback"
        reason = f"execution error: {error_message[:50]}"
    else:
        next_node = "result_summarizer"
        reason = "query executed successfully"
    
    log_routing_decision(logger, "casino_api_executor", next_node, reason)
    return next_node


def build_workflow() -> StateGraph:
    """
    Build the complete LangGraph workflow.
    
    Graph structure:
    
    START → supervisor → {conversation, fallback, schema_feasibility}
    
    conversation → END
    
    fallback → END
    
    schema_feasibility → {sql_generator, fallback}
    sql_generator → sql_validator
    sql_validator → {databricks_executor, fallback}
    databricks_executor → {result_summarizer, fallback}
    result_summarizer → END
    """
    logger.info("Building LangGraph workflow...")
    
    # Create graph with state schema
    workflow = StateGraph(WorkflowState)
    
    # Add all nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("conversation", conversation_node)
    workflow.add_node("fallback", fallback_node)
    workflow.add_node("schema_feasibility", schema_feasibility_node)
    workflow.add_node("sql_generator", sql_generator_node)
    workflow.add_node("sql_validator", sql_validator_node)
    workflow.add_node("casino_api_executor", casino_api_executor_node)
    workflow.add_node("result_summarizer", result_summarizer_node)
    
    # Set entry point
    workflow.set_entry_point("supervisor")
    
    # Add conditional edges from supervisor
    workflow.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "conversation": "conversation",
            "fallback": "fallback",
            "schema_feasibility": "schema_feasibility",
        }
    )
    
    # Conversation and fallback are terminal
    workflow.add_edge("conversation", END)
    workflow.add_edge("fallback", END)
    
    # Databricks query path
    workflow.add_conditional_edges(
        "schema_feasibility",
        route_from_feasibility,
        {
            "sql_generator": "sql_generator",
            "fallback": "fallback",
        }
    )
    
    workflow.add_edge("sql_generator", "sql_validator")
    
    workflow.add_conditional_edges(
        "sql_validator",
        route_from_validator,
        {
            "casino_api_executor": "casino_api_executor",
            "fallback": "fallback",
        }
    )
    
    workflow.add_conditional_edges(
        "casino_api_executor",
        route_from_executor,
        {
            "result_summarizer": "result_summarizer",
            "fallback": "fallback",
        }
    )
    
    workflow.add_edge("result_summarizer", END)
    
    logger.info("✓ LangGraph workflow built successfully")
    
    # Compile the graph
    return workflow.compile()


def create_initial_state(
    user_input: str,
    conversation_history: list = None,
    schema_cache: dict = None
) -> WorkflowState:
    """
    Create initial state for workflow execution.
    
    Args:
        user_input: User's query
        conversation_history: Previous conversation messages
        schema_cache: Pre-cached schema metadata
    
    Returns:
        Initial state dict
    """
    return {
        "user_input": user_input,
        "conversation_history": conversation_history or [],
        "schema_cache": schema_cache or {},
        "intent": "conversation",
        "confidence": 0.0,
        "feasibility_check": {},
        "generated_sql": None,
        "validation_result": {},
        "query_result": None,
        "response": "",
        "current_node": "start",
        "error_message": None,
    }


# Global workflow instance (compiled once)
_workflow = None


def get_workflow():
    """Get or create the compiled workflow (singleton pattern)."""
    global _workflow
    if _workflow is None:
        _workflow = build_workflow()
    return _workflow

