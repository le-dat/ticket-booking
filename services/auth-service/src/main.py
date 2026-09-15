# REASON: Central application entrypoint using FastAPI Application Factory Pattern
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.core.database import engine
from src.core.exceptions import register_exception_handlers
from src.core.logging import setup_logging
from src.core.redis import close_redis, init_redis
from src.middleware.correlation_id import CorrelationIdMiddleware
from src.routers import auth_router, health_router

logger = logging.getLogger("auth-service")


# REASON: Uses modern lifespan asynccontextmanager instead of deprecated @app.on_event
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ready to receive connections
    logger.info("🚀 Auth Service started successfully on port %s", settings.PORT)
    logger.info("📖 Swagger Docs available at http://localhost:%s/docs", settings.PORT)
    await init_redis()
    yield
    # Teardown: Safely dispose database engine connections (Graceful Shutdown)
    logger.info("🛑 Disposing database engine connections...")
    await engine.dispose()
    await close_redis()
    logger.info("✅ Resources cleaned up successfully!")


def create_app() -> FastAPI:
    """Application Factory: Initializes and configures the FastAPI application."""
    # 1. Configure logging with correlation ID formatting
    setup_logging()

    # 2. Initialize FastAPI application
    app = FastAPI(
        title="Ticket Booking - Auth Service",
        description="Authentication & Role-Based Access Control (RBAC) Service for Ticket Booking System",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # 3. Register middlewares
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(CorrelationIdMiddleware)

    # 4. Register global exception handlers
    register_exception_handlers(app)

    # 5. Register API routers
    app.include_router(health_router)
    app.include_router(auth_router, prefix="/api/v1")

    return app


# REASON: Exposes the default app instance for ASGI servers (Uvicorn, Gunicorn)
app = create_app()

if __name__ == "__main__":
    import uvicorn
    # REASON: Allows running directly with python -m src.main if needed
    uvicorn.run("src.main:app", host="0.0.0.0", port=settings.PORT, reload=True)
