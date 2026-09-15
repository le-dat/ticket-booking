# REASON: Re-export core infrastructure and configuration components of Auth Service
from src.core.config import settings
from src.core.constants import DUMMY_BCRYPT_HASH, TOKEN_TYPE_BEARER, ErrorCode
from src.core.database import Base, async_session_factory, engine, get_db
from src.core.exceptions import AppException, register_exception_handlers
from src.core.logging import setup_logging
from src.core.rate_limiter import rate_limit
from src.core.redis import close_redis, get_redis, init_redis
from src.core.security import (
    blacklist_access_token,
    create_access_token,
    decode_access_token,
    is_token_blacklisted,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)

__all__ = [
    "settings",
    "DUMMY_BCRYPT_HASH",
    "TOKEN_TYPE_BEARER",
    "ErrorCode",
    "Base",
    "async_session_factory",
    "engine",
    "get_db",
    "AppException",
    "register_exception_handlers",
    "setup_logging",
    "rate_limit",
    "init_redis",
    "close_redis",
    "get_redis",
    "blacklist_access_token",
    "create_access_token",
    "is_token_blacklisted",
    "decode_access_token",
    "generate_refresh_token",
    "hash_password",
    "hash_token",
    "verify_password",
]
