---
name: modora
description: Use this skill to analyze PDFs with a remote MoDora HTTP service. This skill requires a user-provided settings.json and sends the user's model endpoint and API credentials to the MoDora server for processing. Only use it if you trust that server.
user-invocable: true
---

# MoDora

Use this skill to work with a deployed MoDora service over HTTP.

This skill is for external skill access, not for the logged-in MoDora web UI.

## Security Warning

This skill sends the user's `settings.json` to the remote MoDora service.
That file may contain model endpoints and API credentials.

The intended behavior of this MoDora deployment is to use those settings only
for the current request flow and not as a shared server default for other users.
This deployment is not intended to maliciously store or reuse those credentials.
However, the credentials are still transmitted to a remote service, and that trust
boundary is real.

Only use this skill if you trust the operator of the target MoDora server.
If you do not trust that server, do not use this skill and deploy MoDora locally instead.

This skill is appropriate when the user wants to:
- upload a PDF to MoDora
- wait for document preprocessing to complete
- ask questions about one uploaded document
- verify that the public MoDora service is reachable

This skill assumes the MoDora backend is exposed as an HTTP base URL. Set `MODORA_BASE_URL` before running scripts. Example:

```bash
export MODORA_BASE_URL="https://api.modora.pro"
```

If `MODORA_BASE_URL` is unset, scripts default to `https://api.modora.pro`.

The scripts are implemented in Python so they work across Linux, macOS, Windows, and WSL as long as `python3` is available.

Skill access is separate from the logged-in frontend:
- skill requests send `X-Modora-Client: skill`
- skill requests do not use the frontend login session
- skill requests must provide a user-owned settings JSON file
- skill requests cannot use server default model instance IDs such as `local-default` or `remote-default`
- if the user does not provide a valid settings file, the skill must stop instead of falling back to server defaults
- skill scripts require explicit acknowledgement before sending credentials to the remote MoDora service

## Required settings file

Every skill invocation that uploads a document or asks a question must provide a user-owned `settings.json`.

Start from `skill/settings.template.json` and fill in the user's own values.

The settings file must:
- be provided by the skill user, not copied from the server UI defaults
- be completed by the agent or user with the user's own model credentials and endpoints
- include `pipelines.<module>.modelInstance` for each pipeline module
- define model instances that include the user's own `api_key`, `base_url`, and model identifier where required
- avoid server default model instance IDs such as `local-default` and `remote-default`
- use multimodal-capable model instances for the MoDora pipeline

MoDora requires multimodal models. Do not choose text-only models for OCR-adjacent reasoning, enrichment, retrieval, metadata generation, or QA.

If the user does not provide this file, stop and report the requirement. Do not continue with upload or QA.

## Preferred workflow

1. Prepare a `settings.json` file owned by the skill user.
   A good starting point is `skill/settings.template.json`.
2. Run `python skill/scripts/health.py` to verify the backend is alive.
3. Confirm that you trust the remote MoDora service operator and explicitly allow remote credential transfer.
4. Run `python skill/scripts/upload.py /absolute/path/to/file.pdf --settings-file /path/to/settings.json --allow-remote-credentials` to upload a document.
5. Run `python skill/scripts/wait.py <filename>` until processing reaches `completed`.
6. Run `python skill/scripts/chat.py <filename> "<question>" --settings-file /path/to/settings.json --allow-remote-credentials` to ask a question.

For the common one-shot flow, prefer:

```bash
python skill/scripts/analyze_pdf.py /absolute/path/to/file.pdf "Your question" --settings-file /path/to/settings.json --allow-remote-credentials
```

## Rules

- Always use an absolute file path when uploading.
- Always provide a user-owned settings JSON file.
- The agent should help fill in the user's own API settings instead of relying on server defaults.
- Explicitly confirm remote credential transfer before running upload or chat commands.
- Never fall back to server-side defaults when the settings file is missing.
- Do not call `chat.py` before the task status becomes `completed`.
- Do not use server default model instance IDs such as `local-default` or `remote-default`.
- Use multimodal-capable model instances across the MoDora pipeline.
- If the backend returns an error, surface the response body instead of hiding it.
- If the service is unreachable, tell the user the MoDora public backend is not available.
- If the user supplies a different service URL, set `MODORA_BASE_URL` for that command.

## Script summary

- `scripts/health.py`: GET `/health`
- `scripts/upload.py`: POST `/api/upload` after explicit remote credential acknowledgement
- `scripts/wait.py`: poll GET `/api/task/status/{filename}`
- `scripts/chat.py`: POST `/api/chat` after explicit remote credential acknowledgement
- `scripts/analyze_pdf.py`: health -> upload -> wait -> chat with explicit remote credential acknowledgement
