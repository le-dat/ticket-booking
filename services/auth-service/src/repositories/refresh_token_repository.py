# REASON: Data Access Layer managing database operations for the refresh_tokens table
import uuid
from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    """Repository handling operations on the refresh_tokens table in PostgreSQL."""

    @staticmethod
    async def create(
        db: AsyncSession,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> RefreshToken:
        """Persist a new refresh token hash record to the database."""
        record = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            is_revoked=False,
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def get_by_token_hash(db: AsyncSession, token_hash: str) -> RefreshToken | None:
        """Find a RefreshToken record by its token hash."""
        query = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def revoke(db: AsyncSession, record: RefreshToken) -> None:
        """Revoke a RefreshToken record (set is_revoked = True)."""
        record.is_revoked = True
        await db.commit()

    @staticmethod
    async def revoke_all_for_user(db: AsyncSession, user_id: uuid.UUID) -> None:
        """Revoke all RefreshToken records for a user (global logout across all devices)."""
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.is_revoked == False)
            .values(is_revoked=True)
        )
        await db.execute(stmt)
        await db.commit()
