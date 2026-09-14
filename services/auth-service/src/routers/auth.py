# REASON: Presentation Layer handling HTTP requests and routing to Service layer
from typing import Any
from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.database import get_db
from src.core.rate_limiter import rate_limit
from src.dependencies import get_current_user, require_roles
from src.models.user import Role, User
from src.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from src.schemas.response import ApiResponse
from src.services.auth_service import AuthService

# REASON: Groups authentication-related routes under /auth prefix
router = APIRouter(prefix="/auth", tags=["Authentication & RBAC"])
optional_bearer = HTTPBearer(auto_error=False)


# REASON: Public user registration endpoint (POST /api/v1/auth/register)
@router.post(
    "/register",
    response_model=ApiResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register new user account",
    dependencies=[Depends(rate_limit(max_requests=settings.RATE_LIMIT_REGISTER_MAX, window_seconds=settings.RATE_LIMIT_REGISTER_WINDOW, key_prefix="register"))],
)
async def register(
    dto: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[UserResponse]:
    user = await AuthService.register(db, dto)
    return ApiResponse(
        data=UserResponse.model_validate(user),
        message="User registered successfully",
    )


# REASON: Login endpoint issuing access & refresh token pair (POST /api/v1/auth/login)
@router.post(
    "/login",
    response_model=ApiResponse[TokenResponse],
    status_code=status.HTTP_200_OK,
    summary="Login and obtain access & refresh token pair",
    dependencies=[Depends(rate_limit(max_requests=settings.RATE_LIMIT_LOGIN_MAX, window_seconds=settings.RATE_LIMIT_LOGIN_WINDOW, key_prefix="login"))],
)
async def login(
    dto: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[TokenResponse]:
    token_response = await AuthService.authenticate(db, dto)
    return ApiResponse(
        data=token_response,
        message="Login successful",
    )


# REASON: Token rotation endpoint issuing fresh token pair (POST /api/v1/auth/refresh)
@router.post(
    "/refresh",
    response_model=ApiResponse[TokenResponse],
    status_code=status.HTTP_200_OK,
    summary="Refresh access and refresh token pair (Token Rotation)",
    dependencies=[Depends(rate_limit(max_requests=settings.RATE_LIMIT_REFRESH_MAX, window_seconds=settings.RATE_LIMIT_REFRESH_WINDOW, key_prefix="refresh"))],
)
async def refresh(
    dto: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[TokenResponse]:
    token_response = await AuthService.refresh_token(db, dto.refresh_token)
    return ApiResponse(
        data=token_response,
        message="Token refreshed successfully",
    )


# REASON: Logout endpoint revoking access token in Redis and refresh token in PostgreSQL (POST /api/v1/auth/logout)
@router.post(
    "/logout",
    response_model=ApiResponse[dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Logout and immediately revoke access & refresh tokens",
)
async def logout(
    dto: LogoutRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_bearer),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    access_token = credentials.credentials if credentials else None
    await AuthService.logout(db, raw_refresh_token=dto.refresh_token, access_token=access_token)
    return ApiResponse(
        data={"logged_out": True},
        message="Logged out successfully",
    )


# REASON: Profile retrieval endpoint for authenticated user (GET /api/v1/auth/me)
@router.get(
    "/me",
    response_model=ApiResponse[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="Get current user profile (Requires Bearer JWT)",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> ApiResponse[UserResponse]:
    return ApiResponse(
        data=UserResponse.model_validate(current_user),
        message="User profile retrieved successfully",
    )


# REASON: RBAC demonstration endpoint restricted to ADMIN role (GET /api/v1/auth/admin-dashboard)
@router.get(
    "/admin-dashboard",
    response_model=ApiResponse[dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Admin dashboard (Requires ADMIN role)",
)
async def admin_dashboard(
    admin_user: User = Depends(require_roles(Role.ADMIN)),
) -> ApiResponse[dict[str, Any]]:
    return ApiResponse(
        data={
            "status": "ACCESS_GRANTED",
            "admin_email": admin_user.email,
        },
        message=f"Welcome Admin {admin_user.full_name} to the ticket management system",
    )
