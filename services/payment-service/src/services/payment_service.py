import logging
import uuid
from decimal import Decimal
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.constants import ErrorCode, PaymentStatus, TransactionStatus
from src.core.exceptions import AppException
from src.core.redis import get_redis
from src.gateways.base import BasePaymentGateway
from src.gateways.dto import GatewayPaymentUrlResult, GatewayWebhookResult
from src.gateways.factory import PaymentGatewayFactory
from src.models.payment import Payment
from src.repositories.payment_repository import PaymentRepository
from src.repositories.transaction_repository import TransactionRepository
from src.services.kafka_producer import KafkaProducerService

logger = logging.getLogger("payment-service.service")


class PaymentService:
    """Core domain business logic orchestrator for payment processing and reconciliation."""

    def __init__(
        self,
        db: AsyncSession,
        gateway: BasePaymentGateway | None = None,
        kafka_producer: KafkaProducerService | None = None,
    ):
        self.db = db
        self.gateway = gateway or PaymentGatewayFactory.get_gateway()
        self.payment_repo = PaymentRepository(db)
        self.transaction_repo = TransactionRepository(db)
        self.kafka_producer = kafka_producer or KafkaProducerService()

    async def create_or_get_intent(
        self,
        booking_id: uuid.UUID,
        user_id: uuid.UUID,
        amount: Decimal,
        currency: str = "VND",
    ) -> Payment:
        """Create or retrieve existing payment intent for a booking."""
        existing = await self.payment_repo.get_by_booking_id(booking_id)
        if existing:
            return existing

        payment = await self.payment_repo.create(
            booking_id=booking_id,
            user_id=user_id,
            amount=amount,
            currency=currency,
            status=PaymentStatus.PENDING,
        )
        await self.db.commit()
        await self.db.refresh(payment)
        return payment

    async def checkout(
        self,
        booking_id: uuid.UUID,
        user_id: uuid.UUID,
        amount: Decimal,
        order_info: str | None = None,
        return_url: str | None = None,
        gateway_name: str | None = None,
    ) -> GatewayPaymentUrlResult:
        """Initiate customer checkout session via selected payment gateway."""
        payment = await self.create_or_get_intent(
            booking_id=booking_id,
            user_id=user_id,
            amount=amount,
        )

        if payment.status == PaymentStatus.SUCCESS:
            raise AppException(
                status_code=400,
                code=ErrorCode.CONFLICT,
                message="This booking has already been paid successfully",
            )

        active_gateway = (
            PaymentGatewayFactory.get_gateway(gateway_name)
            if gateway_name
            else self.gateway
        )

        effective_return_url = return_url or settings.PAYMENT_RETURN_URL
        effective_order_info = order_info or f"Ticket booking payment for {booking_id}"

        gateway_res = await active_gateway.create_payment_url(
            booking_id=booking_id,
            amount=amount,
            order_info=effective_order_info,
            return_url=effective_return_url,
        )

        # Audit initiated transaction
        await self.transaction_repo.create(
            payment_id=payment.id,
            amount=amount,
            gateway=gateway_name or settings.DEFAULT_PAYMENT_GATEWAY,
            gateway_transaction_id=gateway_res.gateway_reference,
            idempotency_key=f"init:{booking_id}:{gateway_res.gateway_reference}",
            status=TransactionStatus.INITIATED,
            gateway_response=gateway_res.model_dump(),
        )
        await self.db.commit()

        return gateway_res

    async def process_verified_webhook(
        self,
        result: GatewayWebhookResult,
        gateway_name: str = "mock",
    ) -> dict[str, Any]:
        """Handle normalized webhook callback with idempotency locking and audit recording."""
        redis = get_redis()
        lock_key = f"lock:payment:webhook:{result.gateway_transaction_id}"

        # 1. Distributed Redis Lock for Idempotency
        if redis is not None:
            acquired = await redis.set(lock_key, "1", nx=True, ex=60)
            if not acquired:
                logger.warning("Duplicate webhook detected for tx_id=%s. Skipping.", result.gateway_transaction_id)
                return {"status": "skipped", "message": "Duplicate event ignored"}

        # 2. Lookup Payment record
        payment = await self.payment_repo.get_by_booking_id(result.booking_id)
        if not payment:
            raise AppException(
                status_code=404,
                code=ErrorCode.NOT_FOUND,
                message=f"Payment record for booking {result.booking_id} not found",
            )

        # 3. Already settled payment (Idempotent response)
        if payment.status == PaymentStatus.SUCCESS:
            logger.info("Payment %s already marked SUCCESS. Idempotent skip.", payment.id)
            return {"status": "ok", "message": "Payment already confirmed"}

        # 4. Edge Case 2: Expired / Cancelled booking received payment
        if payment.status == PaymentStatus.CANCELLED and result.status == PaymentStatus.SUCCESS:
            logger.warning(
                "⚠️ Payment %s was received after booking %s was CANCELLED. Triggering compensation refund.",
                payment.id,
                payment.booking_id,
            )
            await self.payment_repo.update_status(payment.id, PaymentStatus.PAYMENT_EXPIRED_REFUND_PENDING)
            await self.transaction_repo.create(
                payment_id=payment.id,
                amount=result.amount,
                gateway=gateway_name,
                gateway_transaction_id=result.gateway_transaction_id,
                idempotency_key=f"webhook:{result.gateway_transaction_id}",
                status=TransactionStatus.SUCCESS,
                gateway_response=result.raw_data,
            )
            await self.db.commit()

            # Emit compensation event to Kafka
            await self.kafka_producer.publish_payment_expired(
                booking_id=str(payment.booking_id),
                user_id=str(payment.user_id),
                amount=result.amount,
                gateway_tx_id=result.gateway_transaction_id,
                reason="Payment received after reservation cancelled/expired",
            )
            return {"status": "refund_pending", "message": "Booking expired, refund initiated"}

        # 5. Normal Path: Record transaction
        tx_status = TransactionStatus.SUCCESS if result.status == PaymentStatus.SUCCESS else TransactionStatus.FAILED
        await self.transaction_repo.create(
            payment_id=payment.id,
            amount=result.amount,
            gateway=gateway_name,
            gateway_transaction_id=result.gateway_transaction_id,
            idempotency_key=f"webhook:{result.gateway_transaction_id}",
            status=tx_status,
            gateway_response=result.raw_data,
        )

        # 6. Update payment status & publish event
        if result.status == PaymentStatus.SUCCESS:
            await self.payment_repo.update_status(payment.id, PaymentStatus.SUCCESS)
            await self.db.commit()

            await self.kafka_producer.publish_payment_processed(
                booking_id=str(payment.booking_id),
                user_id=str(payment.user_id),
                amount=result.amount,
                gateway_tx_id=result.gateway_transaction_id,
                status="SUCCESS",
            )
            logger.info("✅ Payment %s marked SUCCESS & published to Kafka", payment.id)
        else:
            await self.payment_repo.update_status(payment.id, PaymentStatus.FAILED)
            await self.db.commit()

            await self.kafka_producer.publish_payment_processed(
                booking_id=str(payment.booking_id),
                user_id=str(payment.user_id),
                amount=result.amount,
                gateway_tx_id=result.gateway_transaction_id,
                status="FAILED",
            )
            logger.info("❌ Payment %s marked FAILED & published to Kafka", payment.id)

        return {"status": "ok", "message": "Webhook processed successfully"}

    async def get_payment_status(
        self,
        booking_id: uuid.UUID,
        gateway_name: str | None = None,
    ) -> Payment:
        """Retrieve payment status with active reconciliation (Edge Case 1)."""
        payment = await self.payment_repo.get_by_booking_id(booking_id, load_transactions=True)
        if not payment:
            raise AppException(
                status_code=404,
                code=ErrorCode.NOT_FOUND,
                message=f"Payment for booking {booking_id} not found",
            )

        # Active reconciliation if still PENDING
        if payment.status == PaymentStatus.PENDING:
            active_gateway = (
                PaymentGatewayFactory.get_gateway(gateway_name)
                if gateway_name
                else self.gateway
            )
            query_res = await active_gateway.query_transaction(booking_id)

            if query_res.is_found and query_res.status == PaymentStatus.SUCCESS:
                logger.info("🔍 Active reconciliation resolved payment %s to SUCCESS", payment.id)
                await self.payment_repo.update_status(payment.id, PaymentStatus.SUCCESS)
                await self.transaction_repo.create(
                    payment_id=payment.id,
                    amount=query_res.amount or payment.amount,
                    gateway=gateway_name or settings.DEFAULT_PAYMENT_GATEWAY,
                    gateway_transaction_id=query_res.gateway_transaction_id,
                    idempotency_key=f"reconcile:{query_res.gateway_transaction_id}",
                    status=TransactionStatus.SUCCESS,
                    gateway_response=query_res.raw_data,
                )
                await self.db.commit()
                await self.db.refresh(payment)

                await self.kafka_producer.publish_payment_processed(
                    booking_id=str(payment.booking_id),
                    user_id=str(payment.user_id),
                    amount=payment.amount,
                    gateway_tx_id=query_res.gateway_transaction_id or "RECONCILED",
                    status="SUCCESS",
                )

        return payment
