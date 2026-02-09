from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class ResultItem:
    """单条评估结果项。

    代表了数据集中的一个题目及其对应的模型预测与评判结果。

    Attributes:
        questionId: 题目唯一标识。
        pdf_id: 关联的 PDF 文件名或 ID。
        question: 题目文本内容。
        answer: 标准答案列表。支持单答案或多答案。
        tag: 题目分类标签（可选）。
        prediction: 模型生成的预测结果。None 表示未生成答案。
        judge: 评判结果（'T' 表示正确，'F' 表示错误）。
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
        """从字典对象解析并校验 ResultItem。

        Args:
            record: 原始数据字典。

        Returns:
            校验通过的 ResultItem 实例。

        Raises:
            TypeError: 当数据类型不符合规范或缺少必要字段时抛出。
        """
        if not isinstance(record, dict):
            raise TypeError("数据项必须是字典对象")

        qid = record.get("questionId")
        if not isinstance(qid, int):
            raise TypeError("questionId 必须为整数类型")

        question = record.get("question")
        if not isinstance(question, str) or not question.strip():
            raise TypeError("question 必须为非空字符串")

        ans = record.get("answer")
        if ans is None:
            raise TypeError("answer 字段缺失")
        if isinstance(ans, str):
            answer = [ans]
        elif isinstance(ans, list) and all(isinstance(x, str) for x in ans):
            answer = ans
        else:
            raise TypeError("answer 必须为字符串或字符串列表")

        pred = record.get("prediction")
        if pred is not None and not isinstance(pred, str):
            raise TypeError("prediction 必须为字符串或 null")
        if isinstance(pred, str) and not pred.strip():
            raise TypeError("prediction 不能是空字符串")

        pdf_id = record.get("pdf_id")
        if not isinstance(pdf_id, str) or not pdf_id:
            raise TypeError("pdf_id 必须为非空字符串")

        tag = record.get("tag")
        if tag is not None and not isinstance(tag, str):
            raise TypeError("tag 必须为字符串或 null")

        judge = record.get("judge")
        if judge is not None and not isinstance(judge, str):
            raise TypeError("judge 必须为字符串或 null")
        if isinstance(judge, str) and judge not in {"T", "F"}:
            raise TypeError("judge 必须为 'T' 或 'F'")
        if pred is None and judge != "F":
            raise TypeError("当预测结果(prediction)为空时，评判结果(judge)必须为 'F'")

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
        """将当前项序列化为字典。

        Returns:
            包含所有字段的字典，适用于 JSON/JSONL 持久化。
        """
        return {
            "questionId": self.questionId,
            "pdf_id": self.pdf_id,
            "question": self.question,
            "answer": self.answer,
            "tag": self.tag,
            "prediction": self.prediction,
            "judge": self.judge,
        }


def write_results_file(path: str, items: Iterable[ResultItem]) -> int:
    """将结果项列表写入 JSONL 文件。

    Args:
        path: 目标文件路径。
        items: 待写入的 ResultItem 迭代对象。

    Returns:
        成功写入的行数。
    """
    written = 0
    with open(path, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it.to_dict(), ensure_ascii=False) + "\n")
            written += 1
    return written
