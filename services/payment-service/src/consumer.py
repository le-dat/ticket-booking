import asyncio
import json
import logging
import signal
from aiokafka import AIOKafkaConsumer
from src.core.config import settings
from src.core.database import async_session_factory, engine
from src.core.logging import setup_logging
from src.services.kafka_consumer import (
    handle_booking_cancelled_event,
    handle_booking_created_event,
)

logger = logging.getLogger("payment-consumer")
stop_event = asyncio.Event()


def signal_handler():
    logger.info("🛑 Received termination signal. Initiating graceful shutdown...")
    stop_event.set()


async def run_consumer():
    setup_logging()
    logger.info("🎧 Initializing Payment Kafka Consumer Worker...")
    logger.info("📡 Broker: %s | Topic: %s | Group: %s",
                settings.KAFKA_BOOTSTRAP_SERVERS,
                settings.KAFKA_TOPIC_BOOKING_EVENTS,
                settings.KAFKA_CONSUMER_GROUP_ID)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            pass

    consumer = AIOKafkaConsumer(
        settings.KAFKA_TOPIC_BOOKING_EVENTS,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id=settings.KAFKA_CONSUMER_GROUP_ID,
        enable_auto_commit=False,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )

    try:
        await consumer.start()
        logger.info("✅ Kafka Consumer Worker connected and listening for events!")
    except Exception as exc:
        logger.error("❌ Failed to start Kafka Consumer (%s). Retrying in 10 seconds...", exc)
        await asyncio.sleep(10)
        return

    try:
        while not stop_event.is_set():
            try:
                msg_batch = await consumer.getmany(timeout_ms=1000, max_records=20)
                for tp, messages in msg_batch.items():
                    for msg in messages:
                        payload = msg.value
                        event_type = payload.get("event_type") or payload.get("event")
                        logger.info("📥 [Partition %s, Offset %s] Event: %s", msg.partition, msg.offset, event_type)

                        async with async_session_factory() as session:
                            try:
                                if event_type in ("BookingCreated", "booking.created"):
                                    await handle_booking_created_event(payload, session)
                                elif event_type in ("BookingCancelled", "booking.cancelled"):
                                    await handle_booking_cancelled_event(payload, session)
                                else:
                                    logger.debug("Unhandled event type: %s", event_type)

                                await session.commit()
                                await consumer.commit()
                            except Exception as proc_err:
                                await session.rollback()
                                logger.error("❌ Error processing event %s: %s", event_type, proc_err, exc_info=True)
            except asyncio.CancelledError:
                break
            except Exception as loop_err:
                logger.error("Error in consumer poll loop: %s", loop_err)
                await asyncio.sleep(2)
    finally:
        logger.info("🛑 Stopping Kafka Consumer and disposing database engine...")
        await consumer.stop()
        await engine.dispose()
        logger.info("✅ Consumer Worker shutdown complete.")


if __name__ == "__main__":
    asyncio.run(run_consumer())
