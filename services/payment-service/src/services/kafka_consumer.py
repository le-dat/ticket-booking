import logging
import uuid
from decimal import Decimal
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import PaymentStatus
from src.repositories.payment_repository import PaymentRepository

logger = logging.getLogger("payment-service.kafka_consumer")


async def handle_booking_created_event(event_data: dict[str, Any], session: AsyncSession) -> None:
    """Consume 'BookingCreated' event and create a PENDING payment intent."""
    booking_id_raw = event_data.get("booking_id") or event_data.get("id")
    user_id_raw = event_data.get("user_id")
    amount_raw = event_data.get("total_amount") or event_data.get("amount") or "0"
    currency = event_data.get("currency", "VND")

    if not booking_id_raw or not user_id_raw:
        logger.warning("Invalid BookingCreated event payload: missing booking_id or user_id: %s", event_data)
        return

    try:
        booking_id = uuid.UUID(str(booking_id_raw))
        user_id = uuid.UUID(str(user_id_raw))
        amount = Decimal(str(amount_raw))
    except Exception as exc:
        logger.error("Error parsing BookingCreated event data (%s): %s", event_data, exc)
        return

    repo = PaymentRepository(session)
    existing = await repo.get_by_booking_id(booking_id)
    if existing:
        logger.info("Payment intent for booking %s already exists. Skipping.", booking_id)
        return

    payment = await repo.create(
        booking_id=booking_id,
        user_id=user_id,
        amount=amount,
        currency=currency,
        status=PaymentStatus.PENDING,
    )
    logger.info("✨ Created PENDING Payment intent %s for booking %s", payment.id, booking_id)


async def handle_booking_cancelled_event(event_data: dict[str, Any], session: AsyncSession) -> None:
    """Consume 'BookingCancelled' event and cancel payment intent if still PENDING."""
    booking_id_raw = event_data.get("booking_id") or event_data.get("id")
    if not booking_id_raw:
        return

    try:
        booking_id = uuid.UUID(str(booking_id_raw))
    except ValueError:
        return

    repo = PaymentRepository(session)
    payment = await repo.get_by_booking_id(booking_id)
    if payment and payment.status == PaymentStatus.PENDING:
        await repo.update_status(payment.id, PaymentStatus.CANCELLED)
        logger.info("🛑 Cancelled PENDING Payment %s for cancelled booking %s", payment.id, booking_id)
