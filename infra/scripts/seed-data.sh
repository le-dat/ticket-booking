#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQL_FILE="${SCRIPT_DIR}/seed-data.sql"

echo "========================================================="
echo "   🌱 SEEDING DỮ LIỆU MẪU CHO MILESTONE 6               "
echo "========================================================="

if [ ! -f "$SQL_FILE" ]; then
    echo "❌ Không tìm thấy file SQL: $SQL_FILE"
    exit 1
fi

# Detect execution method: Docker container or direct psql
if docker ps --format '{{.Names}}' | grep -q "^ticket-booking-postgres$"; then
    echo "📦 Nạp dữ liệu vào PostgreSQL qua Docker container 'ticket-booking-postgres'..."
    docker exec -i ticket-booking-postgres psql -U event_user -d event_db < "$SQL_FILE"
elif command -v psql >/dev/null 2>&1; then
    echo "💻 Nạp dữ liệu vào PostgreSQL cục bộ..."
    PGPASSWORD="${EVENT_DB_PASSWORD:-event_pass_secret_123}" psql \
        -h "${PGHOST:-localhost}" \
        -p "${PGPORT:-5432}" \
        -U "${EVENT_DB_USER:-event_user}" \
        -d "${EVENT_DB_NAME:-event_db}" \
        -f "$SQL_FILE"
else
    echo "❌ Lỗi: Không tìm thấy container 'ticket-booking-postgres' hoặc binary 'psql' trên hệ thống!"
    echo "Vui lòng khởi động hạ tầng bằng: docker compose -f infra/docker/docker-compose.infra.yml up -d"
    exit 1
fi

echo "✅ Đã nạp thành công 1 Venue, 1 Event, 1 Show và 50 Seats (Bao gồm VIP Seat A01)!"
echo "   - Show ID: d3b07384-d113-4ec6-a56f-958087920782"
echo "   - Seat ID: e7b07384-d113-4ec6-a56f-958087920799 (Seat A01 - AVAILABLE)"
echo "========================================================="
