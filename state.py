"""
State schema and type definitions for the LangGraph workflow.
Defines the minimal state needed to orchestrate the entire workflow.
"""
from typing import TypedDict, Literal, Optional, List, Dict, Any
from dataclasses import dataclass


# Type aliases for clarity
IntentType = Literal["conversation", "databricks", "fallback"]


class WorkflowState(TypedDict, total=False):
    """
    Minimal state schema for the LangGraph workflow.
    
    All nodes read from and write to this shared state.
    Keep mutations minimal for performance.
    """
    # Input
    user_input: str
    conversation_history: List[Dict[str, str]]  # [{"role": "user/assistant", "content": "..."}]
    
    # Schema metadata (read-only, pre-cached)
    schema_cache: Dict[str, Any]  # {"tables": [...], "columns": {...}}
    
    # Supervisor outputs
    intent: IntentType
    confidence: float
    
    # Databricks path
    feasibility_check: Dict[str, Any]  # {"feasible": bool, "tables": [...], "reason": str}
    generated_sql: Optional[str]
    validation_result: Dict[str, Any]  # {"valid": bool, "errors": [...]}
    query_result: Optional[List[Dict[str, Any]]]
    
    # Final output
    response: str
    
    # Metadata for routing and debugging
    current_node: str
    error_message: Optional[str]


@dataclass
class Message:
    """Simple message structure for conversation history."""
    role: str  # "user" or "assistant"
    content: str
    
    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass
class SupervisorOutput:
    """Structured output from the Supervisor node."""
    intent: IntentType
    confidence: float
    reasoning: Optional[str] = None


@dataclass
class SchemaTable:
    """Represents a cached table schema."""
    catalog: str
    schema: str
    table: str
    columns: List[str]
    column_types: Dict[str, str]
    description: Optional[str] = None
    
    @property
    def full_name(self) -> str:
        """
        Returns fully qualified table name.
        
        For PostgreSQL/Supabase with schema prefixes, we use schema.table format.
        For Databricks with Unity Catalog, we use catalog.schema.table format.
        
        If catalog and schema are the same, we only use schema.table to avoid duplication.
        """
        if self.catalog == self.schema:
            # Schema-based naming (e.g., hr_casino.employees)
            return f"{self.schema}.{self.table}"
        else:
            # Full catalog.schema.table naming
            return f"{self.catalog}.{self.schema}.{self.table}"


@dataclass
class SchemaCache:
    """
    Pre-cached schema metadata to avoid runtime lookups.
    This is loaded once at startup and reused.
    """
    tables: List[SchemaTable]
    last_updated: float  # Unix timestamp
    
    def get_table(self, table_name: str) -> Optional[SchemaTable]:
        """Find a table by name (case-insensitive partial match)."""
        table_lower = table_name.lower()
        for table in self.tables:
            if (table.table.lower() == table_lower or 
                table.full_name.lower() == table_lower):
                return table
        return None
    
    def search_tables(self, keyword: str) -> List[SchemaTable]:
        """Search tables by keyword in name or description."""
        keyword_lower = keyword.lower()
        results = []
        for table in self.tables:
            if (keyword_lower in table.table.lower() or
                (table.description and keyword_lower in table.description.lower())):
                results.append(table)
        return results
    
    def get_column_type(self, table_name: str, column_name: str) -> Optional[str]:
        """Get the type of a specific column."""
        table = self.get_table(table_name)
        if table:
            return table.column_types.get(column_name)
        return None

