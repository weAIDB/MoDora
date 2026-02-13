from __future__ import annotations

import fitz
from typing import List, Tuple

from modora.core.domain import CCTree, CCTreeNode, RetrievalResult


class LocationRetriever:
    """Retriever based on PDF location information."""

    def retrieve(
        self,
        tree: CCTree,
        page_list: List[int],
        position_vector: List[float],
        pdf_path: str,
    ) -> RetrievalResult:
        """Retrieves nodes based on page numbers and grid positions.

        Args:
            tree (CCTree): CCTree instance.
            page_list (List[int]): Target page numbers (1-based).
            position_vector (List[float]): Grid position vector [row, col].
            pdf_path (str): Path to the PDF file.

        Returns:
            RetrievalResult: Contains matched text mappings and location lists.
        """
        result = RetrievalResult()

        doc = fitz.open(pdf_path)
        try:
            target_pages = self._resolve_page_list(page_list, doc.page_count)

            # Precompute page dimensions to avoid redundant calls
            page_dims = {}
            for p in target_pages:
                if 1 <= p <= doc.page_count:
                    rect = doc[p - 1].rect
                    page_dims[p] = (rect.width, rect.height)

            for page_number in target_pages:
                if page_number not in page_dims:
                    continue

                dims = page_dims[page_number]

                # Start traversing from the CCTree root node
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
        """Parses the page list, handling the case of -1 (representing all pages)."""
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
        """Recursively traverses the tree to check if nodes overlap with the specified location."""
        # Determine which locations on the current page are hit
        hit_locations = []
        for loc in node.location:
            if loc.page == page_number:
                if self._is_overlapping(loc.bbox, page_dims, position_vector):
                    hit_locations.append(loc)

        if hit_locations:
            if node.data:
                result.text_map[path] = node.data
            result.locations.extend(hit_locations)

        # Recursively check child nodes
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
        """Checks if the given bbox overlaps with the specified grid position."""
        page_width, page_height = page_dims
        x0, y0, x1, y1 = self._normalize_bbox(bbox, page_width, page_height)

        row, column = position_vector

        # 3x3 grid calculation
        grid_x0 = (column - 1) / 3 if column != -1 else 0.0
        grid_x1 = column / 3 if column != -1 else 1.0
        grid_y0 = (row - 1) / 3 if row != -1 else 0.0
        grid_y1 = row / 3 if row != -1 else 1.0

        # Check for overlap
        x_overlap = not (x1 <= grid_x0 or x0 >= grid_x1)
        y_overlap = not (y1 <= grid_y0 or y0 >= grid_y1)

        return x_overlap and y_overlap

    @staticmethod
    def _normalize_bbox(
        bbox: List[float], page_width: float, page_height: float
    ) -> List[float]:
        """Normalizes the absolute coordinate bbox to [0, 1] relative coordinates."""
        return [
            bbox[0] / page_width,
            bbox[1] / page_height,
            bbox[2] / page_width,
            bbox[3] / page_height,
        ]
