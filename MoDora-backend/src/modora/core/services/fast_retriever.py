
import logging
import asyncio
from modora.core.domain.cctree import CCTreeNode
from modora.core.domain.component import Location
from modora.core.services.retriever import AsyncRetriever
from modora.core.infra.pdf.cropper import crop_pdf_image_task

class FastLocationAsyncRetriever(AsyncRetriever):
    """
    一个专门针对位置查询优化的检索器。
    
    策略:
    1. 如果查询包含明确的位置约束：
       - 直接跳转到目标位置内的节点。
       - 如果中间节点只是结构容器，跳过语义相关性检查。
       - 仅当位置内存在多个候选节点时，才执行语义筛选（目前简化为全选）。
    
    2. 如果没有位置约束：
       - 回退到标准的语义检索逻辑（通过 super 类）。
    """

    async def _process_single_node(
        self,
        path: str,
        node: CCTreeNode,
        query: str,
        source_path: str,
        locations: list[dict],
        question_id: str | int = "N/A",
    ) -> tuple[dict, dict, dict, dict, list]:
        """
        重写的处理逻辑。
        """
        # 如果没有位置信息，回退到标准逻辑
        
        # 这里做一个简单的启发式检查：如果 locations 为空，或者解析后包含全文档通配符
        if not locations:
            return await super()._process_single_node(
                path, node, query, source_path, locations, question_id
            )
        
        is_full_doc = False
        for loc in locations:
            if loc.get("page", 0) == 0 and not loc.get("grid"):
                is_full_doc = True
                break
        
        if is_full_doc:
            return await super()._process_single_node(
                path, node, query, source_path, locations, question_id
            )

        async with self.sem:
            self.logger.info(
                f"[FastLoc] Processing node: {path}", extra={"question_id": question_id}
            )
            retrieve_result = {}
            retrieve_bbox = {}
            retrieve_images = {}
            selected_children = {}
            node_trace = []

            # 1. 位置检查 (关键步骤)
            curloc_res, within_locs = await asyncio.to_thread(
                self._check_location, node, source_path, locations, True
            )
            
            node_trace.append({
                "step": "check_location",
                "path": path,
                "result": curloc_res,
                "locations_count": len(within_locs)
            })

            # 移除剪枝逻辑：即使当前节点位置不匹配，也继续检查子节点
            # 因为可能存在“父节点很大（位置未精确匹配）但子节点在目标区域内”的情况

            is_relevant = False
            check_method = "skipped_location_match"

            # 检查此节点是否为“承载内容”的节点（不仅仅是 'root' 或 'Section' 等容器）
            # 并且严格位于目标区域内。
            if node.type not in ["root", "MROOT"] and curloc_res:
                
                is_relevant = True
                check_method = "location_match"

                node_trace.append({
                    "step": "check_relevance",
                    "path": path,
                    "method": check_method,
                    "is_relevant": is_relevant
                })

                if is_relevant:
                    self.logger.info(
                        f"[FastLoc] Node relevant: {path}", extra={"question_id": question_id}
                    )
                    retrieve_result[path] = node.data
                    bbox_dicts = [loc.to_dict() for loc in within_locs]
                    for d in bbox_dicts:
                        d["source_path"] = source_path
                    retrieve_bbox[path] = bbox_dicts

                    # Capture image content for Image nodes
                    if node.type and node.type.strip().lower() == "image":
                        try:
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
                            retrieve_images[path] = base64_image
                            self.logger.info(f"[FastLoc] Captured image for node: {path}", extra={"question_id": question_id})
                        except Exception as e:
                            self.logger.warning(
                                f"[FastLoc] Failed to crop image for {path}: {e}",
                                extra={"question_id": question_id}
                            )

            # 3. 子节点选择
            
            if not node.children:
                return retrieve_result, retrieve_bbox, retrieve_images, selected_children, node_trace

            # 3.1 几何过滤
            children_keys = list(node.children.keys())
            children_keys = await asyncio.to_thread(
                self._filt_by_location, node, source_path, locations
            )
            
            self.logger.info(
                f"[FastLoc] Geometric filtered children: {len(children_keys)}",
                extra={"question_id": question_id},
            )

            if not children_keys:
                return retrieve_result, retrieve_bbox, retrieve_images, selected_children, node_trace

            selected_keys = children_keys # 默认：获取所有几何上有效的子节点
            
            if len(selected_keys) > 10:
                self.logger.warning(
                    f"[FastLoc] Too many children selected ({len(selected_keys)}) at {path}. "
                    "This might indicate a loose location constraint or a dense node.",
                    extra={"question_id": question_id}
                )
            
            node_trace.append({
                "step": "select_children",
                "path": path,
                "strategy": "geometric_only",
                "selected_keys": selected_keys
            })

            # 收集选中的子节点
            for key in selected_keys:
                if key in node.children:
                    child_path = f"{path}--{key}"
                    selected_children[child_path] = node.children[key]

            return retrieve_result, retrieve_bbox, retrieve_images, selected_children, node_trace
