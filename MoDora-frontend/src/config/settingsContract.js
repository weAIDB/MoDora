export const SETTINGS_SCHEMA_VERSION = 2;

export const MODULE_KEYS = [
  'enrichment',
  'levelGenerator',
  'metadataGenerator',
  'retriever',
  'qaService',
];

export const MODULE_LABELS = {
  enrichment: 'Enrichment',
  levelGenerator: 'LevelGenerator',
  metadataGenerator: 'MetadataGenerator',
  retriever: 'Retriever',
  qaService: 'QAService',
};

export const OCR_MODEL_OPTIONS = [
  { value: 'ppstructure', label: 'PPStructureV3' },
  { value: 'paddle_ocr_vl', label: 'PaddleOCRVL' },
];

export const LOCAL_MODEL_OPTIONS = [
  { value: 'qwen-vl-local', label: 'Qwen-VL Local' },
];

export const REMOTE_MODEL_OPTIONS = [
  { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
  { value: 'gpt-4o', label: 'GPT-4o' },
  { value: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash' },
];

export const ALL_MODEL_OPTIONS = [...LOCAL_MODEL_OPTIONS, ...REMOTE_MODEL_OPTIONS];

const DEFAULT_PIPELINE_CONFIG = {
  mode: 'local',
  model: 'qwen-vl-local',
  baseUrl: '',
  apiKey: '',
};

export const DEFAULT_SETTINGS = {
  schemaVersion: SETTINGS_SCHEMA_VERSION,
  ocr: {
    provider: 'ppstructure',
  },
  pipelines: {
    enrichment: { ...DEFAULT_PIPELINE_CONFIG },
    levelGenerator: { ...DEFAULT_PIPELINE_CONFIG },
    metadataGenerator: { ...DEFAULT_PIPELINE_CONFIG },
    retriever: { ...DEFAULT_PIPELINE_CONFIG },
    qaService: { ...DEFAULT_PIPELINE_CONFIG },
  },
  // compatibility fields for current backend parsing
  apiKey: '',
  baseUrl: '',
  layoutModel: 'ppstructure',
  selectedMode: 'local',
  qaModel: 'qwen-vl-local',
  treeModel: 'qwen-vl-local',
};

function normalizePipelineConfig(raw) {
  const cfg = { ...DEFAULT_PIPELINE_CONFIG };
  if (raw && typeof raw === 'object') {
    if (typeof raw.mode === 'string') cfg.mode = raw.mode.trim().toLowerCase();
    if (typeof raw.model === 'string' && raw.model.trim()) cfg.model = raw.model.trim();
    if (typeof raw.baseUrl === 'string') cfg.baseUrl = raw.baseUrl.trim();
    if (typeof raw.apiKey === 'string') cfg.apiKey = raw.apiKey.trim();
  }

  if (cfg.mode !== 'local' && cfg.mode !== 'remote') {
    cfg.mode = DEFAULT_PIPELINE_CONFIG.mode;
  }
  return cfg;
}

function migrateV1toV2(raw) {
  const qaModel = typeof raw?.qaModel === 'string' && raw.qaModel.trim()
    ? raw.qaModel.trim()
    : DEFAULT_PIPELINE_CONFIG.model;
  const treeModel = typeof raw?.treeModel === 'string' && raw.treeModel.trim()
    ? raw.treeModel.trim()
    : qaModel;
  const selectedMode = raw?.selectedMode === 'remote' ? 'remote' : 'local';
  const baseUrl = typeof raw?.baseUrl === 'string' ? raw.baseUrl.trim() : '';
  const apiKey = typeof raw?.apiKey === 'string' ? raw.apiKey.trim() : '';
  const provider = typeof raw?.layoutModel === 'string' && raw.layoutModel.trim()
    ? raw.layoutModel.trim()
    : 'ppstructure';

  return {
    schemaVersion: SETTINGS_SCHEMA_VERSION,
    ocr: { provider },
    pipelines: {
      enrichment: { mode: selectedMode, model: qaModel, baseUrl, apiKey },
      levelGenerator: { mode: selectedMode, model: treeModel, baseUrl, apiKey },
      metadataGenerator: { mode: selectedMode, model: treeModel, baseUrl, apiKey },
      retriever: { mode: selectedMode, model: qaModel, baseUrl, apiKey },
      qaService: { mode: selectedMode, model: qaModel, baseUrl, apiKey },
    },
  };
}

function fillCompatibilityFields(settings) {
  const next = { ...settings };
  const qa = next.pipelines.qaService;
  const tree = next.pipelines.levelGenerator;

  next.apiKey = qa.apiKey || '';
  next.baseUrl = qa.baseUrl || '';
  next.layoutModel = next.ocr.provider;
  next.selectedMode = qa.mode;
  next.qaModel = qa.model;
  next.treeModel = tree.model;
  return next;
}

export function normalizeSettings(raw) {
  let source = raw;
  if (!source || typeof source !== 'object') {
    return { ...DEFAULT_SETTINGS };
  }

  if (Number(source.schemaVersion || 1) < SETTINGS_SCHEMA_VERSION) {
    source = migrateV1toV2(source);
  }

  const normalized = {
    schemaVersion: SETTINGS_SCHEMA_VERSION,
    ocr: {
      provider: DEFAULT_SETTINGS.ocr.provider,
    },
    pipelines: {},
  };

  const ocrProvider = source?.ocr?.provider;
  if (typeof ocrProvider === 'string' && ocrProvider.trim()) {
    normalized.ocr.provider = ocrProvider.trim();
  }

  for (const key of MODULE_KEYS) {
    normalized.pipelines[key] = normalizePipelineConfig(source?.pipelines?.[key]);
  }

  return fillCompatibilityFields(normalized);
}
