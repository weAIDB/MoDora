from __future__ import annotations

from dataclasses import dataclass
from typing import Any

"""Results 模型。

这里定义的是“评估结果”里一行记录的规范形态以及校验/转换过程的报告结构。

设计目标：
- 让 schema（字段与约束）集中在一处，避免在 CLI/存储/评估代码里散落多份规则。
- 允许对历史数据做最小兼容（例如 prediction 允许为 null），并通过显式约束保证一致性。
"""

@dataclass(frozen=True)
class ResultItem:
    """单条结果记录（对应 JSONL 中的一行）。

    字段含义：
    - questionId: 数据集中题目 ID。
    - pdf_id: 题目对应的文件名。
    - question: 题干文本。
    - answer: 标准答案（列表形式，兼容输入为 str 或 list[str]）。
    - tag: 可选的题目类别/子集标记。
    - prediction: 模型预测答案；允许为 None 表示“无答案/未输出”。
    - judge: 人工/自动评测结果；当 prediction 为 None 时强制为 "F"。
    """

    questionId: int
    pdf_id: str
    question: str
    answer: list[str]
    tag: str | None
    prediction: str | None
    judge: str | None

    @staticmethod
    def from_dict(record: dict[str, Any]) -> "ResultItem":
        """从 JSON 对象解析并校验为 ResultItem。

        约束：
        - prediction 允许为 None；若为 str 则必须非空白。
        - judge 允许为 None；若为 str 则必须在 {"T","F"}；当 prediction 为 None 时必须为 "F"。
        """
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
        if pred is not None and not isinstance(pred, str):
            raise TypeError("prediction must be str or null")
        if isinstance(pred, str) and not pred.strip():
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
        if isinstance(judge, str) and judge not in {"T", "F"}:
            raise TypeError("judge must be 'T' or 'F'")
        if pred is None and judge != "F":
            raise TypeError("judge must be 'F' if prediction is null")

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
        """序列化为可写入 JSONL 的 dict（ensure_ascii=False 后写出）。"""
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
    """单行错误信息。

    - line_no: 行号；0 表示文件级 fatal 错误（例如 JSON 解析失败）。
    - error: 错误描述（异常信息字符串化）。
    """

    line_no: int
    error: str


@dataclass(frozen=True)
class ValidateReport:
    """校验报告"""

    total: int
    ok: int
    failed: int
    errors: list[RowError]


@dataclass(frozen=True)
class ConvertReport:
    """转换报告"""

    total: int
    ok: int
    failed: int
    written: int
    errors: list[RowError]
