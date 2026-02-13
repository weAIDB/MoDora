from __future__ import annotations

import json
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from typing import Any

from modora.core.infra.logging.context import get_request_id, get_run_id
from modora.core.settings import Settings

"""Logging Configuration Module.

This module provides a configurable logging system that supports structured output
and context injection.

Key Features:
1. Supports console and rotating file output.
2. Supports plain text and JSON log formats.
3. Automatically injects request_id and run_id into each log entry.
4. Provides automated log file rotation management.

Usage:
    from modora.core.settings import Settings
    from modora.core.infra.logging.setup import configure_logging
    
    settings = Settings()  # Load configuration
    configure_logging(settings)  # Configure the logging system
"""


class _ContextFilter(logging.Filter):
    """Logging context filter.

    This filter is called before each log record is processed to inject
    request_id and run_id.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or "-"
        record.run_id = get_run_id() or "-"
        return True


_STANDARD_LOG_RECORD_ATTRS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
}


def _extract_extras(record: logging.LogRecord) -> dict[str, Any]:
    """Extracts extra fields from the log record.

    This function extracts all non-standard fields from the log record for
    inclusion as additional context in JSON logs.

    Args:
        record: The log record object to process.

    Returns:
        A dictionary containing all extra fields, where keys are field names
        and values are the corresponding field values.
    """
    extras: dict[str, Any] = {}
    for k, v in record.__dict__.items():
        if k in _STANDARD_LOG_RECORD_ATTRS or k in {
            "request_id",
            "run_id",
            "message",
            "asctime",
        }:
            continue
        if k.startswith("_"):
            continue
        extras[k] = v
    return extras


_REST = "\x1b[0m"
_COLOR_TIME = "\x1b[90m"  # Gray
_COLOR_NAME = "\x1b[35m"  # Purple
_COLOR_CONTEXT = "\x1b[90m"  # Gray
_COLOR_BY_LEVEL = {
    logging.DEBUG: "\x1b[34m",  # Blue
    logging.INFO: "\x1b[32m",  # Green
    logging.WARNING: "\x1b[33m",  # Yellow
    logging.ERROR: "\x1b[31m",  # Red
    logging.CRITICAL: "\x1b[1;31m",  # Bold Red
}


class _TextFormater(logging.Formatter):
    def __init__(self, fmt: str, datefmt: str | None = None, color: bool = False):
        super().__init__(fmt, datefmt)
        self._color = color

    def format(self, record: logging.LogRecord) -> str:
        if not self._color or not (
            hasattr(sys.stderr, "isatty") and sys.stderr.isatty()
        ):
            base = super().format(record)
            extras = _extract_extras(record)
            if extras:
                base = f"{base} extra={json.dumps(extras, ensure_ascii=False)}"
            return base

        # Formatted with color
        asctime = self.formatTime(record, self.datefmt)
        levelname = record.levelname
        name = record.name
        request_id = getattr(record, "request_id", "-")
        run_id = getattr(record, "run_id", "-")
        message = record.getMessage()

        level_color = _COLOR_BY_LEVEL.get(record.levelno, _REST)

        # Build colored string
        # Format: %(asctime)s %(levelname)s %(name)s [req=%(request_id)s run=%(run_id)s] %(message)s
        formatted = (
            f"{_COLOR_TIME}{asctime}{_REST} "
            f"{level_color}{levelname:<8}{_REST} "
            f"{_COLOR_NAME}{name}{_REST} "
            f"{_COLOR_CONTEXT}[req={request_id} run={run_id}]{_REST} "
            f"{message}"
        )

        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            if formatted[-1:] != "\n":
                formatted = formatted + "\n"
            formatted = formatted + record.exc_text
        if record.stack_info:
            if formatted[-1:] != "\n":
                formatted = formatted + "\n"
            formatted = formatted + self.formatStack(record.stack_info)

        extras = _extract_extras(record)
        if extras:
            formatted = f"{formatted} {_COLOR_CONTEXT}extra={json.dumps(extras, ensure_ascii=False)}{_REST}"

        return formatted


class _JsonFormatter(logging.Formatter):
    """JSON log formatter.

    Converts log records into structured JSON strings for easy parsing and
    statistical analysis.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "time": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
            "run_id": getattr(record, "run_id", "-"),
        }
        # Format and add exception info to the payload if it exists
        extras = _extract_extras(record)
        if extras:
            payload["extras"] = extras
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(settings: Settings) -> None:
    """Configures the application's logging system.

    This is the main entry point for the module. It performs the following:
    1. Clears existing log handlers.
    2. Sets the log level based on configuration.
    3. Configures the console handler (always enabled).
    4. Configures the file handler (if enabled).
    5. Adds context filters and appropriate formatters to all handlers.

    Args:
        settings: The application settings object, containing all logging
            configurations.

    Note:
        This function modifies the global root logger, affecting the logging
        behavior of the entire application.
    """
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)

    level = getattr(logging, settings.log_level, logging.INFO)
    root.setLevel(level)

    fmt_text = "%(asctime)s %(levelname)s %(name)s [req=%(request_id)s run=%(run_id)s] %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    context_filter = _ContextFilter()

    console = logging.StreamHandler()
    console.addFilter(context_filter)
    # Always print to console in text format
    console.setFormatter(_TextFormater(fmt_text, datefmt=datefmt, color=True))
    root.addHandler(console)

    if settings.log_to_file:
        log_dir = settings.log_dir or os.path.join(os.getcwd(), "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, f"{settings.service_name}.log")

        fh = RotatingFileHandler(
            log_path, maxBytes=20 * 1024 * 1024, backupCount=10, encoding="utf-8"
        )
        fh.addFilter(context_filter)
        if settings.log_format.lower() == "json":
            fh.setFormatter(_JsonFormatter(datefmt=datefmt))
        else:
            fh.setFormatter(_TextFormater(fmt_text, datefmt=datefmt))
        root.addHandler(fh)
