set -euo pipefail

echo "========================================================="
echo "   BẮT ĐẦU CHẠY SMOKE TEST TOÀN DIỆN HẠ TẦNG            "
echo "========================================================="

PASS_COUNT=0
FAIL_COUNT=0

function assert_test() {
    local test_name="$1"
    local command="$2"

    echo -n "Kiểm tra: $test_name... "
    if eval "$command" > /dev/null 2>&1; then
        echo -e "\033[0;32m[PASS]\033[0m"
        PASS_COUNT=$((PASS_COUNT + 1))
    else
        echo -e "\033[0;31m[FAIL]\033[0m"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
}

echo "--- [1] Kiểm tra PostgreSQL & Phân Quyền Cô Lập ---"
assert_test "Postgres Superuser" "docker exec ecom-postgres psql -U postgres -d postgres -c
'SELECT 1;'"
assert_test "Auth DB (auth_user)" "docker exec ecom-postgres psql -U auth_user -d auth_db -c
'SELECT 1;'"
assert_test "Product DB (product_user)" "docker exec ecom-postgres psql -U product_user -d
product_db -c 'SELECT 1;'"
assert_test "Order DB (order_user)" "docker exec ecom-postgres psql -U order_user -d order_db
-c 'SELECT 1;'"
assert_test "Payment DB (payment_user)" "docker exec ecom-postgres psql -U payment_user -d
payment_db -c 'SELECT 1;'"

echo -n "Kiểm tra tính cô lập (auth_user không được truy cập payment_db)... "
if ! docker exec ecom-postgres psql -U auth_user -d payment_db -c 'SELECT 1;' > /dev/null
2>&1; then
    echo -e "\033[0;32m[PASS - Đã chặn thành công]\033[0m"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    echo -e "\033[0;31m[FAIL - Rò rỉ quyền]\033[0m"
    FAIL_COUNT=$((FAIL_COUNT + 1))
fi

echo "--- [2] Kiểm tra Redis ---"
assert_test "Redis PING" "docker exec ecom-redis redis-cli -a redis_secret_123 ping | grep -q
PONG"

echo "--- [3] Kiểm tra Kafka KRaft ---"
assert_test "Kafka Broker Ready" "docker exec ecom-kafka
/opt/kafka/bin/kafka-broker-api-versions.sh --bootstrap-server localhost:9092"
assert_test "Topic order-events" "docker exec ecom-kafka /opt/kafka/bin/kafka-topics.sh
--bootstrap-server localhost:9092 --list | grep -q order-events"
assert_test "Topic inventory-events" "docker exec ecom-kafka /opt/kafka/bin/kafka-topics.sh
--bootstrap-server localhost:9092 --list | grep -q inventory-events"
assert_test "Topic payment-events" "docker exec ecom-kafka /opt/kafka/bin/kafka-topics.sh
--bootstrap-server localhost:9092 --list | grep -q payment-events"
assert_test "Topic notification-events" "docker exec ecom-kafka
/opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list | grep -q
notification-events"

echo "--- [4] Kiểm tra Kong Gateway ---"
assert_test "Kong Admin API" "curl -s -f http://127.0.0.1:8001/status"
assert_test "Kong Proxy Route /api/v1/products" "curl -s -o /dev/null -w '%{http_code}'
http://127.0.0.1:8000/api/v1/products | grep -E '(200|404|502|503)'"

echo "========================================================="
echo "   KẾT QUẢ: $PASS_COUNT PASSED, $FAIL_COUNT FAILED       "
echo "========================================================="

if [ "$FAIL_COUNT" -gt 0 ]; then
    exit 1
fi