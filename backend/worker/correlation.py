"""
Correlation ID utilities for distributed tracing.
"""
import json
import logging
import uuid
from contextvars import ContextVar
from typing import Optional, Dict, Any

# Context variable for correlation ID
correlation_id_context: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


class CorrelationIdFilter(logging.Filter):
    """Logging filter that adds correlation ID to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_context.get() or "none"
        return True


class StructuredJsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, 'correlation_id', 'none'),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                           'levelname', 'levelno', 'lineno', 'module', 'msecs', 'message',
                           'pathname', 'process', 'processName', 'relativeCreated',
                           'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info',
                           'correlation_id']:
                log_data[key] = value
        
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


def extract_correlation_id_from_sqs(message_attributes: Dict[str, Any]) -> Optional[str]:
    """
    Extract correlation ID from SQS message attributes.
    
    Handles both Lambda SQS event format (messageAttributes) and direct SQS format.
    """
    if not message_attributes:
        return None
    
    # Try CorrelationId (as sent by our service)
    correlation_attr = message_attributes.get('CorrelationId')
    if correlation_attr:
        if isinstance(correlation_attr, dict):
            # Lambda SQS event format: {"stringValue": "..."} or {"StringValue": "..."}
            return correlation_attr.get('stringValue') or correlation_attr.get('StringValue')
        elif isinstance(correlation_attr, str):
            # Direct string value
            return correlation_attr
    
    return None


def setup_structured_logging(level: str = "INFO"):
    """Configure structured JSON logging with correlation IDs."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add new handler with structured formatter
    handler = logging.StreamHandler()
    handler.setLevel(level)
    formatter = StructuredJsonFormatter()
    handler.setFormatter(formatter)
    handler.addFilter(CorrelationIdFilter())
    root_logger.addHandler(handler)

