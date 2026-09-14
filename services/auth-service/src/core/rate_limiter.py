# REASON: Production-grade distributed sliding window rate limiter using Redis Lua scripts
import logging
import math
import time
import uuid
from typing import Callable
from fastapi import Request, Response, status
from redis.exceptions import RedisError

from src.core.constants import ErrorCode
from src.core.exceptions import AppException
from src.core.redis import get_redis

logger = logging.getLogger("auth-service.rate_limiter")

# Lua script ensures 100% atomic execution of sliding-window counter in Redis
SLIDING_WINDOW_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local unique_id = ARGV[4]
local clearBefore = now - window

redis.call("ZREMRANGEBYSCORE", key, "-inf", clearBefore)
local currentRequests = redis.call("ZCARD", key)

if currentRequests < limit then
    redis.call("ZADD", key, now, unique_id)
    redis.call("EXPIRE", key, window + 2)
    return {1, limit - currentRequests - 1, 0}
else
    local oldest = redis.call("ZRANGE", key, 0, 0, "WITHSCORES")
    local retry_after = 1
    if #oldest > 1 then
        local oldest_time = tonumber(oldest[2])
        retry_after = math.ceil(window - (now - oldest_time))
        if retry_after <= 0 then retry_after = 1 end
    end
    return {0, 0, retry_after}
end
"""


def get_client_ip(request: Request) -> str:
    """Extracts the client IP from proxy headers (e.g. Kong) or direct client connection."""
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(
    max_requests: int,
    window_seconds: int = 60,
    key_prefix: str = "auth",
) -> Callable:
    """Factory creating a FastAPI Dependency for sliding-window rate limiting."""

    async def dependency(request: Request, response: Response) -> None:
        redis = get_redis()
        if not redis:
            logger.debug("Redis client unavailable; skipping rate limit check (fail-open)")
            return

        client_ip = get_client_ip(request)
        redis_key = f"rate_limit:{key_prefix}:{client_ip}"
        now = time.time()
        unique_id = f"{now}-{uuid.uuid4().hex[:8]}"

        try:
            allowed, remaining, retry_after = await redis.eval(
                SLIDING_WINDOW_LUA,
                1,
                redis_key,
                str(now),
                str(window_seconds),
                str(max_requests),
                unique_id,
            )

            # Store rate limit headers on request state and response
            rate_headers = {
                "X-RateLimit-Limit": str(max_requests),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(window_seconds),
            }
            request.state.rate_limit_headers = rate_headers
            response.headers.update(rate_headers)

            if not allowed:
                logger.warning(
                    "Rate limit exceeded for IP %s on prefix %s (limit: %s/%ss, retry_after: %ss)",
                    client_ip,
                    key_prefix,
                    max_requests,
                    window_seconds,
                    retry_after,
                )
                headers = {
                    "Retry-After": str(retry_after),
                    **rate_headers,
                }
                raise AppException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    code=ErrorCode.RATE_LIMIT_EXCEEDED,
                    message=f"Too many requests. Please try again in {retry_after} seconds.",
                    headers=headers,
                )

        except AppException:
            raise
        except RedisError as exc:
            # REASON: Fail-open strategy prevents taking down authentication if Redis has a transient issue
            logger.warning("Redis error during rate limiting check: %s. Failing open.", exc)
            return

    return dependency
