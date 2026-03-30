import logging
import json
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """
    Formats every log record as a single JSON line.
    Fields included in every line:
      timestamp  — ISO 8601 UTC
      level      — INFO / WARNING / ERROR
      message    — the log message
      service    — always "css-prep-ai"
    Extra fields passed via extra={} are merged in:
      user_id, user_email, model, latency_ms,
      prompt_length, response_length, status, endpoint
    """

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "service": "css-prep-ai",
        }
        extra_fields = [
            "user_id", "user_email", "model", "latency_ms",
            "prompt_length", "response_length", "status",
            "endpoint", "request_id",
        ]
        for field in extra_fields:
            if hasattr(record, field):
                log_data[field] = getattr(record, field)
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)


def get_logger(name: str) -> logging.Logger:
    """
    Returns a logger with JSON formatting attached.
    Usage:
        from app.mlops.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Chat request", extra={
            "user_id": 1,
            "model": "gpt",
            "latency_ms": 1234.5,
        })
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger
