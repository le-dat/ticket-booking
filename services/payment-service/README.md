# 💳 Payment Service — Ticket Booking System

> Dịch vụ xử lý thanh toán, tích hợp cổng thanh toán (Payment Gateway Plugin), xác thực Webhook bảo mật (HMAC-SHA512) và điều phối đối soát giao dịch tài chính cho hệ thống Ticket Booking.

---

## 🚀 Tính Năng Chính

- **Kiến trúc phân tầng sạch sẽ (Clean Layered Architecture):** Tách biệt rõ ràng `Router` ➔ `Service` ➔ `Repository` ➔ `Model`, đồng bộ chuẩn hóa theo `auth-service`.
- **Dual Independent Entrypoints (2 Tiến Trình Riêng Biệt):**
  - `src/main.py`: FastAPI Web API Server (Port `3004`) phục vụ Client Checkout, Webhook, Health Check.
  - `src/consumer.py`: Standalone CLI Worker Daemon chạy vòng lặp `AIOKafkaConsumer` lắng nghe topic `booking-events` (`BookingCreated`, `BookingCancelled`).
- **Gateway Plugin Layer (Strategy Pattern):**
  - Tầng `src/gateways/` tách biệt độc lập giúp Core không phụ thuộc vào bất kỳ bên thứ 3 nào.
  - Hỗ trợ đổi cổng thanh toán linh hoạt (`DEFAULT_PAYMENT_GATEWAY=mock|vnpay|momo`) qua `PaymentGatewayFactory`.
  - Tích hợp sẵn **Mock Gateway Provider** có giao diện Sandbox UI quét mã QR và nút giả lập thanh toán local tức thì.
- **Bảo Mật & Idempotency:**
  - Xác thực chữ ký số webhook HMAC-SHA512.
  - Chống xử lý trùng lặp giao dịch (Duplicate Webhook) bằng **Redis Distributed Lock** (TTL 60s).
  - Bảng `transactions` lưu vết toàn bộ lịch sử (Audit Trail) của từng lần quẹt thẻ / gọi webhook.
- **Xử Lý Trường Hợp Biên (Edge Cases):**
  - **Edge Case 1 (Active Reconciliation):** API `GET /api/v1/payments/{booking_id}/status` chủ động query sang Gateway đối soát nếu trạng thái đơn vẫn `PENDING` khi client quay lại return URL.
  - **Edge Case 2 (Late Webhook / Expired Booking):** Nếu webhook báo `SUCCESS` sau khi đơn giữ chỗ đã bị hủy do quá hạn, dịch vụ chuyển trạng thái `PAYMENT_EXPIRED_REFUND_PENDING` và bắn sự kiện `PaymentExpired` sang Kafka để kích hoạt hoàn tiền bù trừ (Saga Compensation).

---

## 🛠️ Yêu Cầu Môi Trường & Cài Đặt

### Công nghệ sử dụng:
- **Python:** `>= 3.14`
- **Package Manager:** `uv`
- **Web Framework:** `FastAPI` + `Uvicorn`
- **Database:** `PostgreSQL` qua `asyncpg` + `SQLAlchemy 2.0 Async`
- **Migration:** `Alembic`
- **Cache & Lock:** `Redis` (redis-py async)
- **Message Broker:** `Apache Kafka` qua `aiokafka`

### Cài đặt dependencies:
```bash
cd services/payment-service

# Cài đặt toàn bộ môi trường ảo và thư viện bằng uv
uv sync
```

---

## ⚙️ Biến Môi Trường (`.env`)

Sao chép file `.env.example` thành `.env`:
```bash
cp .env.example .env
```

| Tên biến | Giá trị mẫu | Mô tả |
|---|---|---|
| `PORT` | `3004` | Cổng HTTP của Payment Web API |
| `DATABASE_URL` | `postgresql+asyncpg://payment_user:payment_pass_secret_123@localhost:5432/payment_db` | Kết nối PostgreSQL async |
| `REDIS_URL` | `redis://:redis_secret_123@localhost:6379/0` | Kết nối Redis |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Kafka broker |
| `KAFKA_TOPIC_BOOKING_EVENTS` | `booking-events` | Topic nhận đơn đặt chỗ mới |
| `KAFKA_TOPIC_PAYMENT_EVENTS` | `payment-events` | Topic phát trạng thái thanh toán |
| `DEFAULT_PAYMENT_GATEWAY` | `mock` | Cổng thanh toán mặc định (`mock`, `vnpay`, `momo`) |
| `WEBHOOK_SECRET` | `super_secret_webhook_key_payment_2026_very_long` | Khóa bí mật ký checksum HMAC-SHA512 |
| `PAYMENT_RETURN_URL` | `http://localhost:3000/booking/payment-result` | URL chuyển hướng frontend |

---

## 🗄️ Database Migrations (Alembic)

Chạy migration tạo bảng `payments` và `transactions`:
```bash
uv run alembic upgrade head
```

---

## 🚀 Hướng Dẫn Khởi Chạy

### 1. Khởi chạy FastAPI Web API (Port 3004)
```bash
uv run uvicorn src.main:app --host 0.0.0.0 --port 3004 --reload
```
- Swagger API Docs: [http://localhost:3004/docs](http://localhost:3004/docs)
- Health Check: [http://localhost:3004/health](http://localhost:3004/health)

### 2. Khởi chạy Kafka Consumer Worker (Tiến trình daemon)
```bash
uv run python -m src.consumer
```

### 3. Trải nghiệm Mock Gateway Sandbox UI
Truy cập giao diện thanh toán giả lập local:
```text
http://localhost:3004/api/v1/mock-gateway/checkout?booking_id=<BOOKING_UUID>&amount=150000&ref=TX-123456
```

---

## 📡 Danh Sách Endpoints Chính

| Method | Endpoint | Mô tả | Chuẩn Envelope |
|---|---|---|---|
| `POST` | `/api/v1/payments/intent` | Tạo hoặc lấy Payment Intent (`PENDING`) cho booking | `ApiResponse[PaymentResponseDTO]` |
| `POST` | `/api/v1/payments/checkout` | Tạo phiên checkout và nhận Payment URL / QR Code | `ApiResponse[PaymentCheckoutResponse]` |
| `GET` | `/api/v1/payments/{booking_id}/status` | Tra cứu trạng thái & kích hoạt Active Reconciliation | `ApiResponse[PaymentResponseDTO]` |
| `GET` | `/api/v1/payments/{booking_id}` | Lấy chi tiết đơn thanh toán và các giao dịch | `ApiResponse[PaymentResponseDTO]` |
| `POST` | `/api/v1/payments/webhook` | Webhook callback nhận kết quả từ Gateway | Gateway JSON (`{"status": "ok"}`) |
| `GET` | `/api/v1/mock-gateway/checkout` | Giao diện sandbox thanh toán / quét QR local | HTML Sandbox Page |
| `POST` | `/api/v1/mock-gateway/simulate-webhook` | Giả lập bắn webhook có ký HMAC-SHA512 hợp lệ | JSON Response |
| `GET` | `/health` | Liveness probe kiểm tra service | JSON |
| `GET` | `/health/ready` | Readiness probe kiểm tra DB, Redis, Kafka | JSON |
