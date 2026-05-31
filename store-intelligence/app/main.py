"""FastAPI entrypoint — see docs/context/05-api-contracts.md"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.anomalies import router as anomalies_router
from app.config import API_VERSION
from app.db import init_db
from app.funnel import router as funnel_router
from app.health import router as health_router
from app.heatmap import router as heatmap_router
from app.ingestion import router as ingestion_router
from app.logging_config import RequestLoggingMiddleware, configure_logging
from app.metrics import router as metrics_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()
    init_db()
    yield


app = FastAPI(title="Store Intelligence API", version=API_VERSION, lifespan=lifespan)
app.add_middleware(RequestLoggingMiddleware)

app.include_router(health_router)
app.include_router(ingestion_router)
app.include_router(metrics_router)
app.include_router(funnel_router)
app.include_router(heatmap_router)
app.include_router(anomalies_router)


@app.get("/")
def root():
    """Landing page — browsers hitting / get API links instead of 404."""
    return {
        "service": "Store Intelligence API",
        "version": API_VERSION,
        "docs": "/docs",
        "endpoints": {
            "health": "/health",
            "ingest": "POST /events/ingest",
            "metrics": "/stores/ST1008/metrics?date=2026-04-10",
            "funnel": "/stores/ST1008/funnel?date=2026-04-10",
            "heatmap": "/stores/ST1008/heatmap?date=2026-04-10",
            "anomalies": "/stores/ST1008/anomalies?date=2026-04-10",
        },
        "note": "Use ?date=2026-04-10 for sample/POS data. STORE_BLR_002 is an alias for ST1008.",
    }


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={"error": "validation_failed", "details": exc.errors()},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(_request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "detail": str(exc.__class__.__name__)},
    )
