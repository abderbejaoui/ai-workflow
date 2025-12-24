"""
FastAPI application for AI Workflow - Vercel Serverless Function
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import time
import traceback

# Try relative imports first (for Vercel), then absolute (for local)
try:
    # Vercel deployment - use relative imports
    from .workflow import get_workflow, create_initial_state
    from .schema_loader import get_schema_loader
    from .config import config
    from .logging_config import init_default_logger, get_logger
except ImportError:
    # Local development - use absolute imports
    import sys
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    for path in [current_dir, parent_dir]:
        if path not in sys.path:
            sys.path.insert(0, path)
    
    from workflow import get_workflow, create_initial_state
    from schema_loader import get_schema_loader
    from config import config
    from logging_config import init_default_logger, get_logger

# Initialize FastAPI app
app = FastAPI(
    title="AI Workflow API",
    description="Natural language to SQL query API for casino database",
    version="1.0.0"
)

# Mount static files (if public directory exists)
public_dir = os.path.join(os.path.dirname(__file__), "public")
if os.path.exists(public_dir):
    app.mount("/static", StaticFiles(directory=public_dir), name="static")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize logging
init_default_logger()
logger = get_logger("ai_workflow.api")

# Global state
_workflow = None
_schema_cache = None
_conversation_history: Dict[str, List[Dict[str, str]]] = {}  # session_id -> history


class QueryRequest(BaseModel):
    """Request model for query endpoint."""
    query: str
    session_id: Optional[str] = "default"  # For session-based history
    conversation_history: Optional[List[Dict[str, str]]] = None  # Optional override


class QueryResponse(BaseModel):
    """Response model for query endpoint."""
    response: str
    sql: Optional[str] = None
    results: Optional[List[Dict[str, Any]]] = None
    execution_time: float
    path_taken: str
    error: Optional[str] = None
    conversation_history: Optional[List[Dict[str, str]]] = None  # Return updated history


def initialize_system():
    """Initialize workflow and schema cache."""
    global _workflow, _schema_cache
    
    if _workflow is None:
        logger.info("Initializing AI Workflow system...")
        _workflow = get_workflow()
        
        schema_loader = get_schema_loader()
        schema_loader.load_casino_schema()
        _schema_cache = schema_loader.to_dict()
        
        logger.info("✓ System initialized")


@app.on_event("startup")
async def startup_event():
    """Initialize system on startup."""
    initialize_system()


@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint - serve the test UI."""
    html_path = os.path.join(os.path.dirname(__file__), "public", "index.html")
    
    if os.path.exists(html_path):
        with open(html_path, "r") as f:
            return f.read()
    else:
        # Fallback if HTML file doesn't exist - return simple HTML
        return """
        <!DOCTYPE html>
        <html>
        <head><title>AI Workflow API</title></head>
        <body style="font-family: Arial, sans-serif; padding: 40px; max-width: 600px; margin: 0 auto;">
            <h1>🎰 AI Workflow API</h1>
            <p>The API is running successfully!</p>
            <h3>Available Endpoints:</h3>
            <ul>
                <li><a href="/docs">/docs</a> - API Documentation</li>
                <li><a href="/health">/health</a> - Health Check</li>
                <li><a href="/schema">/schema</a> - Database Schema</li>
                <li><a href="/examples">/examples</a> - Example Queries</li>
            </ul>
            <h3>Query Endpoint:</h3>
            <code>POST /query</code> with JSON body: <code>{"query": "your question"}</code>
        </body>
        </html>
        """


@app.get("/health")
async def health():
    """Health check endpoint."""
    api_key = config.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY", "")
    return {
        "status": "healthy",
        "tables_cached": len(_schema_cache.get("tables", [])) if _schema_cache else 0,
        "openai_configured": bool(api_key and len(api_key) > 10),
        "openai_key_prefix": api_key[:15] + "..." if api_key else "NOT SET"
    }


@app.get("/schema")
async def get_schema():
    """Get database schema information."""
    if not _schema_cache:
        raise HTTPException(status_code=500, detail="Schema not loaded")
    
    return {
        "tables": [
            {
                "name": table["full_name"],
                "columns": table["columns"],
                "description": table.get("description", "")
            }
            for table in _schema_cache.get("tables", [])
        ]
    }


@app.post("/query", response_model=QueryResponse)
async def execute_query(request: QueryRequest):
    """
    Execute a natural language query.
    
    Args:
        request: Query request with natural language query
    
    Returns:
        Query response with results and metadata
    """
    global _conversation_history
    
    try:
        # Ensure system is initialized
        if _workflow is None:
            initialize_system()
        
        session_id = request.session_id or "default"
        
        # Get or create conversation history for this session
        if request.conversation_history is not None:
            # Use provided history (client override)
            history = request.conversation_history
        else:
            # Use server-side history
            history = _conversation_history.get(session_id, [])
        
        logger.info(f"Session {session_id}: Processing query with {len(history)} history items")
        
        # Create initial state
        initial_state = create_initial_state(
            user_input=request.query,
            schema_cache=_schema_cache,
            conversation_history=history
        )
        
        # Execute workflow
        start_time = time.time()
        
        final_state = _workflow.invoke(initial_state)
        
        execution_time = time.time() - start_time
        
        # Extract results
        response = final_state.get("response", "No response generated")
        sql = final_state.get("generated_sql")
        results = final_state.get("query_result")
        error = final_state.get("error_message")
        path = final_state.get("current_node", "unknown")
        
        # Update conversation history
        history.append({"role": "user", "content": request.query})
        history.append({"role": "assistant", "content": response})
        
        # Limit history size to prevent memory bloat
        if len(history) > 20:
            history = history[-20:]
        
        # Store updated history
        _conversation_history[session_id] = history
        
        logger.info(f"Session {session_id}: History now has {len(history)} items")
        
        return QueryResponse(
            response=response,
            sql=sql,
            results=results,
            execution_time=execution_time,
            path_taken=path,
            error=error,
            conversation_history=history
        )
        
    except Exception as e:
        logger.error(f"Error executing query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/history/{session_id}")
async def clear_history(session_id: str = "default"):
    """Clear conversation history for a session."""
    global _conversation_history
    
    if session_id in _conversation_history:
        del _conversation_history[session_id]
        return {"status": "cleared", "session_id": session_id}
    
    return {"status": "not_found", "session_id": session_id}


@app.get("/history/{session_id}")
async def get_history(session_id: str = "default"):
    """Get conversation history for a session."""
    history = _conversation_history.get(session_id, [])
    return {
        "session_id": session_id,
        "history": history,
        "message_count": len(history)
    }


@app.get("/examples")
async def get_examples():
    """Get example queries users can try."""
    return {
        "examples": [
            {
                "category": "Simple Queries",
                "queries": [
                    "Show me the first 5 employees",
                    "How many customers are there?",
                    "List all active employees"
                ]
            },
            {
                "category": "Analytical Queries",
                "queries": [
                    "Which employees generated the highest revenue per shift?",
                    "What is the average transaction amount per customer?",
                    "How many customers are in each region?"
                ]
            },
            {
                "category": "Complex Queries",
                "queries": [
                    "Show high-risk customers who lost more than $5000 in game sessions",
                    "Find customers with the highest problem gambling scores by region",
                    "Which equipment generates the most revenue per hour?"
                ]
            }
        ]
    }

