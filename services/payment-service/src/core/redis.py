import logging
import redis.asyncio as aioredis
from redis.asyncio import Redis

from src.core.config import settings

logger = logging.getLogger("payment-service.redis")

_redis_client: Redis | None = None


async def init_redis() -> Redis:
    """Initializes the asynchronous Redis connection pool."""
    global _redis_client
    if _redis_client is None:
        logger.info("🔌 Connecting to Redis at %s...", settings.REDIS_URL.split("@")[-1])
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
            retry_on_timeout=True,
        )
        try:
            await _redis_client.ping()
            logger.info("✅ Redis connected successfully!")
        except Exception as exc:
            logger.warning("⚠️ Could not connect to Redis (%s). Lock will operate in fail-open mode.", exc)
    return _redis_client


async def close_redis() -> None:
    """Safely closes the Redis connection pool on application shutdown."""
    global _redis_client
    if _redis_client is not None:
        logger.info("🛑 Closing Redis connection pool...")
        await _redis_client.aclose()
        _redis_client = None
        logger.info("✅ Redis connection pool closed.")


def get_redis() -> Redis | None:
    """Returns the singleton Redis client instance."""
    return _redis_client
