import logging
from aiokafka import AIOKafkaProducer
from src.core.config import settings

logger = logging.getLogger("payment-service.kafka")

_kafka_producer: AIOKafkaProducer | None = None


async def init_kafka_producer() -> AIOKafkaProducer | None:
    """Initializes the singleton AIOKafkaProducer instance."""
    global _kafka_producer
    if _kafka_producer is None:
        try:
            logger.info("🔌 Connecting to Kafka broker at %s...", settings.KAFKA_BOOTSTRAP_SERVERS)
            _kafka_producer = AIOKafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            )
            await _kafka_producer.start()
            logger.info("✅ Kafka Producer started successfully!")
        except Exception as exc:
            logger.warning("⚠️ Could not connect to Kafka broker (%s). Running in offline mock mode.", exc)
            _kafka_producer = None
    return _kafka_producer


async def close_kafka_producer() -> None:
    """Safely stops the Kafka Producer on application teardown."""
    global _kafka_producer
    if _kafka_producer is not None:
        try:
            logger.info("🛑 Stopping Kafka Producer...")
            await _kafka_producer.stop()
            logger.info("✅ Kafka Producer stopped.")
        except Exception as exc:
            logger.warning("Error stopping Kafka Producer: %s", exc)
        finally:
            _kafka_producer = None


def get_kafka_producer() -> AIOKafkaProducer | None:
    """Returns the singleton Kafka Producer instance."""
    return _kafka_producer
