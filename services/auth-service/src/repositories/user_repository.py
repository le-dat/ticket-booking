# REASON: Data Access Layer isolating all SQL queries for User entities
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.user import User


class UserRepository:
    """Repository responsible for executing User database queries in PostgreSQL."""

    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
        """Find a user by primary key UUID."""
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> User | None:
        """Find a user by unique email address."""
        query = select(User).where(User.email == email)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, user: User) -> User:
        """Persist a new user entity to the database and refresh the record."""
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
