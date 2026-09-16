# Kế Hoạch Triển Khai: Booking Service & Redis Hold Engine (Milestone 4)

> **Mục tiêu:** Xây dựng `services/booking-service` (Go Clean Architecture, Port 3003) - Trái tim xử lý giữ chỗ đồng thời cao (High Concurrency), Redis Distributed Lock, gRPC Client tích hợp `event-service`, Transactional Outbox Pattern, Saga Orchestration và Kafka Consumer cho `payment-events`.

---

## 🗺️ Phạm Vi & Phân Chia Nhiệm Vụ (Task Breakdown)

### Phase 1: Chuẩn Bị & Đồng Bộ Contract gRPC (Event Service)
- [x] Cập nhật proto `libs/contracts/src/proto/event.proto` & `services/event-service/docs/proto/v1/event.proto`:
  - Thêm `rpc ReleaseSeats (ReleaseSeatsRequest) returns (ReleaseSeatsResponse)`
  - Xác nhận trường thông tin `SeatInfo` (`seat_id`, `seat_number`, `row_name`, `price_in_cents`) trong `ValidateSeatsResponse`
- [x] Compile lại protobuf cho Go trong `services/event-service/docs/proto/v1`
- [x] Bổ sung logic `ReleaseSeats` & hoàn thiện `ValidateAndLockSeats` trả về chi tiết ghế và tổng tiền tại `services/event-service/internal/repo/persistent/event/event_postgres.go`
- [x] Expose endpoint `ReleaseSeats` trong `services/event-service/internal/controller/grpc/v1/event.go`

### Phase 2: Khởi Tạo Dự Án `services/booking-service` & Database Migration
- [x] Dọn dẹp mã nguồn thừa của template cũ trong `services/booking-service` (loại bỏ thư mục `.git` con và các artifacts cũ)
- [x] Cấu hình module `go.mod` và `config/config.go` (HTTP Port 3003, Postgres `booking_db`, Redis, Kafka, Event gRPC Host/Port)
- [x] Tạo file Migration SQL:
  - `migrations/20260916000001_create_booking_tables.up.sql` (`bookings`, `booking_items`, `outbox_events`, indexes)
  - `migrations/20260916000001_create_booking_tables.down.sql`
- [x] Cấu hình `.env.example` và `.env`

### Phase 3: Domain Entities & Repository Layer
- [x] Định nghĩa Entities (`internal/entity/`):
  - `booking.go` (`Booking`, status `PENDING`, `CONFIRMED`, `CANCELLED`, `EXPIRED`)
  - `item.go` (`BookingItem`)
  - `outbox.go` (`OutboxEvent`, status `PENDING`, `PUBLISHED`, `FAILED`)
- [x] Định nghĩa Repository Contracts (`internal/repo/contracts.go`)
- [x] Triển khai PostgreSQL Repository (`internal/repo/persistent/booking/booking_postgres.go`):
  - Transactional Create Booking (Ghi `bookings` + `booking_items` + `outbox_events` trong 1 DB Tx)
  - Query Booking By ID (kèm items)
  - Update Status (Confirm / Cancel)
  - Quét & cập nhật hàng loạt đơn quá hạn 10 phút (`SELECT ... FOR UPDATE SKIP LOCKED`)
  - Outbox Repository: Get Pending Events, Update Status, Increment Retry

### Phase 4: Redis Distributed Lock & gRPC Client
- [x] Triển khai Redis Lock Manager (`internal/repo/redis/seat_lock.go`):
  - Atomic acquire lock `SET lock:show:{show_id}:seat:{seat_id} {user_id} NX PX {ttl}`
  - Atomic release lock với Lua script (chỉ giải phóng nếu value trùng khớp hoặc force release)
  - Batch acquire & rollback nếu 1 trong các ghế bị xung đột
- [x] Triển khai gRPC Client (`internal/repo/grpc/event_client.go`):
  - Kết nối pool tới `event-service` (mặc định `localhost:50052`)
  - Gọi `ValidateAndLockSeats`
  - Gọi `ReleaseSeats`

### Phase 5: Core Usecase & REST API Handlers
- [x] Định nghĩa Usecase Contracts (`internal/usecase/contracts.go`)
- [x] Triển khai Core Usecase (`internal/usecase/booking/booking.go`):
  - `CreateBooking`: Acquire Redis locks -> Validate & Lock qua gRPC -> DB Tx tạo Booking + Items + Outbox Event -> Set TTL timer. Rollback Redis lock nếu gRPC/DB fail.
  - `GetBooking`: Trả về chi tiết đơn hàng
  - `CancelBooking`: Hủy đơn nếu còn PENDING -> Nhả ghế gRPC -> Nhả Redis lock -> Tạo Outbox `BookingCancelled`
  - `ConfirmBooking`: Nhận xác nhận từ thanh toán -> Cập nhật CONFIRMED -> Nhả Redis lock (ghế đã được chốt SOLD)
  - `ExpirePendingBookings`: Batch quét đơn quá hạn -> Đánh dấu EXPIRED -> Nhả ghế gRPC -> Nhả Redis lock -> Tạo Outbox `BookingCancelled`/`BookingExpired`
- [x] Triển khai REST API Handlers (`internal/controller/restapi/v1/booking.go`):
  - `POST /v1/bookings`
  - `GET /v1/bookings/:id`
  - `POST /v1/bookings/:id/cancel`
- [x] Đăng ký Route vào Fiber Router (`internal/controller/restapi/v1/router.go`)

### Phase 6: Background Workers (Outbox, Expiry Engine, Payment Consumer)
- [x] Outbox Worker (`internal/worker/outbox_worker.go`):
  - Polling định kỳ bảng `outbox_events`
  - Publish tin nhắn JSON lên Kafka topic `booking-events`
  - Đánh dấu `PUBLISHED`
- [x] Expiry Engine (`internal/worker/expiry_worker.go`):
  - Goroutine chạy nền mỗi 5-10 giây gọi `ExpirePendingBookings`
- [x] Payment Kafka Consumer (`internal/worker/payment_consumer.go`):
  - Lắng nghe Kafka topic `payment-events`
  - Khi nhận `PaymentProcessed` status = SUCCESS -> Gọi `ConfirmBooking`

### Phase 7: Wire-up Dependency Injection, Build & Kiểm Thử
- [x] Kết nối toàn bộ trong `internal/app/app.go`
- [x] Build kiểm tra cú pháp và unit/integration tests (`go build ./...` và `go test ./...` passed)
- [x] Tạo tài liệu README tiếng Anh và README_VN tiếng Việt
