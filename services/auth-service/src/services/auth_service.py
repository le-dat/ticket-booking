# REASON: Service layer isolates business logic from HTTP routing and database queries
import uuid
from datetime import datetime, timedelta, timezone
from fastapi import status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.constants import DUMMY_BCRYPT_HASH, TOKEN_TYPE_BEARER, ErrorCode
from src.core.exceptions import AppException
from src.core.security import (
    blacklist_access_token,
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from src.models.user import Role, User
from src.repositories import RefreshTokenRepository, UserRepository
from src.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse


class AuthService:
    @staticmethod
    async def register(db: AsyncSession, dto: RegisterRequest) -> User:
        """Handles user registration logic."""
        # REASON: Checks if email already exists via UserRepository
        existing_user = await UserRepository.get_by_email(db, dto.email)

        if existing_user:
            raise AppException(
                status_code=status.HTTP_409_CONFLICT,
                code=ErrorCode.EMAIL_ALREADY_EXISTS,
                message="Email is already registered",
            )

        # REASON: Hashes password securely before creating the record
        hashed_pwd = hash_password(dto.password)

        # REASON: Public registrations default to CUSTOMER role to prevent privilege escalation
        new_user = User(
            email=dto.email,
            password_hash=hashed_pwd,
            full_name=dto.full_name,
            role=Role.CUSTOMER,
        )

        # REASON: Persists via UserRepository and catches IntegrityError to prevent concurrent race conditions
        try:
            return await UserRepository.create(db, new_user)
        except IntegrityError:
            await db.rollback()
            raise AppException(
                status_code=status.HTTP_409_CONFLICT,
                code=ErrorCode.EMAIL_ALREADY_EXISTS,
                message="Email is already registered",
            )

    @staticmethod
    async def authenticate(db: AsyncSession, dto: LoginRequest) -> TokenResponse:
        """Authenticates user credentials and issues both Access and Refresh Tokens."""
        # REASON: Retrieves user by email via UserRepository
        user = await UserRepository.get_by_email(db, dto.email)

        # REASON: Timing attack mitigation: performs dummy Bcrypt check if user is not found to equalize response times
        if not user:
            verify_password(dto.password, DUMMY_BCRYPT_HASH)
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code=ErrorCode.INVALID_CREDENTIALS,
                message="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not verify_password(dto.password, user.password_hash):
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code=ErrorCode.INVALID_CREDENTIALS,
                message="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # REASON: Embeds userId (sub), email, and role into JWT claims
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value,
        }
        access_token = create_access_token(data=payload)

        # REASON: Generates 64-hex cryptographically secure refresh token, storing only its SHA-256 hash in DB
        raw_refresh_token = generate_refresh_token()
        refresh_hash = hash_token(raw_refresh_token)
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_EXPIRES_IN_DAYS)
        await RefreshTokenRepository.create(db, user_id=user.id, token_hash=refresh_hash, expires_at=expires_at)

        return TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh_token,
            token_type=TOKEN_TYPE_BEARER,
            expires_in=settings.JWT_ACCESS_EXPIRES_IN_MINUTES * 60,
            user=UserResponse.model_validate(user),
        )

    @staticmethod
    async def refresh_token(db: AsyncSession, raw_refresh_token: str) -> TokenResponse:
        """Handles Token Rotation and issues a fresh token pair."""
        token_hash = hash_token(raw_refresh_token)
        record = await RefreshTokenRepository.get_by_token_hash(db, token_hash)

        if not record:
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code=ErrorCode.TOKEN_INVALID,
                message="Refresh token is missing or invalid",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # REASON: Token reuse / replay attack detection: revokes all user tokens if an already revoked token is reused
        if record.is_revoked:
            await RefreshTokenRepository.revoke_all_for_user(db, record.user_id)
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code=ErrorCode.TOKEN_REVOKED,
                message="Refresh token has been revoked or a security risk was detected",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if record.expires_at < datetime.now(timezone.utc):
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code=ErrorCode.TOKEN_EXPIRED,
                message="Refresh token has expired, please log in again",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # REASON: Token rotation: immediately revokes the consumed refresh token
        await RefreshTokenRepository.revoke(db, record)

        # Retrieve user profile
        user = await UserRepository.get_by_id(db, record.user_id)
        if not user:
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code=ErrorCode.USER_NOT_FOUND,
                message="User account no longer exists",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Issue fresh token pair
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value,
        }
        new_access_token = create_access_token(data=payload)
        new_raw_refresh_token = generate_refresh_token()
        new_refresh_hash = hash_token(new_raw_refresh_token)
        new_expires_at = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_EXPIRES_IN_DAYS)
        await RefreshTokenRepository.create(db, user_id=user.id, token_hash=new_refresh_hash, expires_at=new_expires_at)

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_raw_refresh_token,
            token_type=TOKEN_TYPE_BEARER,
            expires_in=settings.JWT_ACCESS_EXPIRES_IN_MINUTES * 60,
            user=UserResponse.model_validate(user),
        )

    @staticmethod
    async def logout(
        db: AsyncSession,
        raw_refresh_token: str | None = None,
        access_token: str | None = None,
    ) -> None:
        """Handles user logout by blacklisting the access token in Redis and revoking the refresh token in PostgreSQL."""
        # 1. Immediate revocation: Blacklist Access Token in Redis
        if access_token:
            await blacklist_access_token(access_token)

        # 2. Database revocation: Mark Refresh Token as revoked in DB
        if raw_refresh_token:
            token_hash = hash_token(raw_refresh_token)
            record = await RefreshTokenRepository.get_by_token_hash(db, token_hash)
            if record and not record.is_revoked:
                await RefreshTokenRepository.revoke(db, record)

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
        """Finds user by UUID primary key via UserRepository."""
        return await UserRepository.get_by_id(db, user_id)
