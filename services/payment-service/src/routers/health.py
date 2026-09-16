from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.kafka import get_kafka_producer
from src.core.redis import get_redis

router = APIRouter(tags=["health"])


@router.get("/health", summary="Basic liveness probe")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "payment-service"}


@router.get("/health/ready", summary="Readiness probe checking DB, Redis, and Kafka")
async def readiness_check(db: AsyncSession = Depends(get_db)) -> JSONResponse:
    checks: dict[str, str] = {
        "database": "down",
        "redis": "down",
        "kafka": "down",
    }
    overall_status = True

    # 1. Database check
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception as exc:
        checks["database"] = f"unhealthy: {str(exc)}"
        overall_status = False

    # 2. Redis check
    try:
        redis = get_redis()
        if redis is not None and await redis.ping():
            checks["redis"] = "healthy"
        else:
            checks["redis"] = "disconnected"
    except Exception as exc:
        checks["redis"] = f"unhealthy: {str(exc)}"

    # 3. Kafka check
    producer = get_kafka_producer()
    checks["kafka"] = "healthy" if producer is not None else "offline/mock"

    status_code = status.HTTP_200_OK if overall_status else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if overall_status else "not_ready",
            "components": checks,
        },
    )
