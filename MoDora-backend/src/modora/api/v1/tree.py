from __future__ import annotations

import json
import logging
import asyncio
from fastapi import APIRouter, HTTPException

from modora.core.domain.cctree import CCTree
from modora.core.settings import Settings
from modora.core.utils.paths import resolve_paths
from modora.core.utils.config import settings_from_ui_payload
from modora.core.infra.llm.factory import AsyncLLMFactory
from modora.core.utils.tree import (
    convert_tree_to_vueflow,
    dict_to_tree,
    reconstruct_tree_from_elements,
    validate_tree_structure,
    TreeNode,
    recompose_tree_dict,
)
from modora.api.v1.models import (
    TreeRequest,
    TreeResponse,
    TreeUpdateRequest,
    NodeUpdateRequest,
    TreeRecomposeRequest,
)

router = APIRouter(tags=["tree"])
logger = logging.getLogger("modora.api")


@router.post("/tree", response_model=TreeResponse)
async def get_document_tree(request: TreeRequest):
    settings = Settings.load()
    paths = resolve_paths(settings)
    tree_path = paths.doc_cache_dir(request.file_name) / "tree.json"
    if not tree_path.exists():
        raise HTTPException(status_code=404, detail="Tree cache not found.")

    tree_dict = json.loads(tree_path.read_text(encoding="utf-8"))
    elements = convert_tree_to_vueflow(tree_dict, root_label=request.file_name)
    return TreeResponse(elements=elements)


@router.post("/tree/update")
def update_tree_endpoint(request: TreeUpdateRequest):
    settings = Settings.load()
    paths = resolve_paths(settings)

    tree_path = paths.doc_cache_dir(request.file_name) / "tree.json"
    if not tree_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Tree cache not found: {tree_path}"
        )

    original_tree_dict = json.loads(tree_path.read_text(encoding="utf-8"))
    try:
        new_tree_dict = reconstruct_tree_from_elements(
            request.elements, original_tree_dict, request.file_name
        )
        validate_tree_structure(new_tree_dict)
        CCTree.normalize_tree_dict(new_tree_dict)
        tree_path.write_text(
            json.dumps(new_tree_dict, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return {"status": "success", "message": "Tree structure updated."}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=f"Invalid tree structure: {ve}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tree/recompose", response_model=TreeResponse)
async def recompose_tree_endpoint(request: TreeRecomposeRequest):
    settings = Settings.load()
    paths = resolve_paths(settings)
    tree_path = paths.doc_cache_dir(request.file_name) / "tree.json"
    if not tree_path.exists():
        raise HTTPException(status_code=404, detail="Tree cache not found.")

    try:
        tree_dict = json.loads(tree_path.read_text(encoding="utf-8"))
        
        if request.rule == "ai" and request.user_query:
            root_node = dict_to_tree(tree_dict, root_title=request.file_name)
            schema = root_node.get_schema()
            
            # Resolve settings and instance_id from payload
            app_settings, _, instance_id, _ = settings_from_ui_payload(
                settings, request.settings, module_key="levelGenerator"
            )

            # If no instance_id is provided, default to a remote model
            if not instance_id:
                for inst_id, inst in app_settings.model_instances.items():
                    if inst.type == "remote" and inst.base_url and inst.api_key:
                        instance_id = inst_id
                        logger.info(f"Defaulting to remote model instance: {instance_id}")
                        break
            
            # Use actual LLM calls for tree structure recomposition
            llm_client = AsyncLLMFactory.create(app_settings, instance_id=instance_id)
            logger.info(f"AI Recompose Request: {request.user_query} using instance: {instance_id}")
            
            ai_generated_schema = await llm_client.recompose_tree(schema, request.user_query)
            
            # Reconstruct the tree based on the AI-generated schema and inherit all information from original nodes (metadata, type, etc.)
            recomposed_root = root_node.recompose_by_schema(ai_generated_schema)
            recomposed = recomposed_root.to_dict()
        else:
            recomposed = recompose_tree_dict(tree_dict, request.file_name, request.rule)
            
        elements = convert_tree_to_vueflow(recomposed, root_label=request.file_name)
        return TreeResponse(elements=elements)
    except Exception as e:
        logger.error(f"Recompose error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tree/node/update")
def update_node_endpoint(request: NodeUpdateRequest):
    settings = Settings.load()
    paths = resolve_paths(settings)
    tree_path = paths.doc_cache_dir(request.file_name) / "tree.json"
    if not tree_path.exists():
        raise HTTPException(status_code=404, detail="Tree not found")

    try:
        tree_dict = json.loads(tree_path.read_text(encoding="utf-8"))
        root = dict_to_tree(tree_dict, root_title=request.file_name)

        current_node = root
        parent_node = None
        path = list(request.target_path)
        if path:
            first_segment = path[0]
            if first_segment == root.title or first_segment == "Document Root":
                path = path[1:]

        for title in path:
            parent_node = current_node
            found = current_node.find_child(title)
            if not found:
                raise HTTPException(status_code=404, detail=f"Node not found: {title}")
            current_node = found

        if request.action == "update":
            if request.new_data:
                current_node.title = request.new_data.get("title", current_node.title)
                current_node.type = request.new_data.get("type", current_node.type)
                current_node.data = request.new_data.get("data", current_node.data)
                current_node.metadata = request.new_data.get(
                    "metadata", current_node.metadata
                )
        elif request.action == "delete":
            if parent_node:
                parent_node.delete_child(current_node)
            else:
                raise HTTPException(status_code=400, detail="Cannot delete root node")
        elif request.action == "add":
            if request.new_data:
                new_child = TreeNode(
                    title=request.new_data.get("title", "New Node"),
                    typ=request.new_data.get("type", "text"),
                    data=request.new_data.get("data", ""),
                )
                current_node.insert_child(new_child)
        else:
            raise HTTPException(status_code=400, detail="Unknown action")

        new_tree_dict = root.to_dict()
        CCTree.normalize_tree_dict(new_tree_dict)
        tree_path.write_text(
            json.dumps(new_tree_dict, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return {"status": "success", "message": f"Node {request.action}d successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
