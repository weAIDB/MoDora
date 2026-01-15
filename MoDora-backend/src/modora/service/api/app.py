from __future__ import annotations

import logging

from fastapi import FastAPI, Request

from modora.core.logging_context import new_id, request_scope
from modora.core.logging_setup import configure_logging
from modora.core.settings import Settings

settings = Settings.load()
configure_logging(settings)
logger = logging.getLogger("modora.service")

app = FastAPI(title=settings.service_name)

@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    rid = new_id("req_", 8)
    with request_scope(request_id=rid):
        logger.info(f"{request.method} {request.url.path} start")
        res = await call_next(request)
        logger.info(f"{request.method} {request.url.path} done status={res.status_code}")
        return res

@app.get("/health")
def health():
    return {"status": "ok"}

