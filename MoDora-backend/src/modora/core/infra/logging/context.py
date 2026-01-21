from __future__ import annotations

import uuid
from contextvars import ContextVar
from contextlib import contextmanager

# 上下文追踪ID，用于日志和请求追踪。service用request_id，lab用run_id（见架构文档6.3节）
_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_run_id: ContextVar[str | None] = ContextVar("run_id", default=None)


def new_id(prefix: str = "", length: int = 8) -> str:
    """生成唯一ID，默认8位十六进制"""
    s = uuid.uuid4().hex[: max(1, int(length))]
    return f"{prefix}{s}" if prefix else s


def get_request_id() -> str | None:
    """获取当前请求ID（用于FastAPI服务）"""
    return _request_id.get()


def get_run_id() -> str | None:
    """获取当前运行ID（用于CLI批处理任务）"""
    return _run_id.get()


@contextmanager
def request_scope(request_id: str | None):
    """
    请求上下文管理器

    示例（FastAPI中间件）:
        with request_scope("req_abc123"):
            (这里get_request_id()返回"req_abc123")
            process_request()
    """
    tok = _request_id.set(request_id)
    try:
        yield
    finally:
        _request_id.reset(tok)


@contextmanager
def run_scope(run_id: str | None):
    """
    运行上下文管理器

    示例（批处理任务）:
        with run_scope("run_experiment_001"):
            (这里get_run_id()返回"run_experiment_001")
            run_batch_job()
    """
    tok = _run_id.set(run_id)
    try:
        yield
    finally:
        _run_id.reset(tok)
