export const SETTINGS_SCHEMA_VERSION = 3;

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

const DEFAULT_PIPELINE_CONFIG = {
  modelInstance: 'local-default',
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
};

function normalizePipelineConfig(raw) {
  const cfg = { ...DEFAULT_PIPELINE_CONFIG };
  if (raw && typeof raw === 'object') {
    if (typeof raw.modelInstance === 'string' && raw.modelInstance.trim()) {
      cfg.modelInstance = raw.modelInstance.trim();
    }
  }
  return cfg;
}

export function normalizeSettings(raw) {
  let source = raw;
  if (!source || typeof source !== 'object') {
    return { ...DEFAULT_SETTINGS };
  }

  if (Number(source.schemaVersion || 0) !== SETTINGS_SCHEMA_VERSION) {
    return { ...DEFAULT_SETTINGS };
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

  return normalized;
}
