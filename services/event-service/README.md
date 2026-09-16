# Event Service


Microservice quản lý sự kiện hiệu suất cao cho Nền tảng Đặt vé (Ticket Booking Platform), được xây dựng theo mô hình **Clean Architecture** bằng Golang.

---

## 🏗️ Tech Stack & Thư viện

- **Ngôn ngữ:** Go 1.22+
- **Web Framework:** [Fiber](https://github.com/gofiber/fiber) (REST API)
- **Giao thức RPC:** gRPC, AMQP RPC (RabbitMQ), NATS RPC (NATS)
- **Database:** PostgreSQL kết hợp [Squirrel](https://github.com/Masterminds/squirrel) query builder & `golang-migrate`
- **Giám sát & Đo lường:** OpenTelemetry (Distributed Tracing), Prometheus (Metrics), ZeroLog (Structured Logging)
- **Kiểm thử & Mocking:** Testify & Go Mock

---

## 🏛️ Nghiệp vụ & Tính năng (Domain)

Event Service quản lý danh mục sự kiện, địa điểm tổ chức, suất diễn và sơ đồ ghế ngồi cho hệ thống đặt vé:

- **Venues:** Quản lý địa điểm tổ chức (sân vận động, nhà hát, hội trường).
- **Events:** Quản lý thông tin sự kiện, hình ảnh banner và trạng thái (`DRAFT`, `PUBLISHED`, `CANCELLED`).
- **Shows:** Quản lý lịch suất diễn của sự kiện.
- **Seats:** Quản lý sơ đồ ghế ngồi và trạng thái chỗ ngồi trong suất diễn.

### Các API Endpoints (REST v1)

| Thao tác | Method & Path | Mô tả |
| :--- | :--- | :--- |
| Danh sách sự kiện | `GET /v1/events` | Lấy danh sách các sự kiện đã xuất bản |
| Chi tiết sự kiện | `GET /v1/events/:id` | Xem chi tiết sự kiện và các suất diễn |
| Sơ đồ ghế suất diễn | `GET /v1/shows/:id/seats` | Lấy sơ đồ ghế và trạng thái trống/đã đặt |
| Tạo địa điểm | `POST /v1/venues` | Thêm địa điểm tổ chức mới (Admin) |
| Tạo sự kiện | `POST /v1/events` | Tạo mới sự kiện (Admin) |
| Tạo suất diễn | `POST /v1/events/:id/shows` | Lên lịch suất diễn cho sự kiện (Admin) |

---

## 🚀 Bắt đầu nhanh (Quick Start)

### 1. Khởi động Infrastructure (Từ thư mục gốc Monorepo)

Từ thư mục gốc của monorepo, khởi động hạ tầng chung (PostgreSQL, Kafka, Redis, Kong, RabbitMQ, NATS):

```sh
# Thư mục gốc
pnpm install
pnpm infra:up
```

Kiểm tra trạng thái hạ tầng:
```sh
pnpm infra:test
```

### 2. Chạy Event Service tại Local

```sh
cd services/event-service
# Chạy ứng dụng kèm tự động chạy database migration
make run
```

---

## 📊 Khả năng quan sát (Observability)

Hệ thống Distributed tracing được tích hợp bằng **OpenTelemetry** xuất dữ liệu qua OTLP tới Jaeger. Các metrics được expose tại `/metrics` để Prometheus thu thập. Logging chuẩn hóa thông qua **ZeroLog**.

Cấu hình (.env):
- `TRACING_ENABLED=true`
- `TRACING_OTLP_ENDPOINT=localhost:4317`
- `PG_URL=postgres://user:password@localhost:5432/event_db`
