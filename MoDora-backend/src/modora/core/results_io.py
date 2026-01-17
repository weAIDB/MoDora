from __future__ import annotations

from modora.core.domain.results import (
    ConvertReport,
    ResultItem,
    RowError,
    ValidateReport,
)
from modora.core.infra.store.results_store import (
    convert_results_file,
    validate_results_file,
)

"""结果文件 I/O 的对外入口。

上层（CLI/评估脚本）建议只依赖本模块：
- schema/类型来自 domain.results
- 具体的 JSONL 存储实现来自 infra.store.results_store

"""

__all__ = [
    "ConvertReport",
    "ResultItem",
    "RowError",
    "ValidateReport",
    "convert_results_file",
    "validate_results_file",
]
