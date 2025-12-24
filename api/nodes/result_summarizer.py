"""
Result Summarizer - Summarizes query results efficiently.

Generates concise summaries without raw data dumps.
Token-efficient (≤ 150 tokens).
"""
from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage
import time

try:
    from ..state import WorkflowState
    from ..utils import get_main_llm, format_query_result
    from ..config import config
    from ..logging_config import get_logger, log_node_entry, log_node_exit
except ImportError:
    from state import WorkflowState
    from utils import get_main_llm, format_query_result
    from config import config
    from logging_config import get_logger, log_node_entry, log_node_exit


class ResultSummarizer:
    """
    Summarizes query results in natural language.
    
    Produces concise, informative summaries instead of
    dumping raw data to the user.
    """
    
    def __init__(self):
        # Use faster model for summarization (gpt-4o-mini is 10x faster)
        from langchain_openai import ChatOpenAI
        from config import config
        
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",  # Faster and cheaper than gpt-4o
            temperature=0.7,
            max_tokens=300
        )
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
        
        # Fast path: For simple "show me" queries, use basic summary
        simple_keywords = ['show', 'list', 'get', 'give', 'display']
        if any(keyword in user_input.lower() for keyword in simple_keywords) and len(results) <= 10:
            return self._basic_summary(results, user_input)
        
        # Format results for context
        result_preview = format_query_result(results, max_rows=5)
        
        system_prompt = f"""You are a data analyst presenting query results.

FORMAT YOUR RESPONSE EXACTLY LIKE THIS:

📊 **Results Summary**
Found X results. Here are the highlights:

**Top Results:**
1. [Name/ID]: [Key metric] - [Other relevant info]
2. [Name/ID]: [Key metric] - [Other relevant info]
3. [Name/ID]: [Key metric] - [Other relevant info]

**Key Insights:**
• [One interesting observation about the data]
• [Another insight if relevant]

RULES:
- Use numbered lists for data, NOT markdown tables with pipes (|)
- Keep each data point on ONE line
- Round numbers to 2 decimal places
- For names, show "FirstName LastName" format
- Maximum 5-7 highlighted results, then summarize the rest
- Be concise but informative"""
        
        user_message = f"""Question: {user_input}

Data returned ({len(results)} rows):
{result_preview}

Summarize this data clearly using numbered lists (NOT tables with | characters)."""
        
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
        
        # Create a nice formatted summary
        summary = f"📊 **Found {num_rows} result{'s' if num_rows != 1 else ''}**\n\n"
        
        # Show all rows if 10 or fewer, otherwise show first 5
        rows_to_show = min(num_rows, 5)
        
        for i, row in enumerate(results[:rows_to_show], 1):
            # Create a one-line summary for each row
            parts = []
            for key, value in row.items():
                # Format the key nicely
                nice_key = key.replace('_', ' ').title()
                # Format the value
                if isinstance(value, float):
                    formatted_val = f"{value:,.2f}"
                elif value is None:
                    formatted_val = "N/A"
                else:
                    formatted_val = str(value)
                parts.append(f"{nice_key}: {formatted_val}")
            
            summary += f"{i}. {' | '.join(parts[:4])}\n"  # Limit to first 4 columns per line
        
        if num_rows > rows_to_show:
            summary += f"\n... and {num_rows - rows_to_show} more results"
        
        return summary


# Convenience function for LangGraph
def result_summarizer_node(state: WorkflowState) -> Dict[str, Any]:
    """LangGraph node function for result summarization."""
    node = ResultSummarizer()
    return node(state)

