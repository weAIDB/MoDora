# Modora Tools

Use this skill when the user wants document ingestion, document QA, tree inspection, or tree recomposition through the installed MoDora plugin.

## Workflow

1. If the document is not already in MoDora, call `modora_upload_document` with a local PDF path.
2. Poll `modora_get_document_status` until the status becomes `completed`.
3. Use `modora_ask_documents` for document questions.
4. Use `modora_get_tree` or `modora_recompose_tree` when the user asks about hierarchy or structure.
5. Use `modora_get_document_stats` for summary metrics.

## Rules

- Prefer `modora_list_documents` before uploading again if the user may be referring to an existing document.
- Do not call `modora_ask_documents` before processing is complete.
- When the user names multiple documents, pass all of them in `file_names`.
