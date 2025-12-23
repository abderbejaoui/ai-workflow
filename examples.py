"""
Example usage and testing scripts for the AI Workflow system.
"""
from main import AIWorkflowOrchestrator
import time


def test_conversation_path():
    """Test general conversation handling."""
    print("\n" + "="*60)
    print("TEST: Conversation Path")
    print("="*60)
    
    orchestrator = AIWorkflowOrchestrator(use_mock_schema=True)
    
    queries = [
        "Hello! How are you?",
        "What can you help me with?",
        "Thank you for your help",
    ]
    
    for query in queries:
        result = orchestrator.query(query, verbose=False)
        print(f"\nQ: {query}")
        print(f"A: {result['response']}")
        print(f"   [Intent: {result['intent']}, Confidence: {result['confidence']:.2f}, Time: {result['execution_time']:.2f}s]")


def test_databricks_path():
    """Test SQL query generation and execution."""
    print("\n" + "="*60)
    print("TEST: Databricks Query Path")
    print("="*60)
    
    orchestrator = AIWorkflowOrchestrator(use_mock_schema=True)
    
    queries = [
        "Show me all customers",
        "What are the top 5 orders by total amount?",
        "List products in the Electronics category",
        "How many customers are from USA?",
    ]
    
    for query in queries:
        result = orchestrator.query(query, verbose=False)
        print(f"\nQ: {query}")
        print(f"A: {result['response']}")
        if result.get('sql'):
            print(f"   SQL: {result['sql'][:80]}...")
        print(f"   [Path: {result['path_taken']}, Time: {result['execution_time']:.2f}s]")


def test_fallback_path():
    """Test fallback/clarification handling."""
    print("\n" + "="*60)
    print("TEST: Fallback Path")
    print("="*60)
    
    orchestrator = AIWorkflowOrchestrator(use_mock_schema=True)
    
    queries = [
        "Show me that thing",
        "What about yesterday?",
        "Give me the data",
    ]
    
    for query in queries:
        result = orchestrator.query(query, verbose=False)
        print(f"\nQ: {query}")
        print(f"A: {result['response']}")
        print(f"   [Intent: {result['intent']}, Confidence: {result['confidence']:.2f}, Time: {result['execution_time']:.2f}s]")


def test_performance():
    """Test performance and latency."""
    print("\n" + "="*60)
    print("TEST: Performance")
    print("="*60)
    
    orchestrator = AIWorkflowOrchestrator(use_mock_schema=True)
    
    # Test multiple queries
    queries = [
        "Hello",
        "Show me all customers",
        "What are total sales?",
    ]
    
    total_time = 0
    results = []
    
    for query in queries:
        start = time.time()
        result = orchestrator.query(query, verbose=False)
        elapsed = time.time() - start
        total_time += elapsed
        results.append(elapsed)
        print(f"\n{query}: {elapsed:.3f}s")
    
    print(f"\n{'='*60}")
    print(f"Average latency: {sum(results)/len(results):.3f}s")
    print(f"Max latency: {max(results):.3f}s")
    print(f"Min latency: {min(results):.3f}s")
    print(f"Total time: {total_time:.3f}s")
    print(f"{'='*60}")
    
    # Check if meeting requirements
    avg_latency = sum(results) / len(results)
    if avg_latency <= 5.0:
        print("✓ Meeting latency target (<5s)")
    else:
        print(f"⚠ Exceeding latency target: {avg_latency:.2f}s")


def test_conversation_flow():
    """Test multi-turn conversation."""
    print("\n" + "="*60)
    print("TEST: Multi-turn Conversation")
    print("="*60)
    
    orchestrator = AIWorkflowOrchestrator(use_mock_schema=True)
    
    conversation = [
        "Show me all customers",
        "What about their orders?",
        "Which products are most popular?",
    ]
    
    for i, query in enumerate(conversation, 1):
        result = orchestrator.query(query, verbose=False)
        print(f"\nTurn {i}")
        print(f"User: {query}")
        print(f"Assistant: {result['response']}")
        print(f"[History size: {len(orchestrator.conversation_history)}]")


def run_all_tests():
    """Run all test suites."""
    print("\n" + "="*60)
    print("RUNNING ALL TESTS")
    print("="*60)
    
    test_conversation_path()
    test_fallback_path()
    # Uncomment if you want to test Databricks queries with mock data
    # test_databricks_path()
    test_conversation_flow()
    test_performance()
    
    print("\n" + "="*60)
    print("ALL TESTS COMPLETED")
    print("="*60)


if __name__ == "__main__":
    run_all_tests()

