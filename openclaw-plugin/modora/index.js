import path from "node:path";
import { access } from "node:fs/promises";
import { openAsBlob } from "node:fs";

const PLUGIN_ID = "modora";
const DEFAULT_BASE_URL = "https://api.modora.pro";
const DEFAULT_TIMEOUT_MS = 120000;

function getPluginConfig(api) {
  return api?.config?.plugins?.entries?.[PLUGIN_ID]?.config ?? {};
}

function getBaseUrl(api) {
  const cfg = getPluginConfig(api);
  return String(cfg.baseUrl || DEFAULT_BASE_URL).replace(/\/+$/, "");
}

function getTimeoutMs(api) {
  const cfg = getPluginConfig(api);
  const value = Number(cfg.timeoutMs);
  return Number.isFinite(value) && value > 0 ? value : DEFAULT_TIMEOUT_MS;
}

function formatJson(value) {
  return JSON.stringify(value, null, 2);
}

function textResult(text) {
  return { content: [{ type: "text", text }] };
}

async function requestJson(api, method, endpoint, { body, headers } = {}) {
  const baseUrl = getBaseUrl(api);
  const timeoutMs = getTimeoutMs(api);
  const response = await fetch(`${baseUrl}${endpoint}`, {
    method,
    headers: {
      Accept: "application/json",
      ...headers,
    },
    body,
    signal: AbortSignal.timeout(timeoutMs),
  });

  const raw = await response.text();
  let parsed = null;
  if (raw) {
    try {
      parsed = JSON.parse(raw);
    } catch {
      parsed = raw;
    }
  }

  if (!response.ok) {
    const detail =
      parsed && typeof parsed === "object" && "detail" in parsed
        ? parsed.detail
        : parsed;
    throw new Error(
      `MoDora request failed (${response.status} ${response.statusText}): ${typeof detail === "string" ? detail : formatJson(detail)}`
    );
  }

  return parsed;
}

async function uploadDocument(api, params) {
  const resolvedPath = path.resolve(params.file_path);
  await access(resolvedPath);
  const form = new FormData();
  const filename = params.file_name || path.basename(resolvedPath);
  const fileBlob = await openAsBlob(resolvedPath, { type: "application/pdf" });
  form.append("file", fileBlob, filename);
  if (params.settings) {
    form.append("settings", JSON.stringify(params.settings));
  }

  const result = await requestJson(api, "POST", "/api/upload", { body: form });
  return textResult(
    [
      `Uploaded document: ${result.filename || filename}`,
      `Status: ${result.status || "unknown"}`,
      result.message ? `Message: ${result.message}` : null,
    ]
      .filter(Boolean)
      .join("\n")
  );
}

async function listDocuments(api) {
  const result = await requestJson(api, "GET", "/api/kb/docs");
  const docs = Array.isArray(result)
    ? result
    : result && typeof result === "object"
      ? Object.entries(result).map(([fileName, info]) => ({
          file_name: fileName,
          ...(info && typeof info === "object" ? info : {}),
        }))
      : [];
  if (docs.length === 0) {
    return textResult("MoDora has no indexed documents.");
  }
  const lines = [];
  for (const doc of docs) {
    const stats = doc.stats && typeof doc.stats === "object" ? doc.stats : {};
    const tags = Array.isArray(doc.tags) ? doc.tags : [];
    const semanticTags = Array.isArray(doc.semantic_tags) ? doc.semantic_tags : [];
    lines.push(`- ${doc.file_name || "unknown"}`);
    lines.push(`  pages=${stats.pages ?? "?"} nodes=${stats.nodes ?? "?"} depth=${stats.depth ?? "?"}`);
    if (tags.length > 0) {
      lines.push(`  tags=${tags.join(", ")}`);
    }
    if (semanticTags.length > 0) {
      lines.push(`  semantic_tags=${semanticTags.slice(0, 5).join(", ")}`);
    }
    if (doc.added_at) {
      lines.push(`  added_at=${doc.added_at}`);
    }
  }
  return textResult(lines.join("\n"));
}

async function getDocumentStatus(api, params) {
  const result = await requestJson(
    api,
    "GET",
    `/api/task/status/${encodeURIComponent(params.file_name)}`
  );
  return textResult(formatJson(result));
}

async function askDocuments(api, params) {
  const payload = {
    query: params.query,
    file_names: params.file_names,
    settings: params.settings,
  };
  const result = await requestJson(api, "POST", "/api/chat", {
    body: JSON.stringify(payload),
    headers: {
      "Content-Type": "application/json",
    },
  });

  const lines = [`Answer: ${result.answer || ""}`];
  const retrieved = Array.isArray(result.retrieved_documents)
    ? result.retrieved_documents
    : [];
  if (retrieved.length > 0) {
    lines.push("");
    lines.push("Retrieved documents:");
    for (const item of retrieved.slice(0, 8)) {
      lines.push(
        `- ${item.file_name || "unknown"} page=${item.page} score=${item.score ?? 0}`
      );
    }
  }
  if (result.node_impacts && Object.keys(result.node_impacts).length > 0) {
    lines.push("");
    lines.push(`Node impacts: ${formatJson(result.node_impacts)}`);
  }
  return textResult(lines.join("\n"));
}

async function getTree(api, params) {
  const result = await requestJson(api, "POST", "/api/tree", {
    body: JSON.stringify({ file_name: params.file_name }),
    headers: {
      "Content-Type": "application/json",
    },
  });
  return textResult(formatJson(result));
}

async function recomposeTree(api, params) {
  const payload = {
    file_name: params.file_name,
    rule: params.rule,
    user_query: params.user_query,
    settings: params.settings,
  };
  const result = await requestJson(api, "POST", "/api/tree/recompose", {
    body: JSON.stringify(payload),
    headers: {
      "Content-Type": "application/json",
    },
  });
  return textResult(formatJson(result));
}

async function getDocumentStats(api, params) {
  const result = await requestJson(
    api,
    "GET",
    `/api/docs/stats/${encodeURIComponent(params.file_name)}`
  );
  return textResult(formatJson(result));
}

function registerTool(api, definition) {
  api.registerTool(definition, { optional: true });
}

export default function modoraPlugin(api) {
  registerTool(api, {
    name: "modora_upload_document",
    description:
      "Upload a local PDF into the running MoDora backend for OCR, tree building, and later QA.",
    parameters: {
      type: "object",
      additionalProperties: false,
      properties: {
        file_path: {
          type: "string",
          description: "Absolute or relative path to a local PDF file.",
        },
        file_name: {
          type: "string",
          description: "Optional filename override shown inside MoDora.",
        },
        settings: {
          type: "object",
          additionalProperties: true,
          description: "Optional MoDora UI/settings payload.",
        },
      },
      required: ["file_path"],
    },
    async execute(_id, params) {
      return uploadDocument(api, params);
    },
  });

  registerTool(api, {
    name: "modora_list_documents",
    description: "List documents currently indexed by MoDora.",
    parameters: {
      type: "object",
      additionalProperties: false,
      properties: {},
    },
    async execute() {
      return listDocuments(api);
    },
  });

  registerTool(api, {
    name: "modora_get_document_status",
    description: "Check whether an uploaded document has finished processing.",
    parameters: {
      type: "object",
      additionalProperties: false,
      properties: {
        file_name: {
          type: "string",
          description: "Document filename as stored in MoDora.",
        },
      },
      required: ["file_name"],
    },
    async execute(_id, params) {
      return getDocumentStatus(api, params);
    },
  });

  registerTool(api, {
    name: "modora_ask_documents",
    description: "Ask a question against one or more processed documents in MoDora.",
    parameters: {
      type: "object",
      additionalProperties: false,
      properties: {
        query: {
          type: "string",
          description: "Question to answer from the selected documents.",
        },
        file_names: {
          type: "array",
          items: { type: "string" },
          minItems: 1,
          description: "One or more processed document filenames.",
        },
        settings: {
          type: "object",
          additionalProperties: true,
          description: "Optional MoDora UI/settings payload.",
        },
      },
      required: ["query", "file_names"],
    },
    async execute(_id, params) {
      return askDocuments(api, params);
    },
  });

  registerTool(api, {
    name: "modora_get_tree",
    description: "Fetch the current VueFlow tree payload for a document.",
    parameters: {
      type: "object",
      additionalProperties: false,
      properties: {
        file_name: {
          type: "string",
          description: "Processed document filename.",
        },
      },
      required: ["file_name"],
    },
    async execute(_id, params) {
      return getTree(api, params);
    },
  });

  registerTool(api, {
    name: "modora_recompose_tree",
    description:
      "Recompose a document tree using a built-in rule or an AI-guided query.",
    parameters: {
      type: "object",
      additionalProperties: false,
      properties: {
        file_name: {
          type: "string",
          description: "Processed document filename.",
        },
        rule: {
          type: "string",
          description: "Recompose rule such as balanced or ai.",
          default: "balanced",
        },
        user_query: {
          type: "string",
          description: "Required when rule=ai; explains the desired structure.",
        },
        settings: {
          type: "object",
          additionalProperties: true,
          description: "Optional MoDora UI/settings payload.",
        },
      },
      required: ["file_name"],
    },
    async execute(_id, params) {
      return recomposeTree(api, {
        ...params,
        rule: params.rule || "balanced",
      });
    },
  });

  registerTool(api, {
    name: "modora_get_document_stats",
    description: "Return structural statistics for a processed document.",
    parameters: {
      type: "object",
      additionalProperties: false,
      properties: {
        file_name: {
          type: "string",
          description: "Processed document filename.",
        },
      },
      required: ["file_name"],
    },
    async execute(_id, params) {
      return getDocumentStats(api, params);
    },
  });
}
