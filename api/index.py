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
    """Root endpoint - serve the chatbot UI."""
    # Try to read HTML from file first
    html_path = os.path.join(os.path.dirname(__file__), "public", "index.html")
    
    try:
        if os.path.exists(html_path):
            with open(html_path, "r", encoding="utf-8") as f:
                return f.read()
    except Exception as e:
        logger.warning(f"Could not read HTML file: {e}")
    
    # Return inline chatbot UI
    return CHATBOT_HTML


# Chatbot HTML template
CHATBOT_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Casino AI Assistant</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{--bg:#0f0f0f;--bg2:#1a1a1a;--bg3:#252525;--gold:#d4af37;--text:#fff;--text2:#a0a0a0;--text3:#666;--border:#333;--green:#22c55e;--blue:#2563eb}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;display:flex;flex-direction:column}
.header{background:linear-gradient(135deg,var(--bg2),var(--bg3));border-bottom:1px solid var(--border);padding:16px 24px;display:flex;align-items:center;gap:16px}
.logo{width:48px;height:48px;background:linear-gradient(135deg,var(--gold),#a8892c);border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:24px}
.header-info h1{font-size:20px;font-weight:700}
.header-info p{font-size:13px;color:var(--text2)}
.status{margin-left:auto;display:flex;align-items:center;gap:8px;padding:8px 16px;background:rgba(34,197,94,.1);border:1px solid rgba(34,197,94,.3);border-radius:20px;font-size:13px;color:var(--green)}
.dot{width:8px;height:8px;background:var(--green);border-radius:50%;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.5}}
.main{display:flex;flex:1;overflow:hidden}
.sidebar{width:280px;background:var(--bg2);border-right:1px solid var(--border);padding:20px;overflow-y:auto}
.sidebar h3{font-size:12px;text-transform:uppercase;letter-spacing:1px;color:var(--text3);margin-bottom:12px}
.examples{display:flex;flex-direction:column;gap:8px;margin-bottom:24px}
.example-btn{background:var(--bg3);border:1px solid var(--border);border-radius:10px;padding:12px;text-align:left;color:var(--text2);font-size:13px;cursor:pointer;transition:all .2s}
.example-btn:hover{background:var(--bg);border-color:var(--gold);color:var(--text)}
.chat{flex:1;display:flex;flex-direction:column}
.messages{flex:1;overflow-y:auto;padding:24px;display:flex;flex-direction:column;gap:20px}
.message{display:flex;gap:12px;max-width:85%;animation:fadeIn .3s}
@keyframes fadeIn{from{opacity:0;transform:translateY(10px)}to{opacity:1}}
.message.user{align-self:flex-end;flex-direction:row-reverse}
.avatar{width:36px;height:36px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0}
.message.ai .avatar{background:linear-gradient(135deg,var(--gold),#a8892c)}
.message.user .avatar{background:var(--blue)}
.bubble{padding:14px 18px;border-radius:18px;line-height:1.5;font-size:14px}
.message.ai .bubble{background:#1e1e1e;border:1px solid var(--border);border-bottom-left-radius:4px}
.message.user .bubble{background:var(--blue);border-bottom-right-radius:4px}
.meta{font-size:11px;color:var(--text3);display:flex;gap:8px}
.message.user .meta{justify-content:flex-end}
.sql-block{background:#0d1117;border:1px solid #30363d;border-radius:10px;margin-top:8px;overflow:hidden}
.sql-header{padding:10px 14px;background:#161b22;border-bottom:1px solid #30363d;display:flex;justify-content:space-between;align-items:center}
.sql-header span{font-size:12px;color:var(--text3)}
.copy-btn{background:transparent;border:1px solid #30363d;border-radius:6px;padding:4px 10px;font-size:11px;color:var(--text2);cursor:pointer}
.copy-btn:hover{background:#30363d;color:var(--text)}
.sql-code{padding:14px;font-family:monospace;font-size:12px;color:#e6edf3;white-space:pre-wrap;overflow-x:auto}
.results{margin-top:12px;border-radius:10px;overflow:hidden;border:1px solid var(--border)}
.results table{width:100%;border-collapse:collapse;font-size:13px}
.results th{background:var(--bg3);padding:10px 14px;text-align:left;color:var(--text2);border-bottom:1px solid var(--border)}
.results td{padding:10px 14px;border-bottom:1px solid var(--border)}
.results tr:last-child td{border-bottom:none}
.input-area{padding:20px 24px;background:var(--bg2);border-top:1px solid var(--border)}
.input-wrap{display:flex;gap:12px}
#input{flex:1;padding:16px 20px;background:var(--bg);border:1px solid var(--border);border-radius:14px;color:var(--text);font-size:15px;font-family:inherit;resize:none;min-height:54px;max-height:150px}
#input:focus{outline:none;border-color:var(--gold)}
#send{width:54px;height:54px;background:linear-gradient(135deg,var(--gold),#a8892c);border:none;border-radius:14px;cursor:pointer;display:flex;align-items:center;justify-content:center}
#send:hover{transform:scale(1.05)}
#send:disabled{opacity:.5}
#send svg{width:22px;height:22px;fill:var(--bg)}
.typing{display:flex;gap:4px;padding:8px 0}
.typing span{width:8px;height:8px;background:var(--text3);border-radius:50%;animation:typing 1.4s infinite}
.typing span:nth-child(2){animation-delay:.2s}
.typing span:nth-child(3){animation-delay:.4s}
@keyframes typing{0%,60%,100%{transform:translateY(0)}30%{transform:translateY(-6px)}}
.welcome{text-align:center;padding:60px 40px;max-width:600px;margin:auto}
.welcome-icon{width:80px;height:80px;background:linear-gradient(135deg,var(--gold),#a8892c);border-radius:20px;display:flex;align-items:center;justify-content:center;font-size:40px;margin:0 auto 24px}
.welcome h2{font-size:28px;margin-bottom:12px}
.welcome p{color:var(--text2);font-size:16px;line-height:1.6}
@media(max-width:768px){.sidebar{display:none}.header,.messages,.input-area{padding:12px 16px}.message{max-width:95%}}
</style>
</head>
<body>
<header class="header">
<div class="logo">&#127920;</div>
<div class="header-info"><h1>Casino AI Assistant</h1><p>Ask questions about your casino database</p></div>
<div class="status"><span class="dot"></span>Online</div>
</header>
<div class="main">
<aside class="sidebar">
<h3>Quick Queries</h3>
<div class="examples">
<button class="example-btn" onclick="ask('Show me 5 employees')">&#128101; Show me 5 employees</button>
<button class="example-btn" onclick="ask('How many customers are there?')">&#128202; How many customers?</button>
<button class="example-btn" onclick="ask('Show high-risk customers')">&#9888;&#65039; High-risk customers</button>
<button class="example-btn" onclick="ask('What is the total revenue from shifts?')">&#128176; Total shift revenue</button>
</div>
</aside>
<main class="chat">
<div class="messages" id="msgs">
<div class="welcome">
<div class="welcome-icon">&#127920;</div>
<h2>Welcome to Casino AI</h2>
<p>I can help you query and analyze your casino database. Ask me about employees, customers, transactions, and more!</p>
</div>
</div>
<div class="input-area">
<div class="input-wrap">
<textarea id="input" placeholder="Ask about your casino data..." rows="1" onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();send()}"></textarea>
<button id="send" onclick="send()"><svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg></button>
</div>
</div>
</main>
</div>
<script>
const API=window.location.origin;let sid='s'+Date.now(),loading=false;
const input=document.getElementById('input'),msgs=document.getElementById('msgs');
input.addEventListener('input',function(){this.style.height='auto';this.style.height=Math.min(this.scrollHeight,150)+'px'});
function ask(q){input.value=q;send()}
async function send(){const q=input.value.trim();if(!q||loading)return;loading=true;input.value='';input.style.height='auto';document.getElementById('send').disabled=true;const w=document.querySelector('.welcome');if(w)w.remove();addMsg(q,'user');const tid=addTyping();try{const r=await fetch(API+'/query',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query:q,session_id:sid})});const d=await r.json();removeTyping(tid);addAIMsg(d)}catch(e){removeTyping(tid);addMsg('Error: '+e.message,'ai')}loading=false;document.getElementById('send').disabled=false}
function addMsg(c,t){const m=document.createElement('div');m.className='message '+t;m.innerHTML='<div class="avatar">'+(t==='user'?'&#128100;':'&#127920;')+'</div><div class="content"><div class="bubble">'+esc(c)+'</div><div class="meta"><span>'+new Date().toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})+'</span></div></div>';msgs.appendChild(m);msgs.scrollTop=msgs.scrollHeight}
function addAIMsg(d){const m=document.createElement('div');m.className='message ai';let h='<div class="bubble">'+fmt(d.response)+'</div>';if(d.sql&&!d.sql.startsWith('--'))h+='<div class="sql-block"><div class="sql-header"><span>SQL</span><button class="copy-btn" onclick="copy(this)">Copy</button></div><div class="sql-code">'+esc(d.sql)+'</div></div>';if(d.results&&d.results.length>0&&d.results.length<=10)h+=table(d.results);m.innerHTML='<div class="avatar">&#127920;</div><div class="content">'+h+'<div class="meta"><span>'+new Date().toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})+'</span><span>'+d.execution_time.toFixed(2)+'s</span><span>'+d.path_taken+'</span></div></div>';msgs.appendChild(m);msgs.scrollTop=msgs.scrollHeight}
function table(r){const c=Object.keys(r[0]);let h='<div class="results"><table><thead><tr>';c.forEach(k=>h+='<th>'+k.replace(/_/g,' ')+'</th>');h+='</tr></thead><tbody>';r.slice(0,5).forEach(row=>{h+='<tr>';c.forEach(k=>h+='<td>'+esc(String(row[k]||''))+'</td>');h+='</tr>'});h+='</tbody></table></div>';return h}
function addTyping(){const id='t'+Date.now(),m=document.createElement('div');m.className='message ai';m.id=id;m.innerHTML='<div class="avatar">&#127920;</div><div class="content"><div class="bubble"><div class="typing"><span></span><span></span><span></span></div></div></div>';msgs.appendChild(m);msgs.scrollTop=msgs.scrollHeight;return id}
function removeTyping(id){const e=document.getElementById(id);if(e)e.remove()}
function copy(b){navigator.clipboard.writeText(b.closest('.sql-block').querySelector('.sql-code').textContent);b.textContent='Copied!';setTimeout(()=>b.textContent='Copy',2000)}
function esc(t){const d=document.createElement('div');d.textContent=t;return d.innerHTML}
function fmt(t){return t?esc(t).replace(/\\*\\*(.*?)\\*\\*/g,'<strong>$1</strong>').replace(/\\n/g,'<br>'):''}
</script>
</body>
</html>"""


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

