import uuid
from decimal import Decimal
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.constants import PaymentStatus
from src.models.payment import Payment


class PaymentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        booking_id: uuid.UUID,
        user_id: uuid.UUID,
        amount: Decimal,
        currency: str = "VND",
        status: PaymentStatus = PaymentStatus.PENDING,
    ) -> Payment:
        payment = Payment(
            booking_id=booking_id,
            user_id=user_id,
            amount=amount,
            currency=currency,
            status=status,
        )
        self.session.add(payment)
        await self.session.flush()
        return payment

    async def get_by_id(self, payment_id: uuid.UUID, load_transactions: bool = False) -> Payment | None:
        stmt = select(Payment).where(Payment.id == payment_id)
        if load_transactions:
            stmt = stmt.options(selectinload(Payment.transactions))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_booking_id(self, booking_id: uuid.UUID, load_transactions: bool = False) -> Payment | None:
        stmt = select(Payment).where(Payment.booking_id == booking_id)
        if load_transactions:
            stmt = stmt.options(selectinload(Payment.transactions))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_status(self, payment_id: uuid.UUID, status: PaymentStatus) -> Payment | None:
        stmt = (
            update(Payment)
            .where(Payment.id == payment_id)
            .values(status=status)
            .returning(Payment)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
