"""
Logging configuration for the AI Workflow system.

Provides structured logging with:
- Different log levels (DEBUG, INFO, WARNING, ERROR)
- Formatted output with timestamps
- File and console handlers
- Request tracking with correlation IDs
"""
import logging
import sys
import os
from datetime import datetime, timezone
from typing import Optional
import json


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""
    
    def format(self, record):
        """Format log record as JSON for structured logging."""
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add extra fields if present
        if hasattr(record, 'node'):
            log_data['node'] = record.node
        if hasattr(record, 'intent'):
            log_data['intent'] = record.intent
        if hasattr(record, 'confidence'):
            log_data['confidence'] = record.confidence
        if hasattr(record, 'execution_time'):
            log_data['execution_time'] = record.execution_time
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        if hasattr(record, 'sql'):
            log_data['sql'] = record.sql
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


class ColoredConsoleFormatter(logging.Formatter):
    """Colored formatter for console output."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        """Format with colors for console."""
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging(
    log_level: str = None,
    log_file: Optional[str] = None,
    structured: bool = False,
    console_output: bool = True
) -> logging.Logger:
    """
    Setup logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional file path for logging
        structured: If True, use JSON structured logging
        console_output: If True, also log to console
    
    Returns:
        Configured logger
    """
    # Get log level from env or parameter
    if log_level is None:
        log_level = os.getenv("LOG_LEVEL", "INFO")
    
    # Convert string to logging level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create logger
    logger = logging.getLogger("ai_workflow")
    logger.setLevel(numeric_level)
    
    # Remove existing handlers
    logger.handlers = []
    
    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        
        if structured:
            console_formatter = StructuredFormatter()
        else:
            console_formatter = ColoredConsoleFormatter(
                '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        try:
            # Create logs directory if it doesn't exist
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(numeric_level)
            
            if structured:
                file_formatter = StructuredFormatter()
            else:
                file_formatter = logging.Formatter(
                    '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
            
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        except (OSError, PermissionError) as e:
            # Silently skip file logging on read-only filesystems
            print(f"Warning: Could not setup file logging: {e}")
    
    return logger


def get_logger(name: str = "ai_workflow") -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name (default: ai_workflow)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Request ID tracking for correlation
_current_request_id: Optional[str] = None


def set_request_id(request_id: str):
    """Set the current request ID for tracking."""
    global _current_request_id
    _current_request_id = request_id


def get_request_id() -> Optional[str]:
    """Get the current request ID."""
    return _current_request_id


def log_node_entry(logger: logging.Logger, node_name: str, state: dict):
    """Log entry into a node."""
    logger.info(
        f"Entering node: {node_name}",
        extra={
            'node': node_name,
            'request_id': get_request_id()
        }
    )
    logger.debug(f"State keys: {list(state.keys())}")


def log_node_exit(logger: logging.Logger, node_name: str, updates: dict):
    """Log exit from a node."""
    logger.info(
        f"Exiting node: {node_name}",
        extra={
            'node': node_name,
            'updates': list(updates.keys()),
            'request_id': get_request_id()
        }
    )


def log_routing_decision(logger: logging.Logger, from_node: str, to_node: str, reason: str = ""):
    """Log a routing decision."""
    logger.info(
        f"Routing: {from_node} → {to_node} {f'({reason})' if reason else ''}",
        extra={
            'from_node': from_node,
            'to_node': to_node,
            'reason': reason,
            'request_id': get_request_id()
        }
    )


def log_llm_call(logger: logging.Logger, model: str, prompt_tokens: int = None):
    """Log an LLM call."""
    logger.debug(
        f"LLM call: {model}",
        extra={
            'model': model,
            'prompt_tokens': prompt_tokens,
            'request_id': get_request_id()
        }
    )


def log_sql_execution(logger: logging.Logger, sql: str, execution_time: float, row_count: int = None):
    """Log SQL execution."""
    logger.info(
        f"SQL executed in {execution_time:.3f}s",
        extra={
            'sql': sql[:100] + '...' if len(sql) > 100 else sql,
            'execution_time': execution_time,
            'row_count': row_count,
            'request_id': get_request_id()
        }
    )


def log_error(logger: logging.Logger, error: Exception, context: str = ""):
    """Log an error with context."""
    logger.error(
        f"Error in {context}: {str(error)}",
        extra={
            'context': context,
            'error_type': type(error).__name__,
            'request_id': get_request_id()
        },
        exc_info=True
    )


# Initialize default logger
_default_logger = None


def init_default_logger():
    """Initialize the default logger with settings from config."""
    global _default_logger
    if _default_logger is None:
        # Check if we're on Vercel (read-only filesystem)
        is_vercel = os.getenv("VERCEL", "").lower() in ("1", "true")
        
        # Also check via path - Vercel runs from /var/task
        try:
            is_vercel = is_vercel or "/var/task" in os.getcwd()
        except Exception:
            pass
        
        log_file = None  # Disable file logging on serverless
        if not is_vercel and os.getenv("LOG_TO_FILE", "false").lower() == "true":
            log_file = os.getenv("LOG_FILE", "logs/ai_workflow.log")
        
        structured = os.getenv("LOG_STRUCTURED", "false").lower() == "true"
        
        _default_logger = setup_logging(
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_file=log_file,
            structured=structured,
            console_output=True
        )
    
    return _default_logger

