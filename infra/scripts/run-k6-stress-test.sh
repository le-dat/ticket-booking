#!/usr/bin/env bash
# ==============================================================================
# Runner for k6 High-Concurrency Stress Test (Seat Lock Contention)
# Automatically falls back to Docker grafana/k6 if k6 is not installed on host
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JS_FILE="stress-test-seat-lock.js"

echo "========================================================="
echo "   🚀 CHẠY k6 BENCHMARK TRANH CHẤP GHẾ (1,000 VUs)      "
echo "========================================================="

TARGET_URL="${TARGET_URL:-http://localhost:3003/v1/bookings}"
SHOW_ID="${SHOW_ID:-d3b07384-d113-4ec6-a56f-958087920782}"
SEAT_ID="${SEAT_ID:-e7b07384-d113-4ec6-a56f-958087920799}"

echo "📡 Target URL: $TARGET_URL"
echo "🎭 Show ID:    $SHOW_ID"
echo "💺 Seat ID:    $SEAT_ID (VIP A01)"

if command -v k6 >/dev/null 2>&1; then
    echo "⚡ Chạy k6 trực tiếp từ host..."
    TARGET_URL="$TARGET_URL" SHOW_ID="$SHOW_ID" SEAT_ID="$SEAT_ID" \
        k6 run "${SCRIPT_DIR}/${JS_FILE}"
else
    echo "🐳 k6 chưa cài trên host -> Chạy k6 qua Docker 'grafana/k6'..."
    docker run --rm --network host \
        -e TARGET_URL="$TARGET_URL" \
        -e SHOW_ID="$SHOW_ID" \
        -e SEAT_ID="$SEAT_ID" \
        -v "${SCRIPT_DIR}:/scripts" \
        grafana/k6 run "/scripts/${JS_FILE}"
fi
