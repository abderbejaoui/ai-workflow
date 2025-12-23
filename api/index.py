"""
FastAPI application for AI Workflow - Vercel Serverless Function
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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


class QueryRequest(BaseModel):
    """Request model for query endpoint."""
    query: str
    conversation_history: Optional[List[Dict[str, str]]] = []


class QueryResponse(BaseModel):
    """Response model for query endpoint."""
    response: str
    sql: Optional[str] = None
    results: Optional[List[Dict[str, Any]]] = None
    execution_time: float
    path_taken: str
    error: Optional[str] = None


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


@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {
        "status": "ok",
        "message": "AI Workflow API is running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "tables_cached": len(_schema_cache.get("tables", [])) if _schema_cache else 0
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
    try:
        # Ensure system is initialized
        if _workflow is None:
            initialize_system()
        
        # Create initial state
        initial_state = create_initial_state(
            user_input=request.query,
            schema_cache=_schema_cache,
            conversation_history=request.conversation_history or []
        )
        
        # Execute workflow
        import time
        start_time = time.time()
        
        final_state = _workflow.invoke(initial_state)
        
        execution_time = time.time() - start_time
        
        # Extract results
        response = final_state.get("response", "No response generated")
        sql = final_state.get("generated_sql")
        results = final_state.get("query_result")
        error = final_state.get("error_message")
        path = final_state.get("current_node", "unknown")
        
        return QueryResponse(
            response=response,
            sql=sql,
            results=results,
            execution_time=execution_time,
            path_taken=path,
            error=error
        )
        
    except Exception as e:
        logger.error(f"Error executing query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


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


# Vercel serverless function handler
handler = app

