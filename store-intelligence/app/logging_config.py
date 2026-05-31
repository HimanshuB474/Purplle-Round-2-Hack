"""Structured request logging — see docs/context/05-api-contracts.md Appendix C."""

from __future__ import annotations

import json
import logging
import time
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("store_intelligence.api")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        trace_id = str(uuid4())
        request.state.trace_id = trace_id
        started = time.perf_counter()
        response = await call_next(request)
        latency_ms = int((time.perf_counter() - started) * 1000)

        store_id = None
        parts = request.url.path.strip("/").split("/")
        if len(parts) >= 2 and parts[0] == "stores":
            store_id = parts[1]

        event_count = getattr(request.state, "ingest_event_count", None)

        logger.info(
            json.dumps(
                {
                    "trace_id": trace_id,
                    "store_id": store_id,
                    "endpoint": request.url.path,
                    "latency_ms": latency_ms,
                    "event_count": event_count,
                    "status_code": response.status_code,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
            )
        )
        return response


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
