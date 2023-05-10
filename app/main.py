import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from app.api.routes import router
from app.config import settings
from app.observability import setup_logging

setup_logging(settings.log_level)
logger = logging.getLogger("copilot.access")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("service starting", extra={"version": settings.version})
    yield
    logger.info("service stopping")


app = FastAPI(title="AI Customer Support Copilot", version=settings.version, lifespan=lifespan)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-Id") or f"req-{uuid.uuid4().hex[:12]}"
    request.state.request_id = request_id
    start = time.time()
    response = await call_next(request)
    response.headers["X-Request-Id"] = request_id
    latency_ms = int((time.time() - start) * 1000)
    logger.info(
        "request completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "latency_ms": latency_ms,
        },
    )
    return response


app.include_router(router, prefix="/api/v1")


@app.get("/")
def root():
    return {"service": settings.app_name, "version": settings.version}
