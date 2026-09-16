import logging
import re
import uuid
from contextvars import ContextVar
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

SAFE_CORRELATION_ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]{1,128}$")

correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id_ctx", default="")


def get_correlation_id() -> str:
    """Retrieve current request correlation_id from ContextVar."""
    return correlation_id_ctx.get() or ""


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware to extract or generate X-Request-ID and attach it to response headers."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        raw_header = request.headers.get("x-request-id") or request.headers.get("x-correlation-id")

        if raw_header and SAFE_CORRELATION_ID_REGEX.match(raw_header.strip()):
            corr_id = raw_header.strip()
        else:
            corr_id = str(uuid.uuid4())

        token = correlation_id_ctx.set(corr_id)
        request.state.correlation_id = corr_id

        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = corr_id
            return response
        finally:
            correlation_id_ctx.reset(token)


class CorrelationIdLogFilter(logging.Filter):
    """Filter injecting correlation_id into each log record for tracking on Grafana/Loki."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id() or "-"
        return True
