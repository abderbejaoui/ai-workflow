"""
Result Summarizer - Summarizes query results efficiently.

Generates concise summaries without raw data dumps.
Token-efficient (≤ 150 tokens).
"""
from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage
from state import WorkflowState
from utils import get_main_llm, format_query_result
from config import config
from logging_config import get_logger, log_node_entry, log_node_exit
import time


class ResultSummarizer:
    """
    Summarizes query results in natural language.
    
    Produces concise, informative summaries instead of
    dumping raw data to the user.
    """
    
    def __init__(self):
        self.llm = get_main_llm()
        self.logger = get_logger("ai_workflow.result_summarizer")
    
    def __call__(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Summarize query results for the user.
        
        Args:
            state: Current workflow state
        
        Returns:
            Updated state with final response
        """
        log_node_entry(self.logger, "ResultSummarizer", state)
        start_time = time.time()
        
        user_input = state.get("user_input", "")
        query_result = state.get("query_result", [])
        generated_sql = state.get("generated_sql", "")
        
        row_count = len(query_result) if query_result else 0
        self.logger.info(f"Summarizing {row_count} rows for user")
        
        # Log the actual results for debugging
        if query_result:
            self.logger.info("="*70)
            self.logger.info("QUERY RESULTS TO SUMMARIZE:")
            self.logger.info("="*70)
            for i, row in enumerate(query_result[:5], 1):
                self.logger.info(f"Row {i}: {row}")
            if len(query_result) > 5:
                self.logger.info(f"... and {len(query_result) - 5} more rows")
            self.logger.info("="*70)
        else:
            self.logger.warning("No results to summarize - query_result is empty or None")
            self.logger.debug(f"query_result type: {type(query_result)}, value: {query_result}")
        
        # Generate summary
        response = self._summarize_results(user_input, query_result, generated_sql)
        
        execution_time = time.time() - start_time
        self.logger.info(f"Summary generated in {execution_time:.3f}s")
        
        updates = {
            "response": response,
            "current_node": "result_summarizer"
        }
        
        log_node_exit(self.logger, "ResultSummarizer", updates)
        return updates
    
    def _summarize_results(
        self,
        user_input: str,
        results: List[Dict[str, Any]],
        sql: str
    ) -> str:
        """Generate a concise summary of the results."""
        
        if not results:
            return "The query executed successfully but returned no results."
        
        # Format results for context
        result_preview = format_query_result(results, max_rows=5)
        
        system_prompt = f"""You are a data analyst presenting query results to a user.

Summarize the query results in a clear, informative way:
1. State how many rows were returned
2. Show the actual data (format it nicely as a table or list)
3. Provide any notable insights

Keep it clear and user-friendly. Maximum {config.RESULT_SUMMARY_MAX_TOKENS} tokens.

Format the actual data so users can see what was returned. Include ALL returned rows if there are 10 or fewer."""
        
        user_message = f"""User asked: {user_input}

Query executed:
{sql}

Results ({len(results)} rows):
{result_preview}

Present these results to the user in a clear, readable format."""
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_message)
            ]
            
            response = self.llm.invoke(messages)
            summary = response.content.strip()
            
            # Add row count context
            if len(results) >= config.MAX_RESULT_ROWS:
                summary += f"\n\n(Showing first {config.MAX_RESULT_ROWS} results)"
            
            return summary
            
        except Exception as e:
            # Fallback to basic summary
            return self._basic_summary(results, user_input)
    
    def _basic_summary(self, results: List[Dict[str, Any]], user_input: str) -> str:
        """Generate a basic summary when LLM fails."""
        num_rows = len(results)
        
        if num_rows == 0:
            return "No results found."
        
        columns = list(results[0].keys()) if results else []
        
        summary = f"Query returned {num_rows} row{'s' if num_rows != 1 else ''}:\n\n"
        
        # Show all rows if 10 or fewer, otherwise show first 5
        rows_to_show = min(num_rows, 10)
        
        for i, row in enumerate(results[:rows_to_show], 1):
            summary += f"Row {i}:\n"
            for key, value in row.items():
                summary += f"  {key}: {value}\n"
            summary += "\n"
        
        if num_rows > rows_to_show:
            summary += f"... and {num_rows - rows_to_show} more rows"
        
        return summary


# Convenience function for LangGraph
def result_summarizer_node(state: WorkflowState) -> Dict[str, Any]:
    """LangGraph node function for result summarization."""
    node = ResultSummarizer()
    return node(state)

