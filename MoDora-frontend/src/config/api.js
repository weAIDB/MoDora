const apiBase = (import.meta.env.VITE_MODORA_API_BASE || '').trim().replace(/\/$/, '');

export const getApiUrl = (path) => {
  if (!apiBase) return path;
  return `${apiBase}${path}`;
};

export const apiFetch = (path, init = {}) => {
  const nextInit = { ...init, credentials: 'include' };
  return fetch(getApiUrl(path), nextInit);
};

export const createApiXhr = () => {
  const xhr = new XMLHttpRequest();
  xhr.withCredentials = true;
  return xhr;
};
