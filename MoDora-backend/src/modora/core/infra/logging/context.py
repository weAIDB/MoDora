from __future__ import annotations

import uuid
from contextvars import ContextVar
from contextlib import contextmanager

# Context tracking ID for logging and request tracing. Use request_id for services and run_id for lab (refer to architecture documentation section 6.3)
_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_run_id: ContextVar[str | None] = ContextVar("run_id", default=None)


def new_id(prefix: str = "", length: int = 8) -> str:
    """Generates a unique ID, defaults to 8-character hexadecimal.

    Args:
        prefix: Optional prefix for the ID.
        length: Length of the generated hex string. Defaults to 8.

    Returns:
        The generated unique ID.
    """
    s = uuid.uuid4().hex[: max(1, int(length))]
    return f"{prefix}{s}" if prefix else s


def get_request_id() -> str | None:
    """Retrieves the current request ID (used for FastAPI services).

    Returns:
        The current request ID or None if not set.
    """
    return _request_id.get()


def get_run_id() -> str | None:
    """Retrieves the current run ID (used for CLI batch tasks).

    Returns:
        The current run ID or None if not set.
    """
    return _run_id.get()


@contextmanager
def request_scope(request_id: str | None):
    """Request context manager.

    Args:
        request_id: The request ID to set in the context.

    Example (FastAPI middleware):
        with request_scope("req_abc123"):
            # get_request_id() returns "req_abc123" here
            process_request()
    """
    tok = _request_id.set(request_id)
    try:
        yield
    finally:
        _request_id.reset(tok)


@contextmanager
def run_scope(run_id: str | None):
    """Run context manager.

    Args:
        run_id: The run ID to set in the context.

    Example (Batch task):
        with run_scope("run_experiment_001"):
            # get_run_id() returns "run_experiment_001" here
            process_task()
    """
    tok = _run_id.set(run_id)
    try:
        yield
    finally:
        _run_id.reset(tok)
