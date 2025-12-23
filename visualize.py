"""
Visualization utilities for the workflow graph.
"""
try:
    from IPython.display import Image, display
    IPYTHON_AVAILABLE = True
except ImportError:
    IPYTHON_AVAILABLE = False


def visualize_workflow():
    """
    Generate a visualization of the workflow graph.
    
    This is useful for understanding the structure in Jupyter notebooks.
    """
    from workflow import build_workflow
    
    workflow = build_workflow()
    
    try:
        # Try to generate PNG visualization
        png_data = workflow.get_graph().draw_mermaid_png()
        
        if IPYTHON_AVAILABLE:
            display(Image(png_data))
        else:
            print("Graph visualization generated (requires Jupyter/IPython to display)")
            
        return png_data
        
    except Exception as e:
        print(f"Could not generate visualization: {e}")
        print("\nWorkflow structure:")
        print_workflow_structure()


def print_workflow_structure():
    """Print text representation of the workflow."""
    structure = """
    Workflow Structure:
    
    START
      ↓
    [Supervisor] ← Intent Classification (gpt-4o-mini, <0.5s)
      ↓
      ├─→ [Conversation] → END
      │    └─ General chat handling
      │
      ├─→ [Fallback] → END
      │    └─ Clarifying questions
      │
      └─→ [Schema Feasibility] ← Databricks Path
           ↓ (if feasible)
           ├─→ [Fallback] → END (if not feasible)
           ↓
          [SQL Generator]
           ↓
          [SQL Validator]
           ↓ (if valid)
           ├─→ [Fallback] → END (if invalid)
           ↓
          [Databricks Executor] ← Timeout: 2s
           ↓ (if success)
           ├─→ [Fallback] → END (if error)
           ↓
          [Result Summarizer] ← Max 150 tokens
           ↓
          END
    
    Routing Rules:
    ─────────────────────────────────────────────────────────
    From Supervisor:
      • databricks + confidence ≥ 0.75 → Databricks Path
      • confidence < 0.75 → Fallback
      • conversation → Conversation
      • otherwise → Fallback
    
    From Schema Feasibility:
      • feasible=true → SQL Generator
      • feasible=false → Fallback
    
    From SQL Validator:
      • valid=true → Databricks Executor
      • valid=false → Fallback
    
    From Databricks Executor:
      • error=null → Result Summarizer
      • error present → Fallback
    """
    print(structure)


def print_node_details():
    """Print detailed information about each node."""
    details = """
    Node Details:
    ════════════════════════════════════════════════════════════
    
    1. SUPERVISOR NODE
       ├─ Model: gpt-4o-mini (fast & cheap)
       ├─ Input: user_input, history, schema_cache
       ├─ Output: intent, confidence
       ├─ Latency: <0.5s
       └─ Purpose: Route to correct execution path
    
    2. CONVERSATION NODE
       ├─ Model: gpt-4o
       ├─ Input: user_input, conversation_history
       ├─ Output: response
       ├─ Latency: ~1s
       └─ Purpose: Handle general chat
    
    3. FALLBACK NODE
       ├─ Model: gpt-4o
       ├─ Input: user_input, error context
       ├─ Output: clarification question
       ├─ Latency: ~1s
       └─ Purpose: Handle ambiguous queries
    
    4. SCHEMA FEASIBILITY CHECKER
       ├─ Model: gpt-4o
       ├─ Input: user_input, schema_cache
       ├─ Output: feasible, tables[], columns[]
       ├─ Latency: ~0.5s
       └─ Purpose: Validate query against schema
    
    5. SQL GENERATOR
       ├─ Model: gpt-4o
       ├─ Input: user_input, feasibility_check, schema
       ├─ Output: generated_sql
       ├─ Latency: ~1s
       └─ Purpose: Generate safe SQL
    
    6. SQL VALIDATOR
       ├─ Model: None (rule-based)
       ├─ Input: generated_sql, schema_cache
       ├─ Output: valid, errors[], warnings[]
       ├─ Latency: <0.1s
       └─ Purpose: Enforce safety guardrails
    
    7. DATABRICKS EXECUTOR
       ├─ Model: None (DB query)
       ├─ Input: generated_sql
       ├─ Output: query_result or error
       ├─ Latency: ≤2s (enforced)
       └─ Purpose: Execute SQL safely
    
    8. RESULT SUMMARIZER
       ├─ Model: gpt-4o
       ├─ Input: user_input, query_result, sql
       ├─ Output: response
       ├─ Latency: ~1s
       └─ Purpose: Natural language summary
    
    Total Worst-Case Latency:
    ────────────────────────────────────────────────────────────
    Supervisor (0.5s) + Feasibility (0.5s) + SQL Gen (1s) + 
    Validate (0.1s) + Execute (2s) + Summarize (1s) = ~5.1s
    
    Optimizations:
    ────────────────────────────────────────────────────────────
    • Pre-cached schema (no runtime discovery)
    • Connection pooling
    • Minimal prompt sizes
    • Early short-circuiting
    • Parallel-ready architecture
    """
    print(details)


if __name__ == "__main__":
    print("Workflow Visualization\n")
    print_workflow_structure()
    print()
    print_node_details()

