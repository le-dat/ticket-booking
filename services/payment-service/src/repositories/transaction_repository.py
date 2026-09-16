import uuid
from decimal import Decimal
from typing import Any
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import TransactionStatus
from src.models.transaction import Transaction


class TransactionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        payment_id: uuid.UUID,
        amount: Decimal,
        gateway: str = "mock",
        gateway_transaction_id: str | None = None,
        idempotency_key: str | None = None,
        status: TransactionStatus = TransactionStatus.INITIATED,
        gateway_response: dict[str, Any] | None = None,
    ) -> Transaction:
        tx = Transaction(
            payment_id=payment_id,
            amount=amount,
            gateway=gateway,
            gateway_transaction_id=gateway_transaction_id,
            idempotency_key=idempotency_key,
            status=status,
            gateway_response=gateway_response,
        )
        self.session.add(tx)
        await self.session.flush()
        return tx

    async def get_by_id(self, tx_id: uuid.UUID) -> Transaction | None:
        stmt = select(Transaction).where(Transaction.id == tx_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(self, idempotency_key: str) -> Transaction | None:
        stmt = select(Transaction).where(Transaction.idempotency_key == idempotency_key)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_gateway_tx_id(self, gateway_tx_id: str) -> Transaction | None:
        stmt = select(Transaction).where(Transaction.gateway_transaction_id == gateway_tx_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_payment_id(self, payment_id: uuid.UUID) -> list[Transaction]:
        stmt = (
            select(Transaction)
            .where(Transaction.payment_id == payment_id)
            .order_by(Transaction.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self,
        tx_id: uuid.UUID,
        status: TransactionStatus,
        gateway_response: dict[str, Any] | None = None,
    ) -> Transaction | None:
        values: dict[str, Any] = {"status": status}
        if gateway_response is not None:
            values["gateway_response"] = gateway_response

        stmt = (
            update(Transaction)
            .where(Transaction.id == tx_id)
            .values(**values)
            .returning(Transaction)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
