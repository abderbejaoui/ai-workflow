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


class ResultSummarizer:
    """
    Summarizes query results in natural language.
    
    Produces concise, informative summaries instead of
    dumping raw data to the user.
    """
    
    def __init__(self):
        self.llm = get_main_llm()
    
    def __call__(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Summarize query results for the user.
        
        Args:
            state: Current workflow state
        
        Returns:
            Updated state with final response
        """
        user_input = state.get("user_input", "")
        query_result = state.get("query_result", [])
        generated_sql = state.get("generated_sql", "")
        
        # Generate summary
        response = self._summarize_results(user_input, query_result, generated_sql)
        
        return {
            "response": response,
            "current_node": "result_summarizer"
        }
    
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

Summarize the query results in 2-3 sentences:
1. Key findings or insights
2. Notable patterns or values
3. Brief context

Keep it concise and informative. Maximum {config.RESULT_SUMMARY_MAX_TOKENS} tokens.

DO NOT:
- List all rows
- Dump raw data
- Repeat column names excessively"""
        
        user_message = f"""User asked: {user_input}

Query executed:
{sql}

Results ({len(results)} rows):
{result_preview}

Summarize these results."""
        
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
        
        summary = f"Found {num_rows} results"
        
        if columns:
            summary += f" with columns: {', '.join(columns)}"
        
        # Show first row as example
        if results:
            first_row = results[0]
            summary += f"\n\nExample: {first_row}"
        
        return summary


# Convenience function for LangGraph
def result_summarizer_node(state: WorkflowState) -> Dict[str, Any]:
    """LangGraph node function for result summarization."""
    node = ResultSummarizer()
    return node(state)

