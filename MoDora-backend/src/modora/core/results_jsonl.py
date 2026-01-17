from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any, Iterable


@dataclass(frozen=True)
class ResultItem:
    questionId: int
    pdf_id: str
    question: str
    answer: list[str]
    tag: str | None
    prediction: str
    judge: str | None

    @staticmethod
    def from_dict(record: dict[str, Any]) -> "ResultItem":
        if not isinstance(record, dict):
            raise TypeError("line is not an object")

        qid = record.get("questionId")
        if not isinstance(qid, int):
            raise TypeError("questionId must be int")

        question = record.get("question")
        if not isinstance(question, str) or not question.strip():
            raise TypeError("question must be non-empty str")

        ans = record.get("answer")
        if ans is None:
            raise TypeError("answer is required")
        if isinstance(ans, str):
            answer = [ans]
        elif isinstance(ans, list) and all(isinstance(x, str) for x in ans):
            answer = ans
        else:
            raise TypeError("answer must be list[str] (or str)")

        pred = record.get("prediction")
        if not isinstance(pred, str) or not pred.strip():
            raise TypeError("prediction must be non-empty str")

        pdf_id = record.get("pdf_id")
        if not isinstance(pdf_id, str) or not pdf_id:
            raise TypeError("pdf_id must be non-empty str")

        tag = record.get("tag")
        if tag is not None and not isinstance(tag, str):
            raise TypeError("tag must be str or null")

        judge = record.get("judge")
        if judge is not None and not isinstance(judge, str):
            raise TypeError("judge must be str or null")

        return ResultItem(
            questionId=qid,
            pdf_id=pdf_id,
            question=question,
            answer=answer,
            tag=tag,
            prediction=pred,
            judge=judge,
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "questionId": self.questionId,
            "pdf_id": self.pdf_id,
            "question": self.question,
            "answer": self.answer,
            "tag": self.tag,
            "prediction": self.prediction,
            "judge": self.judge,
        }
        return out


@dataclass(frozen=True)
class RowError:
    line_no: int
    error: str


@dataclass(frozen=True)
class ValidateReport:
    total: int
    ok: int
    failed: int
    errors: list[RowError]


@dataclass(frozen=True)
class ConvertReport:
    total: int
    ok: int
    failed: int
    written: int
    errors: list[RowError]


def _iter_jsonl_objects(path: str) -> Iterable[tuple[int, dict[str, Any]]]:
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
    total = 0
    ok = 0
    errors: list[RowError] = []

    items_latest: dict[int, ResultItem] = {}
    items_list: list[ResultItem] = []

    try:
        for line_no, obj in _iter_jsonl_objects(in_path):
            total += 1
            try:
                it = ResultItem.from_dict(obj)
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
