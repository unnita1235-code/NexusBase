"""
NexusBase — Request-ID Logging Middleware.

Generates a UUID4 request_id for every incoming request, stores it in a
ContextVar so all downstream loggers can access it, and attaches it
as an X-Request-ID response header for client-side correlation.
"""

from __future__ import annotations

import logging
import time
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# ── Context variable — accessible from any async/sync code in the request ──
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")

logger = logging.getLogger("rag.middleware")


class RequestIDFilter(logging.Filter):
    """Inject request_id into every log record automatically."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get("-")  # type: ignore[attr-defined]
        return True


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware that:
    1. Generates a UUID4 request_id per request
    2. Stores it in contextvars for downstream access
    3. Logs request start / end with method, path, status, duration
    4. Adds X-Request-ID header to every response
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        rid = uuid.uuid4().hex[:12]  # short but unique enough
        request_id_ctx.set(rid)

        start = time.perf_counter()
        method = request.method
        path = request.url.path

        logger.info(
            f"[{rid}] ▶ {method} {path}",
            extra={"request_id": rid},
        )

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                f"[{rid}] ✖ {method} {path} — unhandled exception after {duration_ms:.0f}ms",
                extra={"request_id": rid},
            )
            raise

        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            f"[{rid}] ◀ {method} {path} → {response.status_code} ({duration_ms:.0f}ms)",
            extra={"request_id": rid},
        )

        response.headers["X-Request-ID"] = rid
        return response
