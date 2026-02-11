export const SETTINGS_SCHEMA_VERSION = 1;

export const DEFAULT_SETTINGS = {
  schemaVersion: SETTINGS_SCHEMA_VERSION,
  apiKey: '',
  baseUrl: '',
  layoutModel: 'ppstructure',
  selectedMode: 'local',
  qaModel: 'qwen-vl-local',
  treeModel: 'qwen-vl-local',
};

export const SETTINGS_KEYS = Object.keys(DEFAULT_SETTINGS);

export function normalizeSettings(raw) {
  const base = { ...DEFAULT_SETTINGS };
  if (!raw || typeof raw !== 'object') return base;

  for (const key of SETTINGS_KEYS) {
    if (raw[key] !== undefined) base[key] = raw[key];
  }

  if (base.selectedMode !== 'local' && base.selectedMode !== 'remote') {
    base.selectedMode = DEFAULT_SETTINGS.selectedMode;
  }

  return base;
}

