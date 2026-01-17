from __future__ import annotations

import json
import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Any

from modora.core.logging_context import get_request_id, get_run_id
from modora.core.settings import Settings

"""
日志配置模块

本模块提供了可配置的、支持结构化输出和上下文注入的日志系统。
主要功能：
1. 支持控制台和滚动文件两种日志输出方式
2. 支持纯文本和JSON两种日志格式
3. 自动为每条日志注入 request_id 和运行 run_id
4. 提供自动化的日志文件轮转管理

使用方式：
    from modora.core.settings import Settings
    from modora.core.logging_config import configure_logging
    
    settings = Settings()  # 加载配置
    configure_logging(settings)  # 配置日志系统
"""


class _ContextFilter(logging.Filter):
    """日志上下文过滤器

    此过滤器会在每条日志记录被处理前调用，为其注入 request_id 和 run_id
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
    """从日志记录中提取额外字段

    此函数会从日志记录中提取所有非标准字段，用于在JSON日志中包含额外上下文信息。

    Args:
        record: 待处理的日志记录对象

    Returns:
        包含所有额外字段的字典，键为字段名，值为对应字段值
    """
    extras: dict[str, Any] = {}
    for k, v in record.__dict__.items():
        if k in _STANDARD_LOG_RECORD_ATTRS or k in {"request_id", "run_id"}:
            continue
        if k.startswith("_"):
            continue
        extras[k] = v
    return extras


class _TextFormater(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        extras = _extract_extras(record)
        if extras:
            return f"{base} extra={json.dumps(extras, ensure_ascii=False)}"
        return base


class _JsonFormatter(logging.Formatter):
    """JSON格式日志格式化器

    将日志记录转换为结构化JSON字符串，便于解析和统计
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "time": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
            "run_id": getattr(record, "run_id", "-"),
        }
        # 如果存在异常信息，将其格式化后加入载荷
        extras = _extract_extras(record)
        if extras:
            payload["extras"] = extras
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(settings: Settings) -> None:
    """配置应用程序的日志系统

    这是本模块的主入口函数。它会：
    1. 清理现有的日志处理器
    2. 根据配置设置日志级别
    3. 配置控制台处理器（始终启用）
    4. 配置文件处理器（如果启用）
    5. 为所有处理器添加上下文过滤器和适当的格式化器

    Args:
        settings: 应用程序配置对象，包含日志相关的所有设置

    Note:
        此函数会修改全局的根日志记录器(root logger)，影响整个应用程序的日志行为。
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
    # 一直以text格式打印到控制台
    console.setFormatter(_TextFormater(fmt_text, datefmt=datefmt))
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
