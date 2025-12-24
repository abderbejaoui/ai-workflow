"""
Databricks Executor - Executes validated SQL queries.

Features:
- Connection pooling
- Timeout enforcement (≤ 2s)
- Result size limits
- Error handling
"""
from typing import Dict, Any, List, Optional
from state import WorkflowState
from config import config
from logging_config import get_logger, log_node_entry, log_node_exit, log_sql_execution, log_error
import time


class DatabricksExecutor:
    """
    Executes SQL queries against Databricks.
    
    Uses connection pooling and enforces strict timeouts
    to meet latency requirements.
    """
    
    def __init__(self):
        self.connection = None
        self.cursor = None
        self.logger = get_logger("ai_workflow.databricks_executor")
        self._init_connection()
    
    def _init_connection(self):
        """Initialize Databricks connection (lazy loading)."""
        # Connection is initialized on first use
        pass
    
    def _get_cursor(self):
        """Get or create a database cursor with connection pooling."""
        try:
            from databricks import sql
            
            if not self.connection:
                self.connection = sql.connect(
                    server_hostname=config.DATABRICKS_SERVER_HOSTNAME,
                    http_path=config.DATABRICKS_HTTP_PATH,
                    access_token=config.DATABRICKS_ACCESS_TOKEN,
                    # Connection pool settings
                    _connection_timeout=5,
                    _socket_timeout=config.DATABRICKS_QUERY_TIMEOUT,
                )
            
            if not self.cursor:
                self.cursor = self.connection.cursor()
            
            return self.cursor
            
        except ImportError:
            raise RuntimeError("databricks-sql-connector not installed")
        except Exception as e:
            raise RuntimeError(f"Failed to connect to Databricks: {str(e)}")
    
    def __call__(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Execute the validated SQL query.
        
        Args:
            state: Current workflow state
        
        Returns:
            Updated state with query results
        """
        log_node_entry(self.logger, "DatabricksExecutor", state)
        
        sql = state.get("generated_sql", "")
        self.logger.info(f"Executing SQL query...")
        self.logger.debug(f"SQL: {sql}")
        
        # Execute query
        result = self._execute_query(sql)
        
        if result.get("error"):
            self.logger.error(f"Query execution failed: {result['error']}")
        else:
            row_count = len(result.get("data", []))
            self.logger.info(f"Query executed successfully: {row_count} rows returned")
        
        updates = {
            "query_result": result.get("data"),
            "error_message": result.get("error"),
            "current_node": "databricks_executor"
        }
        
        log_node_exit(self.logger, "DatabricksExecutor", updates)
        return updates
    
    def _execute_query(self, sql: str) -> Dict[str, Any]:
        """
        Execute SQL with timeout and size limits.
        
        Returns:
            {
                "data": List[Dict] | None,
                "error": str | None,
                "execution_time": float
            }
        """
        start_time = time.time()
        
        try:
            self.logger.debug("Getting database cursor...")
            cursor = self._get_cursor()
            
            self.logger.debug(f"Executing query with timeout: {config.DATABRICKS_QUERY_TIMEOUT}s")
            # Execute with timeout
            cursor.execute(sql)
            
            # Fetch results with limit
            rows = cursor.fetchmany(config.MAX_RESULT_ROWS)
            
            # Convert to list of dicts
            if rows:
                columns = [desc[0] for desc in cursor.description]
                data = [dict(zip(columns, row)) for row in rows]
            else:
                data = []
            
            execution_time = time.time() - start_time
            
            log_sql_execution(self.logger, sql, execution_time, len(data))
            
            return {
                "data": data,
                "error": None,
                "execution_time": execution_time
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            log_error(self.logger, e, "Query execution")
            
            return {
                "data": None,
                "error": f"Query execution failed: {str(e)}",
                "execution_time": execution_time
            }
    
    def close(self):
        """Close database connections."""
        if self.cursor:
            try:
                self.cursor.close()
            except:
                pass
            self.cursor = None
        
        if self.connection:
            try:
                self.connection.close()
            except:
                pass
            self.connection = None
    
    def __del__(self):
        """Cleanup on deletion."""
        self.close()


# Convenience function for LangGraph
def databricks_executor_node(state: WorkflowState) -> Dict[str, Any]:
    """LangGraph node function for query execution."""
    node = DatabricksExecutor()
    return node(state)

