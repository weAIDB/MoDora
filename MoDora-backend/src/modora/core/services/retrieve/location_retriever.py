from __future__ import annotations

import fitz
from typing import List, Tuple

from modora.core.domain import CCTree, CCTreeNode, RetrievalResult


class LocationRetriever:
    """
    基于 PDF 位置信息的检索器。
    """

    def retrieve(
        self,
        tree: CCTree,
        page_list: List[int],
        position_vector: List[float],
        pdf_path: str,
    ) -> RetrievalResult:
        """
        根据页码和网格位置检索节点。

        参数:
            tree: CCTree 实例。
            page_list: 目标页码列表（1-based）。
            position_vector: 网格位置向量 [row, col]。
            pdf_path: PDF 文件路径。

        返回:
            RetrievalResult: 包含命中的文本映射和位置列表。
        """
        result = RetrievalResult()

        doc = fitz.open(pdf_path)
        try:
            target_pages = self._resolve_page_list(page_list, doc.page_count)

            # 预计算页面尺寸以避免重复调用
            page_dims = {}
            for p in target_pages:
                if 1 <= p <= doc.page_count:
                    rect = doc[p - 1].rect
                    page_dims[p] = (rect.width, rect.height)

            for page_number in target_pages:
                if page_number not in page_dims:
                    continue

                dims = page_dims[page_number]

                # 从 CCTree 根节点开始遍历
                self._traverse_tree(
                    node=tree.root,
                    path="root",
                    page_number=page_number,
                    page_dims=dims,
                    position_vector=position_vector,
                    result=result,
                )
        finally:
            doc.close()

        return result

    def _resolve_page_list(self, page_list: List[int], total_pages: int) -> List[int]:
        """解析页码列表，处理 -1（表示所有页面）的情况。"""
        if -1 in page_list:
            return list(range(1, total_pages + 1))
        return page_list

    def _traverse_tree(
        self,
        node: CCTreeNode,
        path: str,
        page_number: int,
        page_dims: Tuple[float, float],
        position_vector: List[float],
        result: RetrievalResult,
    ):
        """递归遍历树，检查节点是否与指定位置重叠。"""
        # 确定当前页面上有哪些位置被命中
        hit_locations = []
        for loc in node.location:
            if loc.page == page_number:
                if self._is_overlapping(loc.bbox, page_dims, position_vector):
                    hit_locations.append(loc)

        if hit_locations:
            if node.data:
                result.text_map[path] = node.data
            result.locations.extend(hit_locations)

        # 递归检查子节点
        for child_key, child_node in node.children.items():
            child_path = f"{path}--{child_key}"
            self._traverse_tree(
                child_node, child_path, page_number, page_dims, position_vector, result
            )

    def _is_overlapping(
        self,
        bbox: List[float],
        page_dims: Tuple[float, float],
        position_vector: List[float],
    ) -> bool:
        """检查给定的 bbox 是否与指定的网格位置重叠。"""
        page_width, page_height = page_dims
        x0, y0, x1, y1 = self._normalize_bbox(bbox, page_width, page_height)

        row, column = position_vector

        # 3x3 网格计算
        grid_x0 = (column - 1) / 3 if column != -1 else 0.0
        grid_x1 = column / 3 if column != -1 else 1.0
        grid_y0 = (row - 1) / 3 if row != -1 else 0.0
        grid_y1 = row / 3 if row != -1 else 1.0

        # 检查重叠
        x_overlap = not (x1 <= grid_x0 or x0 >= grid_x1)
        y_overlap = not (y1 <= grid_y0 or y0 >= grid_y1)

        return x_overlap and y_overlap

    @staticmethod
    def _normalize_bbox(
        bbox: List[float], page_width: float, page_height: float
    ) -> List[float]:
        """将绝对坐标 bbox 归一化为 [0, 1] 相对坐标。"""
        return [
            bbox[0] / page_width,
            bbox[1] / page_height,
            bbox[2] / page_width,
            bbox[3] / page_height,
        ]
