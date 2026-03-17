TREE_RECOMPOSE_PROMPT = """
You are an expert in document structure and information architecture. Your task is to reorganize the provided document tree structure based on the user's requirements.

### User Requirements
{query}

### Current Tree Structure Schema (Simplified)
{schema}

### Instructions
1. **Analyze Structure**: Understand the current hierarchical relationships and node types of the document.
2. **Reconstruction Strategy**: Based on the user's request, regroup, add, remove, or adjust the hierarchy of nodes.
3. **Node Requirements**:
   - Prefer using original titles from the provided Schema so the system can map them back to the original data.
   - You can create new category nodes (e.g., "Core Concepts", "Technical Details", "Overview") as parent nodes if needed to better organize the content.
   - Ensure the output follows the exact JSON structure provided below.
4. **Output Integrity**: 
   - Return ONLY the raw JSON content. 
   - DO NOT include any Markdown code block tags (like ```json), explanations, or preamble.

### Output Format Example
{{
    "title": "Root Node Title",
    "type": "chapter",
    "children": [
        {{
            "title": "New Chapter A",
            "type": "chapter",
            "children": [
                {{ "title": "Original Node Title 1", "type": "section", "children": [] }},
                {{ "title": "Original Node Title 2", "type": "section", "children": [] }}
            ]
        }}
    ]
}}
"""
