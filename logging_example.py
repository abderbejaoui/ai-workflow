"""
Example demonstrating the logging system.
Run this to see how logging works throughout the workflow.
"""
from main import AIWorkflowOrchestrator
from logging_config import init_default_logger, get_logger
import os

# Set logging to DEBUG to see everything
os.environ["LOG_LEVEL"] = "DEBUG"

# Initialize logging
init_default_logger()
logger = get_logger("example")

print("\n" + "="*70)
print("LOGGING EXAMPLE - Watch the logs below")
print("="*70)
print("\nThis example shows the comprehensive logging throughout the workflow.")
print("Notice:")
print("  - Request ID tracking")
print("  - Node entry/exit logs")
print("  - Routing decisions with reasons")
print("  - LLM call tracking")
print("  - Performance metrics")
print("  - SQL generation and execution")
print("\n" + "="*70 + "\n")

# Initialize orchestrator
logger.info("Initializing orchestrator for logging example...")
orchestrator = AIWorkflowOrchestrator(use_mock_schema=True)

# Example 1: Conversation path
print("\n" + "-"*70)
print("EXAMPLE 1: Conversation Path")
print("-"*70 + "\n")

result = orchestrator.query("Hello! How are you?", verbose=False)
print(f"\nResponse: {result['response']}")
print(f"Path taken: {result['path_taken']}")
print(f"Execution time: {result['execution_time']:.3f}s")

# Example 2: Databricks path (with mock schema)
print("\n" + "-"*70)
print("EXAMPLE 2: Databricks Query Path")
print("-"*70 + "\n")

result = orchestrator.query("Show me all customers from USA", verbose=False)
print(f"\nResponse: {result['response']}")
print(f"Path taken: {result['path_taken']}")
print(f"Intent: {result['intent']}")
print(f"Confidence: {result['confidence']:.2f}")
if result.get('sql'):
    print(f"SQL: {result['sql'][:80]}...")
print(f"Execution time: {result['execution_time']:.3f}s")

# Example 3: Fallback path
print("\n" + "-"*70)
print("EXAMPLE 3: Fallback Path (Ambiguous Query)")
print("-"*70 + "\n")

result = orchestrator.query("Show me that thing", verbose=False)
print(f"\nResponse: {result['response']}")
print(f"Path taken: {result['path_taken']}")
print(f"Confidence: {result['confidence']:.2f}")
print(f"Execution time: {result['execution_time']:.3f}s")

print("\n" + "="*70)
print("LOGGING EXAMPLE COMPLETE")
print("="*70)
print("\nKey observations from the logs:")
print("  ✓ Every query has a unique Request ID")
print("  ✓ All nodes log entry and exit")
print("  ✓ Routing decisions show clear reasoning")
print("  ✓ LLM calls are tracked")
print("  ✓ Execution times are measured")
print("  ✓ Errors would show full stack traces")
print("\nLogs are also saved to: logs/ai_workflow.log")
print("\nFor more logging options, see LOGGING.md")
print("="*70 + "\n")

