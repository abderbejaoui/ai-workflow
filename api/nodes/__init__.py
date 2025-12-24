"""
Node package initialization.
Exports all node classes and functions for easy importing.
"""
try:
    # Relative imports for Vercel
    from .supervisor import SupervisorNode, supervisor_node
    from .conversation import ConversationResponder, conversation_node
    from .fallback import FallbackClarifier, fallback_node
    from .schema_feasibility import SchemaFeasibilityChecker, schema_feasibility_node
    from .sql_generator import SQLGenerator, sql_generator_node
    from .sql_validator import SQLValidator, sql_validator_node
    from .casino_api_executor import CasinoAPIExecutor, casino_api_executor_node
    from .result_summarizer import ResultSummarizer, result_summarizer_node
except ImportError:
    # Absolute imports for local development
    from nodes.supervisor import SupervisorNode, supervisor_node
    from nodes.conversation import ConversationResponder, conversation_node
    from nodes.fallback import FallbackClarifier, fallback_node
    from nodes.schema_feasibility import SchemaFeasibilityChecker, schema_feasibility_node
    from nodes.sql_generator import SQLGenerator, sql_generator_node
    from nodes.sql_validator import SQLValidator, sql_validator_node
    from nodes.casino_api_executor import CasinoAPIExecutor, casino_api_executor_node
    from nodes.result_summarizer import ResultSummarizer, result_summarizer_node

__all__ = [
    "SupervisorNode",
    "supervisor_node",
    "ConversationResponder",
    "conversation_node",
    "FallbackClarifier",
    "fallback_node",
    "SchemaFeasibilityChecker",
    "schema_feasibility_node",
    "SQLGenerator",
    "sql_generator_node",
    "SQLValidator",
    "sql_validator_node",
    "CasinoAPIExecutor",
    "casino_api_executor_node",
    "ResultSummarizer",
    "result_summarizer_node",
]