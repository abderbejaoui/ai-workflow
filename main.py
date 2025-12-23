"""
Main Entry Point for the AI Workflow System.

Provides a simple interface for executing queries through the workflow.
"""
import sys
import time
import uuid
from typing import Dict, Any, List, Optional
from workflow import get_workflow, create_initial_state
from schema_loader import get_schema_loader
from config import config
from logging_config import (
    init_default_logger,
    get_logger,
    set_request_id,
    log_error
)


class AIWorkflowOrchestrator:
    """
    Main orchestrator for the AI workflow system.
    
    Handles:
    - Schema initialization
    - Workflow execution
    - Conversation history management
    - Performance monitoring
    """
    
    def __init__(self, use_mock_schema: bool = False):
        """
        Initialize the orchestrator.
        
        Args:
            use_mock_schema: If True, use mock schema for testing
        """
        # Initialize logging first
        init_default_logger()
        self.logger = get_logger("ai_workflow.orchestrator")
        
        self.logger.info("Initializing AI Workflow Orchestrator...")
        
        self.workflow = get_workflow()
        self.schema_loader = get_schema_loader()
        self.conversation_history: List[Dict[str, str]] = []
        
        # Load schema cache
        self._initialize_schema(use_mock_schema)
        
        self.logger.info("✓ AI Workflow Orchestrator initialized")
    
    def _initialize_schema(self, use_mock: bool = False):
        """Initialize schema cache."""
        self.logger.info("Loading schema metadata...")
        
        if use_mock:
            self.schema_loader.load_mock_schema()
            self.logger.info("✓ Mock schema loaded")
            print("✓ Mock schema loaded")
        else:
            # Load casino schema by default
            self.schema_loader.load_casino_schema()
            self.logger.info("✓ Casino database schema loaded (7 tables, 600K+ records)")
            print("✓ Casino database schema loaded")
            print("  Tables: customers, customer_behaviors, transactions, game_sessions, gaming_equipment, shifts, employees")
    
    def query(
        self,
        user_input: str,
        verbose: bool = False
    ) -> Dict[str, Any]:
        """
        Execute a query through the workflow.
        
        Args:
            user_input: User's natural language query
            verbose: If True, print execution details
        
        Returns:
            {
                "response": str,
                "execution_time": float,
                "path_taken": str,
                "sql": Optional[str]
            }
        """
        start_time = time.time()
        
        # Generate unique request ID for tracking
        request_id = str(uuid.uuid4())[:8]
        set_request_id(request_id)
        
        self.logger.info("="*70)
        self.logger.info(f"NEW QUERY [ID: {request_id}]")
        self.logger.info(f"User input: {user_input}")
        self.logger.info("="*70)
        
        # Create initial state
        initial_state = create_initial_state(
            user_input=user_input,
            conversation_history=self.conversation_history,
            schema_cache=self.schema_loader.to_dict()
        )
        
        if verbose:
            print(f"\n{'='*60}")
            print(f"Query: {user_input}")
            print(f"Request ID: {request_id}")
            print(f"{'='*60}")
        
        # Execute workflow
        try:
            self.logger.info("Starting workflow execution...")
            final_state = self.workflow.invoke(initial_state)
            self.logger.info("Workflow execution completed")
            
            response = final_state.get("response", "")
            intent = final_state.get("intent", "unknown")
            confidence = final_state.get("confidence", 0.0)
            sql = final_state.get("generated_sql")
            current_node = final_state.get("current_node", "unknown")
            
            execution_time = time.time() - start_time
            
            self.logger.info(
                f"Query completed successfully in {execution_time:.3f}s",
                extra={
                    'execution_time': execution_time,
                    'intent': intent,
                    'confidence': confidence,
                    'path': current_node,
                    'request_id': request_id
                }
            )
            
            # Update conversation history
            self.conversation_history.append({"role": "user", "content": user_input})
            self.conversation_history.append({"role": "assistant", "content": response})
            
            # Keep history manageable
            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-20:]
            
            if verbose:
                print(f"\nIntent: {intent} (confidence: {confidence:.2f})")
                print(f"Path: {current_node}")
                if sql:
                    print(f"\n{'='*60}")
                    print(f"SQL Query:")
                    print(f"{sql}")
                    print(f"{'='*60}")
                print(f"Execution time: {execution_time:.3f}s")
                print(f"\nResponse: {response}")
                print(f"{'='*60}\n")
            
            return {
                "response": response,
                "execution_time": execution_time,
                "path_taken": current_node,
                "intent": intent,
                "confidence": confidence,
                "sql": sql,
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Error executing workflow: {str(e)}"
            
            log_error(self.logger, e, "Workflow execution")
            
            if verbose:
                print(f"\n❌ {error_msg}")
                print(f"Execution time: {execution_time:.3f}s")
                print(f"{'='*60}\n")
            
            return {
                "response": "I apologize, but I encountered an error processing your request.",
                "execution_time": execution_time,
                "path_taken": "error",
                "intent": "unknown",
                "confidence": 0.0,
                "sql": None,
                "error": str(e)
            }
    
    def reset_conversation(self):
        """Reset conversation history."""
        self.conversation_history = []
        print("✓ Conversation history reset")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get system statistics."""
        schema_cache = self.schema_loader.get_cache()
        
        return {
            "tables_cached": len(schema_cache.tables) if schema_cache else 0,
            "conversation_length": len(self.conversation_history),
            "cache_age_seconds": time.time() - schema_cache.last_updated if schema_cache else 0,
        }


def main():
    """CLI interface for testing the workflow."""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Workflow Orchestrator")
    parser.add_argument("--mock", action="store_true", help="Use mock schema")
    parser.add_argument("--query", type=str, help="Single query to execute")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")
    args = parser.parse_args()
    
    # Validate config
    if not config.validate():
        print("❌ Configuration incomplete. Please set API keys in .env file")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("AI WORKFLOW ORCHESTRATOR")
    print("="*60)
    
    # Initialize orchestrator
    orchestrator = AIWorkflowOrchestrator(use_mock_schema=args.mock)
    
    # Show statistics
    stats = orchestrator.get_statistics()
    print(f"\nSystem ready:")
    print(f"  - Tables cached: {stats['tables_cached']}")
    print(f"  - Confidence threshold: {config.DATABRICKS_CONFIDENCE_THRESHOLD}")
    print(f"  - Query timeout: {config.DATABRICKS_QUERY_TIMEOUT}s")
    print()
    
    # Single query mode
    if args.query:
        result = orchestrator.query(args.query, verbose=True)
        sys.exit(0)
    
    # Interactive mode
    if args.interactive:
        print("Interactive mode (type 'exit' to quit, 'reset' to clear history)")
        print()
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() == "exit":
                    print("Goodbye!")
                    break
                
                if user_input.lower() == "reset":
                    orchestrator.reset_conversation()
                    continue
                
                result = orchestrator.query(user_input, verbose=False)
                print(f"\nAssistant: {result['response']}")
                print(f"[{result['execution_time']:.2f}s | {result['path_taken']}]\n")
                
            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")
    else:
        print("Use --query 'your question' or --interactive mode")
        print("\nExamples:")
        print("  python main.py --mock --query 'Show me all customers'")
        print("  python main.py --mock --interactive")


if __name__ == "__main__":
    main()

