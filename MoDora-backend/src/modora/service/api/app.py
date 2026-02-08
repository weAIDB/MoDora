from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from modora.core.infra.logging.context import new_id, request_scope
from modora.core.infra.logging.setup import configure_logging
from modora.core.settings import Settings
from modora.service.api.llm_local import ensure_llm_local_loaded, shutdown_llm_local
from modora.service.api.ocr.router import router as ocr_router
from modora.service.api.ocr.runtime import ensure_ocr_model_loaded
from modora.service.api.modora.router import router as modora_router
from modora.service.api.modora.paths import resolve_paths

settings = Settings.load()
configure_logging(settings)
logger = logging.getLogger("modora.service")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_llm_local_loaded(settings, logger)
    try:
        ensure_ocr_model_loaded(settings, logger)
    except Exception as e:
        logger.warning(f"ocr model init failed: {e}")
    try:
        yield
    finally:
        shutdown_llm_local()


app = FastAPI(title=settings.service_name, lifespan=lifespan)
paths = resolve_paths(settings)
app.mount("/api/files", StaticFiles(directory=str(paths.docs_dir)), name="files")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(ocr_router)
app.include_router(modora_router)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    rid = new_id("req_", 8)
    with request_scope(request_id=rid):
        logger.info(f"{request.method} {request.url.path} start")
        res = await call_next(request)
        logger.info(
            f"{request.method} {request.url.path} done status={res.status_code}"
        )
        return res


@app.get("/health")
def health():
    return {"status": "ok"}
