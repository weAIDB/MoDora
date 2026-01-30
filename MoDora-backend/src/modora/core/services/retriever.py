from __future__ import annotations

import ast
import asyncio
import json
import logging
import re

import fitz

from modora.core.domain.cctree import CCTree, CCTreeNode
from modora.core.domain.component import Location
from modora.core.infra.llm.qwen import AsyncQwenLLMClient
import concurrent.futures
from modora.core.infra.pdf.cropper import PDFCropper, crop_pdf_image_task


class AsyncRetriever:
    def __init__(
        self,
        llm_client: AsyncQwenLLMClient,
        cropper: PDFCropper,
        logger: logging.Logger,
        max_workers: int = 16,
    ):
        self.llm = llm_client
        self.cropper = cropper
        self.logger = logger
        self.sem = asyncio.Semaphore(max_workers)
        # Use ProcessPoolExecutor to avoid GIL and fitz thread-safety issues
        self.proc_pool = concurrent.futures.ProcessPoolExecutor(max_workers=max_workers)

    def __del__(self):
        self.proc_pool.shutdown(wait=False)

    async def retrieve(
        self, query: str, cctree: CCTree, source_path: str, question_id: str | int = "N/A"
    ) -> tuple[dict[str, str], dict[str, list[dict]]]:
        """
        执行异步检索。

        Returns:
            retrieve_result: {path: text_evidence}
            retrieve_bbox: {path: [location_dicts]}
        """
        # 1. Parse Question
        locations, content_query = await self._parse_question(query, question_id)
        self.logger.info(
            f"Parsed query: content='{content_query}', locations={locations}",
            extra={"question_id": question_id},
        )

        # 2. Start Recursive Search
        if not cctree.root:
            return {}, {}

        return await self._select_and_check_by_level(
            {"root": cctree.root}, content_query, source_path, locations, question_id
        )

    async def _parse_question(
        self, query: str, question_id: str | int = "N/A"
    ) -> tuple[list[dict], str]:
        """解析问题，提取位置约束和核心语义。"""
        try:
            res = await self.llm.parse_question(query)
            location_match = re.search(r"-location:\s*(\[.*\])", res, re.DOTALL)
            content_match = re.search(r"-content:\s*(.*)", res, re.DOTALL)

            locations = []
            content = query

            if location_match:
                try:
                    locations = json.loads(location_match.group(1))
                except json.JSONDecodeError:
                    self.logger.warning(
                        f"Failed to parse location JSON: {location_match.group(1)}",
                        extra={"question_id": question_id},
                    )

            if content_match:
                content = content_match.group(1).strip()

            return locations, content
        except Exception as e:
            self.logger.error(
                f"Error parsing question: {e}", extra={"question_id": question_id}
            )
            return [], query

    async def _select_and_check_by_level(
        self,
        cur_level: dict[str, CCTreeNode],
        query: str,
        source_path: str,
        locations: list[dict],
        question_id: str | int = "N/A",
    ) -> tuple[dict, dict]:
        retrieve_result = {}
        retrieve_bbox = {}
        selected_children = {}

        if not cur_level:
            return retrieve_result, retrieve_bbox

        # 并发处理当前层的所有节点
        tasks = []
        for path, node in cur_level.items():
            tasks.append(
                self._process_single_node(
                    path, node, query, source_path, locations, question_id
                )
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, res in enumerate(results):
            if isinstance(res, Exception):
                self.logger.error(
                    f"Error processing node: {res}", extra={"question_id": question_id}
                )
                continue

            rr, rb, sc = res
            retrieve_result.update(rr)
            retrieve_bbox.update(rb)
            selected_children.update(sc)

        # 递归处理下一层
        if selected_children:
            sub_rr, sub_rb = await self._select_and_check_by_level(
                selected_children, query, source_path, locations, question_id
            )
            retrieve_result.update(sub_rr)
            retrieve_bbox.update(sub_rb)

        return retrieve_result, retrieve_bbox

    async def _process_single_node(
        self,
        path: str,
        node: CCTreeNode,
        query: str,
        source_path: str,
        locations: list[dict],
        question_id: str | int = "N/A",
    ) -> tuple[dict, dict, dict]:
        async with self.sem:
            self.logger.info(
                f"Processing node: {path}", extra={"question_id": question_id}
            )
            retrieve_result = {}
            retrieve_bbox = {}
            selected_children = {}

            base_path = path.split("--")[-1] if "--" in path else path

            # 1. Backward Verification (Check Node)
            curloc_res = True
            within_locs: list[Location] = []

            if not locations:
                within_locs = node.location
            else:
                curloc_res, within_locs = await asyncio.to_thread(
                    self._check_location, node, source_path, locations, True
                )

            # 如果位置符合且不是 root/MROOT，则检查内容
            if node.type not in ["root", "MROOT"] and curloc_res:
                is_relevant = False
                try:
                    if within_locs:
                        # Prepare picklable data for process pool
                        bbox_data = [
                            {"page": loc.page, "bbox": loc.bbox} for loc in within_locs
                        ]
                        loop = asyncio.get_running_loop()
                        base64_image = await loop.run_in_executor(
                            self.proc_pool,
                            crop_pdf_image_task,
                            source_path,
                            bbox_data,
                        )
                        text_data = f"{base_path}: {node.data}"
                        self.logger.info(
                            f"Check node MM input: text='{text_data}', query='{query}', image_len={len(base64_image)}",
                            extra={"question_id": question_id},
                        )
                        is_relevant = await self.llm.check_node_mm(
                            text_data, base64_image, query
                        )
                    else:
                        self.logger.info(
                            f"Check node input: text='{node.data}', query='{query}'",
                            extra={"question_id": question_id},
                        )
                        is_relevant = await self.llm.check_node(node.data, query)
                except Exception as e:
                    self.logger.warning(
                        f"Check node failed for {path}: {e}",
                        extra={"question_id": question_id},
                    )
                    is_relevant = False

                if is_relevant:
                    self.logger.info(
                        f"Node relevant: {path}", extra={"question_id": question_id}
                    )
                    retrieve_result[path] = node.data
                    # 统一转为 dict 输出
                    bbox_dicts = [loc.to_dict() for loc in within_locs]
                    for d in bbox_dicts:
                        d["source_path"] = source_path
                    retrieve_bbox[path] = bbox_dicts
                else:
                    self.logger.info(
                        f"Node NOT relevant: {path}", extra={"question_id": question_id}
                    )

            # 2. Forward Search (Select Children)
            if not node.children:
                return retrieve_result, retrieve_bbox, selected_children

            # 先按位置过滤子节点
            children_keys = list(node.children.keys())
            if locations:
                children_keys = await asyncio.to_thread(
                    self._filt_by_location, node, source_path, locations
                )
                self.logger.info(
                    f"Filtered children by location: {len(children_keys)}/{len(node.children)}",
                    extra={"question_id": question_id},
                )

            if not children_keys:
                return retrieve_result, retrieve_bbox, selected_children

            # LLM 选择子节点
            metadata_map = {k: str(node.children[k].metadata) for k in children_keys}

            try:
                select_res = await self.llm.select_children(
                    children_keys, query, path, str(metadata_map)
                )
                selected_keys = ast.literal_eval(select_res)
                if not isinstance(selected_keys, list):
                    selected_keys = []
            except Exception as e:
                self.logger.warning(
                    f"Select children failed: {e}", extra={"question_id": question_id}
                )
                selected_keys = []

            # 收集选中的子节点
            for key in selected_keys:
                if key in node.children:
                    self.logger.info(
                        f"Selected child: {path}--{key}",
                        extra={"question_id": question_id},
                    )
                    child_path = f"{path}--{key}"
                    selected_children[child_path] = node.children[key]

            return retrieve_result, retrieve_bbox, selected_children

    def _check_location(
        self,
        node: CCTreeNode,
        source_path: str,
        target_locations: list[dict],
        only_self: bool = False,
    ) -> tuple[bool, list[Location]]:
        """检查节点位置是否在目标区域内。"""
        if not target_locations:
            return True, []

        try:
            doc = fitz.open(source_path)
            page_count = doc.page_count
        except Exception:
            return False, []

        # 预处理 targets
        processed_targets = []
        for loc in target_locations:
            p = loc.get("page", 0)
            grids_str = loc.get("grid", [])
            parsed_grids = []
            for g in grids_str:
                try:
                    g = g.strip("()")
                    r, c = map(int, g.split(","))
                    parsed_grids.append((r, c))
                except:
                    pass
            if not parsed_grids:
                parsed_grids = [(-1, -1)]

            if p == 0:
                for i in range(1, page_count + 1):
                    processed_targets.append({"page": i, "grids": parsed_grids})
            elif p < 0:
                np = page_count + p + 1
                if 1 <= np <= page_count:
                    processed_targets.append({"page": np, "grids": parsed_grids})
            else:
                processed_targets.append({"page": p, "grids": parsed_grids})

        flag = False
        within_locs: list[Location] = []

        # Check current node
        for loc in node.location:
            # Check page index
            try:
                page = doc[loc.page - 1]
                page_w, page_h = page.rect.width, page.rect.height
            except:
                continue

            for t in processed_targets:
                if t["page"] == loc.page:
                    bbox = loc.bbox  # [x0, y0, x1, y1]
                    for r, c in t["grids"]:
                        if r == -1:  # Whole page
                            flag = True
                            within_locs.append(loc)
                            break

                        # Normalized
                        nx0, ny0 = bbox[0] / page_w, bbox[1] / page_h
                        nx1, ny1 = bbox[2] / page_w, bbox[3] / page_h

                        # Grid (3x3)
                        gx0 = (c - 1) / 3.0 if c != -1 else 0
                        gx1 = c / 3.0 if c != -1 else 1
                        gy0 = (r - 1) / 3.0 if r != -1 else 0
                        gy1 = r / 3.0 if r != -1 else 1

                        # Overlap
                        x_overlap = not (nx1 <= gx0 or nx0 >= gx1)
                        y_overlap = not (ny1 <= gy0 or ny0 >= gy1)

                        if x_overlap and y_overlap:
                            flag = True
                            within_locs.append(loc)
                            break
                # Do not break here to collect all locations across pages
                # if flag and loc in within_locs:
                #    break

        doc.close()

        if flag:
            return True, within_locs

        # Recursively check children
        if not only_self and node.children:
            for child in node.children.values():
                res, _ = self._check_location(
                    child, source_path, target_locations, only_self=False
                )
                if res:
                    return True, []

        return False, []

    def _filt_by_location(
        self, node: CCTreeNode, source_path: str, locations: list[dict]
    ) -> list[str]:
        if not locations:
            return list(node.children.keys())

        filtered_keys = []
        for key, child in node.children.items():
            res, _ = self._check_location(
                child, source_path, locations, only_self=False
            )
            if res:
                filtered_keys.append(key)
        return filtered_keys
