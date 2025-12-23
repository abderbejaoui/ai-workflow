"""
Configuration management for the AI workflow system.
Loads from environment variables with sensible defaults.
"""
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Central configuration class for all system settings."""
    
    # LLM Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    
    # Supervisor settings - uses fast, cheap model
    SUPERVISOR_MODEL: str = os.getenv("SUPERVISOR_MODEL", "gpt-4o-mini")
    SUPERVISOR_TEMPERATURE: float = float(os.getenv("SUPERVISOR_TEMPERATURE", "0.0"))
    SUPERVISOR_MAX_TOKENS: int = 150  # Keep responses minimal
    
    # Main LLM settings
    MAIN_MODEL: str = os.getenv("MAIN_MODEL", "gpt-4o")
    MAIN_TEMPERATURE: float = float(os.getenv("MAIN_TEMPERATURE", "0.7"))
    MAIN_MAX_TOKENS: int = 500
    
    # Databricks Configuration
    DATABRICKS_SERVER_HOSTNAME: str = os.getenv("DATABRICKS_SERVER_HOSTNAME", "")
    DATABRICKS_HTTP_PATH: str = os.getenv("DATABRICKS_HTTP_PATH", "")
    DATABRICKS_ACCESS_TOKEN: str = os.getenv("DATABRICKS_ACCESS_TOKEN", "")
    DATABRICKS_QUERY_TIMEOUT: int = int(os.getenv("DATABRICKS_QUERY_TIMEOUT", "2"))
    
    # Performance and Limits
    MAX_RESULT_ROWS: int = int(os.getenv("MAX_RESULT_ROWS", "1000"))
    CONVERSATION_HISTORY_LIMIT: int = int(os.getenv("CONVERSATION_HISTORY_LIMIT", "5"))
    RESULT_SUMMARY_MAX_TOKENS: int = 150
    
    # Confidence Thresholds
    DATABRICKS_CONFIDENCE_THRESHOLD: float = float(
        os.getenv("DATABRICKS_CONFIDENCE_THRESHOLD", "0.75")
    )
    
    # Schema Cache Settings
    SCHEMA_CACHE_TTL: int = 3600  # 1 hour in seconds
    
    # Logging Settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_TO_FILE: bool = os.getenv("LOG_TO_FILE", "true").lower() == "true"
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/ai_workflow.log")
    LOG_STRUCTURED: bool = os.getenv("LOG_STRUCTURED", "false").lower() == "true"
    
    @classmethod
    def validate(cls) -> bool:
        """Validate that required configuration is present."""
        required = [
            cls.OPENAI_API_KEY or cls.ANTHROPIC_API_KEY,
        ]
        return all(required)


# Global config instance
config = Config()

