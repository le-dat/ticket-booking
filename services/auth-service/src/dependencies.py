# REASON: Leverages FastAPI Dependency Injection for endpoint protection and RBAC verification
import uuid
from typing import Callable
from fastapi import Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from src.core import AppException, ErrorCode, decode_access_token, get_db, is_token_blacklisted
from src.models.user import Role, User
from src.services.auth_service import AuthService

# REASON: HTTPBearer automatically renders the Authorize lock button in Swagger UI (/docs)
security_scheme = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Decodes Bearer token from Authorization header and fetches the current user from DB."""
    token = credentials.credentials
    payload = decode_access_token(token)

    # REASON: Returns 401 Unauthorized if token fails validation or lacks sub claim
    if not payload or "sub" not in payload:
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code=ErrorCode.TOKEN_INVALID,
            message="Authentication token is missing or invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # REASON: Checks if token has been explicitly revoked / blacklisted in Redis
    jti = payload.get("jti")
    if jti and await is_token_blacklisted(jti):
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code=ErrorCode.TOKEN_REVOKED,
            message="Token has been revoked, please log in again",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = uuid.UUID(payload["sub"])
    except ValueError:
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code=ErrorCode.TOKEN_INVALID,
            message="Invalid subject format in authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # REASON: Verifies that the user account still exists in the database
    user = await AuthService.get_user_by_id(db, user_id)
    if not user:
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code=ErrorCode.USER_NOT_FOUND,
            message="User account not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_roles(*allowed_roles: Role) -> Callable:
    """Dependency factory for Role-Based Access Control (RBAC) verification."""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        # REASON: Raises 403 Forbidden if user role is not in the allowed roles list
        if current_user.role not in allowed_roles:
            raise AppException(
                status_code=status.HTTP_403_FORBIDDEN,
                code=ErrorCode.FORBIDDEN,
                message="You do not have permission to perform this action",
            )
        return current_user

    return role_checker
