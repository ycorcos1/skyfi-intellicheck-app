"""
Structured logging configuration for the FastAPI backend.
"""
import json
import logging
import os
import uuid
from contextvars import ContextVar
from datetime import datetime
from typing import Optional, Dict, Any

# Context variable for correlation ID
correlation_id_context: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


class CorrelationIdFilter(logging.Filter):
    """Logging filter that adds correlation ID to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_context.get() or "none"
        return True


class StructuredJsonFormatter(logging.Formatter):
    """JSON formatter for structured logging with consistent fields."""
    
    def __init__(self, service_name: str = "api", environment: Optional[str] = None):
        super().__init__()
        self.service_name = service_name
        self.environment = environment or os.getenv("ENVIRONMENT", "development")
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, 'correlation_id', 'none'),
            "service": self.service_name,
            "environment": self.environment,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            log_data["stack_trace"] = self.formatStack(record.stack_info) if record.stack_info else None
        
        # Add extra fields (excluding standard logging fields)
        standard_fields = {
            'name', 'msg', 'args', 'created', 'filename', 'funcName',
            'levelname', 'levelno', 'lineno', 'module', 'msecs', 'message',
            'pathname', 'process', 'processName', 'relativeCreated',
            'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info',
            'correlation_id', 'asctime'
        }
        
        for key, value in record.__dict__.items():
            if key not in standard_fields:
                # Only include JSON-serializable values
                try:
                    json.dumps(value)
                    log_data[key] = value
                except (TypeError, ValueError):
                    log_data[key] = str(value)
        
        return json.dumps(log_data)


def set_correlation_id(correlation_id: str):
    """Set correlation ID for current context."""
    correlation_id_context.set(correlation_id)


def get_correlation_id() -> Optional[str]:
    """Get correlation ID from current context."""
    return correlation_id_context.get()


def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    return str(uuid.uuid4())


def setup_structured_logging(
    service_name: str = "api",
    level: str = "INFO",
    environment: Optional[str] = None
) -> logging.Logger:
    """
    Configure structured JSON logging with correlation IDs.
    
    Args:
        service_name: Name of the service (e.g., "api", "worker")
        level: Logging level (e.g., "INFO", "DEBUG")
        environment: Environment name (e.g., "development", "production")
    
    Returns:
        Configured root logger
    """
    root_logger = logging.getLogger()
    log_level = getattr(logging, level.upper(), logging.INFO)
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add new handler with structured formatter
    handler = logging.StreamHandler()
    handler.setLevel(log_level)
    formatter = StructuredJsonFormatter(service_name=service_name, environment=environment)
    handler.setFormatter(formatter)
    handler.addFilter(CorrelationIdFilter())
    root_logger.addHandler(handler)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with structured logging support.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    return logger

