import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.core.database import engine
from src.core.exceptions import register_exception_handlers
from src.core.kafka import close_kafka_producer, init_kafka_producer
from src.core.logging import setup_logging
from src.core.redis import close_redis, init_redis
from src.middleware.correlation_id import CorrelationIdMiddleware
from src.routers import (
    health_router,
    mock_gateway_router,
    payments_router,
    webhook_router,
)

logger = logging.getLogger("payment-service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup lifecycle
    logger.info("🚀 Payment Service starting on port %s...", settings.PORT)
    logger.info("📖 Swagger Docs available at http://localhost:%s/docs", settings.PORT)
    await init_redis()
    await init_kafka_producer()
    yield
    # Teardown lifecycle (Graceful Shutdown)
    logger.info("🛑 Cleaning up resources and connections...")
    await close_kafka_producer()
    await close_redis()
    await engine.dispose()
    logger.info("✅ All connections closed safely.")


def create_app() -> FastAPI:
    """Application Factory initializing FastAPI application with routers and middlewares."""
    setup_logging()

    app = FastAPI(
        title="Ticket Booking - Payment Service",
        description="Payment processing, Webhook reconciliation, and Idempotency service",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Middlewares
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(CorrelationIdMiddleware)

    # Global Exception Handlers
    register_exception_handlers(app)

    # Register Routers
    app.include_router(health_router)
    app.include_router(payments_router)
    app.include_router(webhook_router)
    app.include_router(mock_gateway_router)

    return app


app = create_app()
