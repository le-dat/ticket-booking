from datetime import datetime, timezone
from typing import Generic, TypeVar
from pydantic import BaseModel, Field

from src.middleware.correlation_id import get_correlation_id

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Standard envelope structure for successful responses."""

    success: bool = Field(default=True, description="Execution status")
    data: T | None = Field(default=None, description="Main response data payload")
    message: str = Field(default="Success", description="Response message")
    request_id: str = Field(
        default_factory=get_correlation_id,
        description="Distributed tracing identifier (Correlation ID)",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Response timestamp in UTC",
    )


class ErrorItem(BaseModel):
    """Detailed information for an individual error item."""

    field: str | None = Field(default=None, description="Field causing error if applicable")
    message: str = Field(..., description="Detailed error description")


class ErrorDetail(BaseModel):
    """Detailed error payload containing error code, message, and details."""

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: list[ErrorItem] | None = Field(default=None, description="Field-level error details if any")


class ApiErrorResponse(BaseModel):
    """Standard envelope structure for failed responses."""

    success: bool = Field(default=False, description="Execution status (always False for errors)")
    error: ErrorDetail = Field(..., description="Error information object")
    request_id: str = Field(
        default_factory=get_correlation_id,
        description="Distributed tracing identifier (Correlation ID)",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Response timestamp in UTC",
    )
