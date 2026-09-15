# REASON: Dedicated health check router verifying service status and DB connectivity
import logging
from typing import Any
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.schemas.response import ApiErrorResponse, ApiResponse, ErrorDetail

logger = logging.getLogger("auth-service.health")

router = APIRouter(tags=["Health Check"])


@router.get(
    "/health",
    response_model=ApiResponse[dict[str, Any]],
    summary="Check service health and database connectivity",
)
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return ApiResponse(
            data={
                "status": "UP",
                "service": "auth-service",
                "database": "CONNECTED",
            },
            message="Service is healthy",
        )
    except Exception as exc:
        logger.error("Health check failed to connect to database: %s", exc)
        error_resp = ApiErrorResponse(
            error=ErrorDetail(
                code="SERVICE_UNAVAILABLE",
                message="Database connection failed",
            )
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=error_resp.model_dump(mode="json"),
        )
