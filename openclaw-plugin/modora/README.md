# MoDora OpenClaw Plugin

This plugin exposes a running MoDora backend as optional OpenClaw agent tools. The plugin itself is thin: it forwards validated requests to MoDora's FastAPI service, so MoDora remains the system of record for document ingestion, OCR, tree generation, and QA.

## Requirements

- Node.js 20+
- A running MoDora backend reachable from the OpenClaw Gateway host
- OpenClaw installed on the machine that runs the Gateway

## What It Adds

The plugin registers these optional tools:

- `modora_upload_document`
- `modora_list_documents`
- `modora_get_document_status`
- `modora_ask_documents`
- `modora_get_tree`
- `modora_recompose_tree`
- `modora_get_document_stats`

## Install The Plugin

From the repository root during development:

```bash
openclaw plugins install ./openclaw-plugin/modora
openclaw plugins enable modora
```

For npm distribution, use:

```bash
openclaw plugins install @weaidb/modora
openclaw plugins enable modora
```

Restart the OpenClaw Gateway after install or enable.

## Configure OpenClaw

Configure `plugins.entries.modora.config`:

```json
{
  "plugins": {
    "entries": {
      "modora": {
        "enabled": true,
        "config": {
          "baseUrl": "https://modora.pro",
          "timeoutMs": 120000
        }
      }
    }
  }
}
```

Because all tools are registered as optional, add the plugin to an allowlist for the agent that should use MoDora:

```json
{
  "agents": {
    "list": [
      {
        "id": "main",
        "tools": {
          "allow": ["modora"]
        }
      }
    ]
  }
}
```

## Tool Behavior

- `modora_upload_document`: Upload a local PDF path into MoDora. Processing starts asynchronously.
- `modora_get_document_status`: Poll processing status for an uploaded file until it reaches `completed`.
- `modora_list_documents`: List the documents currently known to MoDora.
- `modora_ask_documents`: Ask a question over one or more processed documents.
- `modora_get_tree`: Fetch the current tree payload for a document.
- `modora_recompose_tree`: Recompose the tree with a built-in rule or an AI instruction.
- `modora_get_document_stats`: Return structural statistics derived from OCR and tree caches.

## Typical Workflow

1. Start the MoDora backend.
2. Upload a PDF with `modora_upload_document`.
3. Poll `modora_get_document_status` until it reports `completed`.
4. Ask questions with `modora_ask_documents`.
5. Use `modora_get_tree` or `modora_recompose_tree` when the user asks about hierarchy or structure.

## MoDora Backend Setup

This repository's backend is configured through `local.json`. The default `setup.sh` installs a full GPU-oriented stack and expects valid remote-model credentials in `local.json`, including embedding and rerank API keys. If those values are missing, backend setup stops early.

Minimum practical steps for local testing:

```bash
cp local.example.json local.json
# fill in required API keys and model settings
./setup.sh
./start_backend.sh
```

The default plugin target is `https://modora.pro`. Override `baseUrl` when you need to point OpenClaw at a local or staging backend.

## Troubleshooting

- If installation succeeds but tools do nothing, verify the MoDora backend is running and reachable at `baseUrl`.
- If upload works but QA fails, the document may still be processing or your `local.json` model settings may be incomplete.
- If backend setup fails during `./setup.sh`, check whether required API keys are missing or whether package downloads are blocked by the current environment.
