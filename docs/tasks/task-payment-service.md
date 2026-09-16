# Kế Hoạch Triển Khai: Payment Service (Milestone 5)

> **Mục tiêu:** Xây dựng `services/payment-service` hoàn chỉnh theo chuẩn `auth-service`, kiến trúc 2 entrypoints độc lập (API + Consumer Worker), tích hợp Gateway Plugin Strategy Pattern (Mock Gateway), Async SQLAlchemy 2.0 và Redis Idempotency.

---

## 🗺️ Phạm Vi & Phân Chia Nhiệm Vụ (Task Breakdown)

### Phase 1: Môi Trường & Khởi Tạo Project (Tooling & Config)
- [x] Khởi tạo dự án bằng **uv** với `pyproject.toml` (Python 3.14).
- [x] Khai báo đầy đủ dependencies: `fastapi`, `uvicorn[standard]`, `sqlalchemy[asyncio]`, `asyncpg`, `pydantic`, `pydantic-settings`, `aiokafka`, `redis`, `alembic`.
- [x] Thiết lập file `.env.example`, `.python-version` và `alembic.ini`.
- [x] Cấu hình core:
  - `src/core/config.py`: Đọc cấu hình từ biến môi trường.
  - `src/core/logging.py`: Log định dạng kèm Correlation ID.
  - `src/core/constants.py`: Enums `PaymentStatus`, `TransactionStatus`, `KafkaTopics`.
  - `src/core/exceptions.py`: Custom Exception Handler theo chuẩn `ApiResponse`.

### Phase 2: Database Layer & Migrations
- [x] Cấu hình `src/core/database.py`: AsyncEngine connection pool, `async_sessionmaker`, `DeclarativeBase`, `get_db()`.
- [x] Cấu hình `alembic/env.py` hỗ trợ async migrations với SQLAlchemy 2.0.
- [x] Tạo migration `001_init_payments_and_transactions.py`:
  - Bảng `payments`: `id`, `booking_id`, `user_id`, `amount`, `currency`, `status`, `created_at`, `updated_at`.
  - Bảng `transactions`: `id`, `payment_id`, `gateway`, `gateway_transaction_id`, `idempotency_key`, `amount`, `status`, `gateway_response`, `created_at`.
- [x] Triển khai `src/models/payment.py` và `src/models/transaction.py`.
- [x] Triển khai `src/repositories/payment_repository.py` và `src/repositories/transaction_repository.py`.

### Phase 3: Gateway Plugin Layer (Strategy Pattern)
- [x] `src/gateways/base.py`: Định nghĩa abstract class `BasePaymentGateway` (`create_payment_url`, `verify_webhook`, `query_transaction`).
- [x] `src/gateways/dto.py`: `GatewayPaymentUrlResult`, `GatewayWebhookResult`, `GatewayQueryResult`.
- [x] `src/gateways/factory.py`: `PaymentGatewayFactory` resolve provider theo config hoặc request.
- [x] `src/gateways/mock/provider.py`: Plugin Mock Gateway sinh link checkout sandbox, active query và xác thực checksum HMAC-SHA512.

### Phase 4: Core Services & Kafka Integration
- [x] Cấu hình `src/core/redis.py`: Async Redis pool quản lý Distributed Lock & Idempotency.
- [x] Cấu hình `src/core/kafka.py`: Quản lý kết nối `AIOKafkaProducer` & `AIOKafkaConsumer`.
- [x] Triển khai `src/services/kafka_producer.py`: Bắn sự kiện `PaymentProcessed` và `PaymentExpired` (`payment-events`).
- [x] Triển khai `src/services/payment_service.py`: Điều phối nghiệp vụ tạo đơn thanh toán, xử lý Webhook idempotent, Active Reconciliation (Edge Case 1), và xử lý Booking Expired Refund (Edge Case 2).
- [x] Triển khai `src/services/kafka_consumer.py`: Xử lý message `BookingCreated` và `BookingCancelled` từ `booking-events`.

### Phase 5: FastAPI Web Application & Routers
- [x] `src/middleware/correlation_id.py`: Bắt và truyền `X-Correlation-ID`.
- [x] `src/schemas/response.py`: Chuẩn hóa `ApiResponse[T]` và `ApiErrorResponse`.
- [x] `src/routers/payments.py`: REST API `POST /api/v1/payments/intent`, `POST /api/v1/payments/checkout`, `GET /api/v1/payments/{booking_id}/status`.
- [x] `src/routers/webhook.py`: Webhook callback `POST /api/v1/payments/webhook`.
- [x] `src/routers/mock_gateway.py`: Endpoint sandbox giả lập giao diện quét mã / callback thanh toán local.
- [x] `src/routers/health.py`: Liveness & Readiness probe kiểm tra DB, Redis, Kafka.
- [x] `src/main.py`: Entrypoint Web API với `create_app()` factory và `lifespan`.

### Phase 6: Kafka Consumer Worker Daemon
- [x] `src/consumer.py`: Entrypoint CLI Worker chạy độc lập với vòng lặp `AIOKafkaConsumer`.

### Phase 7: Dockerfile, Docker Compose & Verification
- [x] Tạo `Dockerfile` hỗ trợ chạy cả 2 container: API và Consumer.
- [x] Viết tài liệu `README.md` bằng tiếng Việt theo convention dự án.
- [x] Kiểm thử tự động qua bộ test suite `pytest` (10/10 tests passed).
