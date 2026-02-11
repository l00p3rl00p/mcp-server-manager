from __future__ import annotations
import json
import logging
import sys
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional

from .config import LOGS_DIR


def _resolve_logs_dir() -> Path:
    """
    Resolve a writable logs directory.
    Falls back to ~/.mcpinv/logs if ~/.mcp-tools/... is not writable.
    """
    primary = LOGS_DIR
    try:
        primary.mkdir(parents=True, exist_ok=True)
        probe = primary / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return primary
    except Exception:
        fallback = Path.home() / ".mcpinv" / "logs"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


ACTIVE_LOGS_DIR = _resolve_logs_dir()

# Logger names
LOGGER_NAME = "mcpinv"

class JsonFormatter(logging.Formatter):
    """
    Formatter that outputs JSON strings for machine consumption.
    Fields: timestamp, level, message, ...extra_fields
    """
    def format(self, record: logging.LogRecord) -> str:
        data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        # Add any extra attributes from the record if they exist
        if hasattr(record, "props") and isinstance(record.props, dict):
            data.update(record.props)
        
        return json.dumps(data)

def setup_logging(verbose: bool = False) -> logging.Logger:
    """
    Sets up the unified logging configuration.
    - Console: Human readable (INFO or DEBUG)
    - File: Machine readable JSONL (DEBUG, rotating)
    """
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.DEBUG)
    
    # clear existing handlers to avoid duplicates
    if logger.hasHandlers():
        logger.handlers.clear()

    # 1. Console Handler (Human)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_format = logging.Formatter("%(message)s")
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # 2. File Handler (Machine - JSONL)
    log_file = ACTIVE_LOGS_DIR / "mcpinv.jsonl"
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024, # 5MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(JsonFormatter())
    logger.addHandler(file_handler)

    return logger

def get_logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)

def log_event(event: str, data: Optional[Dict[str, Any]] = None, level: int = logging.INFO) -> None:
    """
    Helper to log structured events.
    """
    logger = get_logger()
    props = {"event": event}
    if data:
        props.update(data)
    
    # We use the 'extra' dict to pass properties to the Formatter, 
    # but since standard logging.Formatter doesn't use it easily for JSON,
    # we bind it to the record in a custom way or just pass it as a message dictionary?
    # Actually, the cleanest way with standard logging is to use 'extra'.
    # But our JsonFormatter looks for 'props'.
    
    # Let's just pass a structured message if we want, or use the adapter pattern.
    # For now, we'll manually attach it.
    
    logger.log(level, event, extra={"props": props})
