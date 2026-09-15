# REASON: Centralized exception handling (Global Exception Handlers) following ApiErrorResponse schema
import logging
from typing import Any
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.core.constants import ErrorCode
from src.schemas.response import ApiErrorResponse, ErrorDetail, ErrorItem

logger = logging.getLogger("auth-service.exceptions")


def _get_code_value(code: Any) -> str:
    """Helper to extract raw string value from ErrorCode Enum or string."""
    if hasattr(code, "value"):
        return str(code.value)
    return str(code)


# REASON: Mapping table from HTTP status code to default machine-readable ErrorCode
STATUS_CODE_MAP: dict[int, ErrorCode] = {
    status.HTTP_400_BAD_REQUEST: ErrorCode.BAD_REQUEST,
    status.HTTP_401_UNAUTHORIZED: ErrorCode.UNAUTHORIZED,
    status.HTTP_403_FORBIDDEN: ErrorCode.FORBIDDEN,
    status.HTTP_404_NOT_FOUND: ErrorCode.NOT_FOUND,
    status.HTTP_409_CONFLICT: ErrorCode.CONFLICT,
    422: ErrorCode.VALIDATION_ERROR,
    status.HTTP_500_INTERNAL_SERVER_ERROR: ErrorCode.INTERNAL_SERVER_ERROR,
    status.HTTP_503_SERVICE_UNAVAILABLE: ErrorCode.SERVICE_UNAVAILABLE,
}


class AppException(Exception):
    """Custom business exception carrying explicit error codes."""
    def __init__(
        self,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        code: ErrorCode | str | None = None,
        message: str = "An error occurred while processing the request",
        details: list[ErrorItem] | None = None,
        headers: dict[str, str] | None = None,
    ):
        self.status_code = status_code
        if code:
            self.code = _get_code_value(code)
        else:
            default_map = STATUS_CODE_MAP.get(status_code, f"HTTP_{status_code}")
            self.code = _get_code_value(default_map)
        self.message = message
        self.details = details
        self.headers = headers
        super().__init__(self.message)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle custom business exceptions raised explicitly in code."""
    error_response = ApiErrorResponse(
        error=ErrorDetail(
            code=_get_code_value(exc.code),
            message=exc.message,
            details=exc.details,
        )
    )
    headers = dict(exc.headers or {})
    if hasattr(request.state, "rate_limit_headers"):
        headers.update(request.state.rate_limit_headers)

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(mode="json"),
        headers=headers if headers else None,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle standard FastAPI/Starlette HTTPException."""
    detail = exc.detail
    default_code = STATUS_CODE_MAP.get(exc.status_code, f"HTTP_{exc.status_code}")
    code = default_code
    message = str(detail)
    details = None

    # If detail is a dictionary containing structured error info
    if isinstance(detail, dict):
        code = detail.get("code", code)
        message = detail.get("message", message)
        if "details" in detail and isinstance(detail["details"], list):
            details = [ErrorItem(**d) if isinstance(d, dict) else ErrorItem(message=str(d)) for d in detail["details"]]

    error_response = ApiErrorResponse(
        error=ErrorDetail(
            code=_get_code_value(code),
            message=message,
            details=details,
        )
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(mode="json"),
        headers=getattr(exc, "headers", None),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Format Pydantic input validation errors (422) into friendly response structure."""
    details: list[ErrorItem] = []
    for err in exc.errors():
        # REASON: Strip body from loc path for cleaner field naming on client
        loc = [str(item) for item in err.get("loc", ()) if item != "body"]
        field_name = ".".join(loc) if loc else None
        msg = err.get("msg", "Invalid value")
        details.append(ErrorItem(field=field_name, message=msg))

    error_response = ApiErrorResponse(
        error=ErrorDetail(
            code=ErrorCode.VALIDATION_ERROR.value,
            message="Invalid request data",
            details=details,
        )
    )
    headers = None
    if hasattr(request.state, "rate_limit_headers"):
        headers = request.state.rate_limit_headers

    return JSONResponse(
        status_code=422,
        content=error_response.model_dump(mode="json"),
        headers=headers,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected 500 server crashes, hide internal stack traces, and log error."""
    logger.exception("❌ [CRITICAL] Unhandled Exception at %s: %s", request.url.path, exc)
    error_response = ApiErrorResponse(
        error=ErrorDetail(
            code=ErrorCode.INTERNAL_SERVER_ERROR.value,
            message="An internal server error occurred, please try again later",
        )
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(mode="json"),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all Global Exception Handlers to FastAPI application."""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
