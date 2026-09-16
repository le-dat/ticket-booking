import json
import logging
from decimal import Decimal
from src.core.config import settings
from src.core.kafka import get_kafka_producer

logger = logging.getLogger("payment-service.kafka_producer")


class KafkaProducerService:
    """Service to publish domain payment events to Kafka topics."""

    async def publish_payment_processed(
        self,
        booking_id: str,
        user_id: str,
        amount: Decimal | float,
        gateway_tx_id: str,
        status: str,
    ) -> None:
        producer = get_kafka_producer()
        payload = {
            "event_type": "PaymentProcessed",
            "booking_id": str(booking_id),
            "user_id": str(user_id),
            "amount": float(amount),
            "status": status,
            "gateway_transaction_id": gateway_tx_id,
        }
        raw_bytes = json.dumps(payload).encode("utf-8")

        if producer is not None:
            try:
                await producer.send_and_wait(
                    settings.KAFKA_TOPIC_PAYMENT_EVENTS,
                    value=raw_bytes,
                    key=str(booking_id).encode("utf-8"),
                )
                logger.info("📤 Published 'PaymentProcessed' event for booking %s to Kafka", booking_id)
            except Exception as exc:
                logger.error("❌ Failed to emit 'PaymentProcessed' event to Kafka: %s", exc)
        else:
            logger.info("💡 [Offline / Mock] Event 'PaymentProcessed' produced: %s", payload)

    async def publish_payment_expired(
        self,
        booking_id: str,
        user_id: str,
        amount: Decimal | float,
        gateway_tx_id: str,
        reason: str = "Booking reservation expired before payment completed",
    ) -> None:
        producer = get_kafka_producer()
        payload = {
            "event_type": "PaymentExpired",
            "booking_id": str(booking_id),
            "user_id": str(user_id),
            "amount": float(amount),
            "status": "PAYMENT_EXPIRED_REFUND_PENDING",
            "gateway_transaction_id": gateway_tx_id,
            "reason": reason,
        }
        raw_bytes = json.dumps(payload).encode("utf-8")

        if producer is not None:
            try:
                await producer.send_and_wait(
                    settings.KAFKA_TOPIC_PAYMENT_EVENTS,
                    value=raw_bytes,
                    key=str(booking_id).encode("utf-8"),
                )
                logger.info("📤 Published 'PaymentExpired' event for booking %s to Kafka", booking_id)
            except Exception as exc:
                logger.error("❌ Failed to emit 'PaymentExpired' event to Kafka: %s", exc)
        else:
            logger.info("💡 [Offline / Mock] Event 'PaymentExpired' produced: %s", payload)
