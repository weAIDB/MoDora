from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from modora.core.infra.logging.context import new_id, request_scope
from modora.core.infra.logging.setup import configure_logging
from modora.core.settings import Settings
from modora.core.infra.llm.process import ensure_llm_local_loaded, shutdown_llm_local
from modora.core.infra.ocr.manager import ensure_ocr_model_loaded
from modora.core.utils.paths import resolve_paths

# Import new v1 routers
from modora.api.v1.chat import router as chat_router
from modora.api.v1.documents import router as doc_router
from modora.api.v1.kb import router as kb_router
from modora.api.v1.tree import router as tree_router
from modora.api.v1.stats import router as stats_router
from modora.api.v1.model_instances import router as model_instances_router
from modora.api.ocr.router import router as ocr_router

settings = Settings.load()
configure_logging(settings)
logger = logging.getLogger("modora.api")


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

# Mount docs directory for static access if needed
if paths.docs_dir.exists():
    app.mount("/api/files", StaticFiles(directory=str(paths.docs_dir)), name="files")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat_router, prefix="/api")
app.include_router(doc_router, prefix="/api")
app.include_router(kb_router, prefix="/api")
app.include_router(tree_router, prefix="/api")
app.include_router(stats_router, prefix="/api")
app.include_router(model_instances_router, prefix="/api")
app.include_router(ocr_router, prefix="/api")


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
