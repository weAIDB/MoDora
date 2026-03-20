# Repository Guidelines

## Project Structure & Module Organization
`MoDora-frontend/` contains the Vue 3 + Vite client. Main app code lives in `src/`, with UI in `src/components/`, shared state/hooks in `src/composables/`, and static assets in `src/assets/` and `public/`. `MoDora-backend/` contains the FastAPI service and CLI package under `src/modora/`; keep HTTP entrypoints in `src/modora/api/`, core logic in `src/modora/core/`, and CLI flows in `src/modora/lab/`. Repository-level `datasets/` and `Results/` hold sample data and generated outputs.

## Build, Test, and Development Commands
Run `./setup.sh` once from the repo root to install the backend venv and frontend dependencies. Use `./run.sh` to start both services, or `./start_backend.sh` and `./start_frontend.sh` in separate terminals when debugging. Frontend-only work uses `cd MoDora-frontend && npm run dev`, `npm run build`, and `npm run lint`. Backend experiment workflows use `source MoDora-backend/venv/bin/activate` and `modora --help`; common examples are `modora ocr --dataset datasets/MMDA --cache-dir MoDora-backend/cache_v5` and `modora evaluate --input datasets/MMDA/test.json --result MoDora-backend/tmp/result.json`.

## Coding Style & Naming Conventions
Follow existing file conventions: Vue components use PascalCase filenames such as `ChatWindow.vue`, composables use `useXxx.js`, and backend packages/modules use snake_case. Use 2 spaces in frontend config and JavaScript where already established, and 4 spaces in Python. Keep FastAPI routers thin; move reusable logic into `modora.core`. Run `npm run lint` before submitting frontend changes.

## Testing Guidelines
There is no full automated test suite yet, so contributors should treat smoke testing as required. For backend checks, review `MoDora-backend/test.sh` and run targeted CLI flows against the sample `datasets/MMDA` data. For frontend changes, verify the affected view in `npm run dev` and confirm production build success with `npm run build`. Name any new Python tests `test_*.py` near the relevant module or under a future `tests/` package.

## Commit & Pull Request Guidelines
Recent history uses short, imperative subjects such as `Trim dev data to minimal samples` and `Update scenario`. Keep commits focused and descriptive. Pull requests should explain the user-visible impact, list config or dataset assumptions, link related issues, and include screenshots or short recordings for UI changes.
