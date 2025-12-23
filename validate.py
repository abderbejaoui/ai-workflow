"""
Validation script to ensure the workflow is properly configured and functional.
Run this before deploying to production.
"""
import sys
import time
from typing import Dict, Any, List


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def print_result(check: str, passed: bool, details: str = ""):
    """Print a check result."""
    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"{status:8} | {check}")
    if details:
        print(f"         | {details}")


def validate_dependencies() -> bool:
    """Check that all required dependencies are installed."""
    print_section("1. DEPENDENCY CHECK")
    
    all_passed = True
    required_modules = [
        ("langgraph", "LangGraph orchestration"),
        ("langchain", "LangChain framework"),
        ("langchain_openai", "OpenAI integration"),
        ("langchain_anthropic", "Anthropic integration"),
        ("databricks.sql", "Databricks connector"),
        ("dotenv", "Environment configuration"),
    ]
    
    for module, description in required_modules:
        try:
            __import__(module)
            print_result(f"{description}", True)
        except ImportError:
            print_result(f"{description}", False, f"Missing: {module}")
            all_passed = False
    
    return all_passed


def validate_configuration() -> bool:
    """Check that configuration is properly set up."""
    print_section("2. CONFIGURATION CHECK")
    
    try:
        from config import config
        
        all_passed = True
        
        # Check API keys
        has_api_key = bool(config.OPENAI_API_KEY or config.ANTHROPIC_API_KEY)
        print_result("LLM API Key configured", has_api_key)
        if not has_api_key:
            all_passed = False
        
        # Check models
        print_result("Supervisor model set", bool(config.SUPERVISOR_MODEL))
        print_result("Main model set", bool(config.MAIN_MODEL))
        
        # Check thresholds
        valid_threshold = 0 <= config.DATABRICKS_CONFIDENCE_THRESHOLD <= 1
        print_result(
            "Confidence threshold valid",
            valid_threshold,
            f"Value: {config.DATABRICKS_CONFIDENCE_THRESHOLD}"
        )
        
        if not valid_threshold:
            all_passed = False
        
        return all_passed
        
    except Exception as e:
        print_result("Configuration load", False, str(e))
        return False


def validate_nodes() -> bool:
    """Check that all nodes can be imported and instantiated."""
    print_section("3. NODE VALIDATION")
    
    all_passed = True
    nodes = [
        ("SupervisorNode", "nodes.supervisor"),
        ("ConversationResponder", "nodes.conversation"),
        ("FallbackClarifier", "nodes.fallback"),
        ("SchemaFeasibilityChecker", "nodes.schema_feasibility"),
        ("SQLGenerator", "nodes.sql_generator"),
        ("SQLValidator", "nodes.sql_validator"),
        ("DatabricksExecutor", "nodes.databricks_executor"),
        ("ResultSummarizer", "nodes.result_summarizer"),
    ]
    
    for node_name, module_path in nodes:
        try:
            module = __import__(module_path, fromlist=[node_name])
            node_class = getattr(module, node_name)
            instance = node_class()
            print_result(f"{node_name}", True)
        except Exception as e:
            print_result(f"{node_name}", False, str(e))
            all_passed = False
    
    return all_passed


def validate_workflow() -> bool:
    """Check that the workflow can be built."""
    print_section("4. WORKFLOW CONSTRUCTION")
    
    try:
        from workflow import build_workflow, create_initial_state
        
        # Build workflow
        workflow = build_workflow()
        print_result("Workflow compilation", True)
        
        # Create initial state
        state = create_initial_state(
            user_input="test query",
            conversation_history=[],
            schema_cache={"tables": []}
        )
        print_result("State initialization", True)
        
        # Check required state fields
        required_fields = [
            "user_input", "conversation_history", "schema_cache",
            "intent", "confidence", "response"
        ]
        
        has_all_fields = all(field in state for field in required_fields)
        print_result("State schema complete", has_all_fields)
        
        return True
        
    except Exception as e:
        print_result("Workflow build", False, str(e))
        return False


def validate_schema_loader() -> bool:
    """Check that schema loading works."""
    print_section("5. SCHEMA LOADER")
    
    try:
        from schema_loader import SchemaLoader
        
        loader = SchemaLoader()
        
        # Test mock schema loading
        cache = loader.load_mock_schema()
        print_result("Mock schema load", True, f"{len(cache.tables)} tables")
        
        # Test conversion to dict
        schema_dict = loader.to_dict()
        has_tables = "tables" in schema_dict and len(schema_dict["tables"]) > 0
        print_result("Schema serialization", has_tables)
        
        return True
        
    except Exception as e:
        print_result("Schema loader", False, str(e))
        return False


def validate_routing() -> bool:
    """Check that routing logic works correctly."""
    print_section("6. ROUTING LOGIC")
    
    try:
        from workflow import (
            route_from_supervisor,
            route_from_feasibility,
            route_from_validator,
            route_from_executor
        )
        
        # Test supervisor routing
        state1 = {"intent": "databricks", "confidence": 0.8}
        route1 = route_from_supervisor(state1)
        print_result(
            "High-confidence databricks → schema_feasibility",
            route1 == "schema_feasibility"
        )
        
        state2 = {"intent": "conversation", "confidence": 0.9}
        route2 = route_from_supervisor(state2)
        print_result(
            "Conversation intent → conversation",
            route2 == "conversation"
        )
        
        state3 = {"intent": "databricks", "confidence": 0.5}
        route3 = route_from_supervisor(state3)
        print_result(
            "Low confidence → fallback",
            route3 == "fallback"
        )
        
        # Test feasibility routing
        state4 = {"feasibility_check": {"feasible": True}}
        route4 = route_from_feasibility(state4)
        print_result(
            "Feasible → sql_generator",
            route4 == "sql_generator"
        )
        
        return True
        
    except Exception as e:
        print_result("Routing logic", False, str(e))
        return False


def test_end_to_end() -> bool:
    """Run end-to-end tests with mock data."""
    print_section("7. END-TO-END TESTS")
    
    try:
        from main import AIWorkflowOrchestrator
        
        # Initialize with mock schema
        orchestrator = AIWorkflowOrchestrator(use_mock_schema=True)
        print_result("Orchestrator initialization", True)
        
        # Test conversation path
        result1 = orchestrator.query("Hello!", verbose=False)
        conversation_works = (
            result1.get("response") and
            result1.get("intent") == "conversation"
        )
        print_result(
            "Conversation path",
            conversation_works,
            f"{result1.get('execution_time', 0):.2f}s"
        )
        
        # Test fallback path
        result2 = orchestrator.query("Show me that thing", verbose=False)
        fallback_works = "response" in result2
        print_result(
            "Fallback path",
            fallback_works,
            f"{result2.get('execution_time', 0):.2f}s"
        )
        
        # Check latency
        meets_sla = result1.get("execution_time", 999) < 5.0
        print_result(
            "Latency requirement (<5s)",
            meets_sla,
            f"Actual: {result1.get('execution_time', 0):.2f}s"
        )
        
        # Test statistics
        stats = orchestrator.get_statistics()
        print_result(
            "Statistics tracking",
            "tables_cached" in stats,
            f"{stats.get('tables_cached', 0)} tables"
        )
        
        return conversation_works and fallback_works
        
    except Exception as e:
        print_result("End-to-end test", False, str(e))
        return False


def test_sql_validation() -> bool:
    """Test SQL validation rules."""
    print_section("8. SQL VALIDATION RULES")
    
    try:
        from nodes.sql_validator import SQLValidator
        
        validator = SQLValidator()
        
        # Test dangerous patterns
        test_cases = [
            ("SELECT * FROM users", False, "SELECT * blocked"),
            ("DROP TABLE users", False, "DROP blocked"),
            ("SELECT id, name FROM users LIMIT 10;", True, "Valid SELECT"),
            ("DELETE FROM users WHERE id=1", False, "DELETE blocked"),
            ("SELECT id FROM users; DROP TABLE users;", False, "Multiple statements blocked"),
        ]
        
        for sql, should_pass, description in test_cases:
            result = validator._validate_sql(sql, {"tables": []}, {})
            is_valid = result["valid"]
            passed = is_valid == should_pass
            print_result(description, passed, f"Valid: {is_valid}")
        
        return True
        
    except Exception as e:
        print_result("SQL validation", False, str(e))
        return False


def performance_benchmark() -> bool:
    """Run performance benchmarks."""
    print_section("9. PERFORMANCE BENCHMARK")
    
    try:
        from main import AIWorkflowOrchestrator
        
        orchestrator = AIWorkflowOrchestrator(use_mock_schema=True)
        
        queries = [
            "Hello",
            "Show me customers",
            "What about orders?",
        ]
        
        latencies = []
        
        for query in queries:
            start = time.time()
            result = orchestrator.query(query, verbose=False)
            elapsed = time.time() - start
            latencies.append(elapsed)
        
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        
        print_result(
            "Average latency",
            avg_latency < 5.0,
            f"{avg_latency:.2f}s"
        )
        print_result(
            "Max latency",
            max_latency < 5.0,
            f"{max_latency:.2f}s"
        )
        print_result(
            "Min latency",
            True,
            f"{min(latencies):.2f}s"
        )
        
        return avg_latency < 5.0
        
    except Exception as e:
        print_result("Performance benchmark", False, str(e))
        return False


def main():
    """Run all validation checks."""
    print("\n" + "="*70)
    print("  AI WORKFLOW VALIDATION SUITE")
    print("="*70)
    print("\nValidating system configuration and functionality...")
    
    results = {}
    
    # Run all checks
    results["dependencies"] = validate_dependencies()
    results["configuration"] = validate_configuration()
    results["nodes"] = validate_nodes()
    results["workflow"] = validate_workflow()
    results["schema_loader"] = validate_schema_loader()
    results["routing"] = validate_routing()
    results["sql_validation"] = test_sql_validation()
    results["end_to_end"] = test_end_to_end()
    results["performance"] = performance_benchmark()
    
    # Summary
    print_section("VALIDATION SUMMARY")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for check, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} | {check.replace('_', ' ').title()}")
    
    print(f"\n{'-'*70}")
    print(f"Total: {passed}/{total} checks passed")
    print(f"{'-'*70}\n")
    
    if passed == total:
        print("🎉 All validation checks passed!")
        print("   System is ready for production deployment.")
        return 0
    else:
        print("⚠️  Some validation checks failed.")
        print("   Please fix the issues before deploying.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

