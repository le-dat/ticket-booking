from collections.abc import AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.services.payment_service import PaymentService


async def get_payment_service(
    db: AsyncSession = Depends(get_db),
) -> PaymentService:
    """Dependency provider injecting PaymentService with current DB session."""
    return PaymentService(db)
