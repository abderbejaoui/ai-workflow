"""
Casino API Executor - Executes SQL queries via HTTP API.

Replaces Databricks executor with HTTP API calls to the casino database.
"""
from typing import Dict, Any, List, Optional
from state import WorkflowState
from config import config
from logging_config import get_logger, log_node_entry, log_node_exit, log_sql_execution, log_error
import time
import requests


class CasinoAPIExecutor:
    """
    Executes SQL queries via HTTP API instead of Databricks.
    
    Makes POST requests to the casino database API endpoint.
    """
    
    def __init__(self):
        self.logger = get_logger("ai_workflow.casino_api_executor")
        self.api_url = config.CASINO_API_URL
        self.timeout = config.QUERY_TIMEOUT
    
    def __call__(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Execute the validated SQL query via API.
        
        Args:
            state: Current workflow state
        
        Returns:
            Updated state with query results
        """
        log_node_entry(self.logger, "CasinoAPIExecutor", state)
        
        sql = state.get("generated_sql", "")
        self.logger.info("="*70)
        self.logger.info(f"EXECUTING SQL QUERY:")
        self.logger.info(f"{sql}")
        self.logger.info("="*70)
        self.logger.debug(f"API URL: {self.api_url}")
        
        # Execute query
        result = self._execute_query(sql)
        
        # Safety check: ensure result is not None
        if result is None:
            self.logger.error("Query execution returned None - unexpected error")
            result = {
                "data": None,
                "error": "Query execution returned unexpected None result",
                "execution_time": 0
            }
        
        if result.get("error"):
            self.logger.error(f"Query execution failed: {result['error']}")
        else:
            data = result.get("data", [])
            row_count = len(data) if data is not None else 0
            self.logger.info(f"Query executed successfully: {row_count} rows returned")
        
        updates = {
            "query_result": result.get("data"),
            "error_message": result.get("error"),
            "current_node": "casino_api_executor"
        }
        
        log_node_exit(self.logger, "CasinoAPIExecutor", updates)
        return updates
    
    def _execute_query(self, sql: str) -> Dict[str, Any]:
        """
        Execute SQL via HTTP API with timeout and error handling.
        
        Args:
            sql: SQL query to execute
        
        Returns:
            {
                "data": List[Dict] | None,
                "error": str | None,
                "execution_time": float
            }
            
        Note: This method ALWAYS returns a dict, never None.
        """
        start_time = time.time()
        
        try:
            self.logger.debug(f"Making POST request to {self.api_url}")
            
            # Prepare request body
            payload = {
                "sql_query": sql,
                "params": None
            }
            
            # Make API request
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=self.timeout,
                headers={'Content-Type': 'application/json'}
            )
            
            execution_time = time.time() - start_time
            
            # Check response status
            if response.status_code != 200:
                error_msg = f"API returned status {response.status_code}: {response.text}"
                self.logger.error(error_msg)
                return {
                    "data": None,
                    "error": error_msg,
                    "execution_time": execution_time
                }
            
            # Parse response
            response_data = response.json()
            
            # Log the raw response for debugging (using INFO so it shows in terminal)
            self.logger.info(f"API Response - Type: {type(response_data)}")
            self.logger.info(f"API Response - Content: {response_data}")
            
            # Handle different response formats
            if isinstance(response_data, dict):
                self.logger.info(f"Response is a dict with keys: {list(response_data.keys())}")
                
                # Check if there's an error in the response (error is not None)
                if response_data.get("error"):  # Only if error has a value
                    return {
                        "data": None,
                        "error": response_data["error"],
                        "execution_time": execution_time
                    }
                
                # Extract data - use get() with None default to avoid issues with empty lists
                data = response_data.get("data")
                if data is None:
                    data = response_data.get("results")
                if data is None:
                    data = response_data.get("rows")
                
                self.logger.info(f"Extracted data from response (type: {type(data)}): {data}")
                
                if data is None:
                    # Log what keys are available
                    self.logger.warning(f"No standard data keys found in response. Available keys: {list(response_data.keys())}")
                    # Check if response itself looks like a single result
                    if any(key in response_data for key in ['employee_id', 'customer_id', 'transaction_id', 'session_id']):
                        self.logger.info("Response appears to be a single row, wrapping in list")
                    data = [response_data]
                    else:
                        # If no specific key and not a single row, return empty
                        data = []
            
            elif isinstance(response_data, list):
                self.logger.info(f"Response is a list with {len(response_data)} items")
                data = response_data
            
            else:
                self.logger.warning(f"Unexpected response type: {type(response_data)}")
                data = []
            
            # Limit results
            if len(data) > config.MAX_RESULT_ROWS:
                self.logger.warning(f"Truncating results from {len(data)} to {config.MAX_RESULT_ROWS} rows")
                data = data[:config.MAX_RESULT_ROWS]
            
            log_sql_execution(self.logger, sql, execution_time, len(data))
            
            # Print results to console for visibility
            self.logger.info("="*70)
            self.logger.info(f"QUERY RESULTS: {len(data)} rows returned")
            self.logger.info("="*70)
            if data:
                # Show first few rows
                for i, row in enumerate(data[:5], 1):
                    self.logger.info(f"Row {i}: {row}")
                if len(data) > 5:
                    self.logger.info(f"... and {len(data) - 5} more rows")
            else:
                self.logger.info("No rows returned")
            self.logger.info("="*70)
            
            return {
                "data": data,
                "error": None,
                "execution_time": execution_time
            }
            
        except requests.exceptions.Timeout:
            execution_time = time.time() - start_time
            error_msg = f"Query timeout after {self.timeout}s"
            self.logger.error(error_msg)
            
            return {
                "data": None,
                "error": error_msg,
                "execution_time": execution_time
            }
            
        except requests.exceptions.RequestException as e:
            execution_time = time.time() - start_time
            error_msg = f"API request failed: {str(e)}"
            log_error(self.logger, e, "API request")
            
            return {
                "data": None,
                "error": error_msg,
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


# Convenience function for LangGraph
def casino_api_executor_node(state: WorkflowState) -> Dict[str, Any]:
    """LangGraph node function for API query execution."""
    node = CasinoAPIExecutor()
    return node(state)

