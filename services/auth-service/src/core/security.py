# REASON: Password hashing with Bcrypt and JWT token creation/verification using PyJWT
import hashlib
import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from src.core.config import settings
from src.core.redis import get_redis

logger = logging.getLogger("auth-service.security")


def generate_refresh_token() -> str:
    """Generate a cryptographically secure 64-character hex string as Refresh Token."""
    return secrets.token_hex(32)


def hash_token(token: str) -> str:
    """Hash token using SHA-256 for secure database storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    """Hash user password using Bcrypt with a random salt."""
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)  # REASON: 12 rounds ensures high brute-force resistance
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check if plaintext password matches the bcrypt hash."""
    plain_bytes = plain_password.encode("utf-8")
    hashed_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(plain_bytes, hashed_bytes)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Generate JWT Access Token containing user identity payload and unique jti."""
    to_encode = data.copy()

    # REASON: Calculate expiration in UTC
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.JWT_ACCESS_EXPIRES_IN_MINUTES)

    # REASON: Append exp, iat, and unique jti claims according to RFC 7519
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(UTC),
        "jti": str(uuid.uuid4()),
    })

    # REASON: Sign token with algorithm from settings
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode and verify validity of JWT token."""
    try:
        # REASON: PyJWT verifies signature and expiration time
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except jwt.PyJWTError:
        # REASON: Returns None if token expired, tampered with, or invalid format
        return None


async def blacklist_access_token(token: str) -> bool:
    """Blacklist an Access Token in Redis by its unique jti until natural expiration."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_exp": False},
        )
        jti = payload.get("jti")
        exp = payload.get("exp")
        if not jti or not exp:
            return False

        now_ts = datetime.now(UTC).timestamp()
        remaining_ttl = int(exp - now_ts)

        if remaining_ttl > 0:
            redis = get_redis()
            if redis:
                await redis.set(f"blacklist:jti:{jti}", "1", ex=remaining_ttl)
                logger.info("Access token jti %s blacklisted in Redis for %ss", jti, remaining_ttl)
                return True
        return False
    except Exception as exc:
        logger.warning("Could not blacklist access token in Redis: %s", exc)
        return False


async def is_token_blacklisted(jti: str) -> bool:
    """Check if an Access Token jti exists in the Redis blacklist."""
    try:
        redis = get_redis()
        if not redis:
            return False  # Fail-open if Redis is unavailable
        return bool(await redis.exists(f"blacklist:jti:{jti}"))
    except Exception as exc:
        logger.warning("Error checking token blacklist in Redis: %s", exc)
        return False
