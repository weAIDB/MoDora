from __future__ import annotations

import json
import os
from typing import Any, Iterable

from modora.core.domain.results import (
    ConvertReport,
    ResultItem,
    RowError,
    ValidateReport,
)

"""结果文件(JSONL)存储实现。

职责：
- 读取 JSONL: 一行一个 JSON object。
- 校验：逐行解析为 ResultItem 并汇总错误。
- 转换：对输入做最小归一化（例如 prediction 空串 -> None, prediction 为 None 时 judge 强制为 "F"),
  然后按需去重并原子写出新的 JSONL。

说明：
- infra/store 层实现细节，上层通过 core.results_io 调用。
"""


def _iter_jsonl_objects(path: str) -> Iterable[tuple[int, dict[str, Any]]]:
    """逐行读取 JSONL 并 yield (line_no, obj)。

    - 跳过空行。
    - 解析失败会抛异常，由上层捕获并转成 fatal 错误。
    """
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            s = line.strip()
            if not s:
                continue
            obj = json.loads(s)
            if not isinstance(obj, dict):
                raise TypeError(f"line {i}: not a JSON object")
            yield i, obj


def validate_results_file(path: str) -> ValidateReport:
    """校验单个结果 JSONL 文件。

    返回值包含：总行数、通过行数、失败行数，以及失败原因列表。
    """
    total: int = 0
    ok: int = 0
    errors: list[RowError] = []
    try:
        for line_no, obj in _iter_jsonl_objects(path):
            total += 1
            try:
                ResultItem.from_dict(obj)
                ok += 1
            except Exception as e:
                errors.append(RowError(line_no=line_no, error=str(e)))
    except Exception as e:
        errors.append(RowError(line_no=0, error=f"fatal:{e}"))

    failed = total - ok
    return ValidateReport(total=total, ok=ok, failed=failed, errors=errors)


def _atomic_write_jsonl(path: str, items: Iterable[ResultItem]) -> int:
    """原子写 JSONL。

    先写入临时文件再 os.replace 覆盖目标文件，避免中途失败留下半截文件。
    """
    tmp = f"{path}.tmp"
    written = 0
    with open(tmp, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it.to_dict(), ensure_ascii=False) + "\n")
            written += 1
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    return written


def convert_results_file(
    in_path: str, out_path: str, dedup: str = "latest"
) -> ConvertReport:
    """转换结果 JSONL 文件并写出新文件。

    行级归一化：
    - prediction == "" -> None
    - prediction 为 None 且 judge == "T" 时，自动修正 judge 为 "F"

    去重策略：
    - dedup == "latest"：按 questionId 去重，保留最后出现的一条。
    - dedup == "none"：不去重，保持原顺序（写出时仍是逐项写入）。

    注意：只要存在任意行失败，则不写 out_path（written=0）。
    """
    total = 0
    ok = 0
    errors: list[RowError] = []

    items_latest: dict[int, ResultItem] = {}
    items_list: list[ResultItem] = []

    try:
        for line_no, record in _iter_jsonl_objects(in_path):
            total += 1
            try:
                if record.get("prediction") == "":
                    record["prediction"] = None
                if record.get("prediction") is None and record.get("judge") == "T":
                    record["judge"] = "F"
                it = ResultItem.from_dict(record)
                ok += 1
                if dedup == "latest":
                    items_latest[it.questionId] = it
                else:
                    items_list.append(it)
            except Exception as e:
                errors.append(RowError(line_no=line_no, error=str(e)))
    except Exception as e:
        errors.append(RowError(line_no=0, error=f"fatal: {e}"))

    failed = total - ok
    if failed:
        return ConvertReport(
            total=total, ok=ok, failed=failed, written=0, errors=errors
        )

    if dedup == "latest":
        written = _atomic_write_jsonl(out_path, items_latest.values())
    else:
        written = _atomic_write_jsonl(out_path, items_list)

    return ConvertReport(
        total=total, ok=ok, failed=failed, written=written, errors=errors
    )
