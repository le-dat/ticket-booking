#!/usr/bin/env bash
set -euo pipefail

BOOTSTRAP_SERVER="${KAFKA_BOOTSTRAP_SERVER:-localhost:9092}"
PARTITIONS=3
REPLICATION_FACTOR=1

echo "Chờ Kafka Broker sẵn sàng tại: $BOOTSTRAP_SERVER..."
MAX_RETRIES=30
RETRY_COUNT=0

until /opt/kafka/bin/kafka-broker-api-versions.sh --bootstrap-server "$BOOTSTRAP_SERVER" > /dev/null 2>&1; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ "$RETRY_COUNT" -ge "$MAX_RETRIES" ]; then
        echo "Lỗi: Kafka không phản hồi sau 60s."
        exit 1
    fi
    echo "Đang thử lại... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done

echo "Kafka đã sẵn sàng! Bắt đầu tạo các Saga Event Topics..."

TOPICS=(
    "booking-events"
    "payment-events"
    "notification-events"
)

for TOPIC_NAME in "${TOPICS[@]}"; do
    /opt/kafka/bin/kafka-topics.sh --bootstrap-server "$BOOTSTRAP_SERVER" \
        --create --if-not-exists \
        --topic "$TOPIC_NAME" \
        --partitions "$PARTITIONS" \
        --replication-factor "$REPLICATION_FACTOR" \
        --config retention.ms=604800000 \
        --config cleanup.policy=delete
    echo "--> [OK] Topic '$TOPIC_NAME' đã sẵn sàng."
done

echo "Danh sách Topics hiện tại:"
/opt/kafka/bin/kafka-topics.sh --bootstrap-server "$BOOTSTRAP_SERVER" --list
