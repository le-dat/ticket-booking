# Notification Service (Milestone 5)

> **Dịch vụ thông báo và phát vé điện tử E-Ticket theo thời gian thực (Realtime Notification & E-Ticket Gateway)**
> Xây dựng bằng **NestJS 11** (TypeScript), tích hợp **Socket.IO** (hỗ trợ scale ngang qua Redis Adapter), **Kafka Consumer** (`kafkajs`) và bộ sinh mã QR vé điện tử (`qrcode`).

---

## 🎯 Mục Tiêu & Chức Năng Chính

1. **Lắng nghe sự kiện thanh toán từ Kafka:**
   - Đăng ký topic `payment-events` với consumer group `notification-consumer-group`.
   - Bắt các sự kiện `PaymentProcessed` có trạng thái `SUCCESS`.
2. **Sinh mã QR vé điện tử E-Ticket:**
   - Tạo mã QR chuẩn bảo mật cao (Level `H`) dưới dạng **Base64 Data URL** (`image/png`).
   - Mã hóa thông tin vé: `bookingId`, `userId`, `txId`, và `timestamp`.
3. **Phát thông báo Realtime qua WebSocket (Socket.IO):**
   - Namespace: `/notifications` (cổng `3005`).
   - Tự động định tuyến thông báo vào room riêng của từng người dùng: `user:{userId}`.
   - Gửi sự kiện `BookingConfirmed` kèm mã QR Base64 ngay khi thanh toán hoàn tất.
4. **Cơ chế xác thực Gateway Trusted Header (`X-User-ID`):**
   - Tận dụng Kong API Gateway xác thực JWT tại biên.
   - Downstream `notification-service` chỉ đọc và tin tưởng header `X-User-ID` (kế thừa chuẩn từ `event-service` và `booking-service`).
   - Từ chối ngay lập tức mọi kết nối thiếu định danh người dùng (`missing user identification header`).
5. **Khả năng mở rộng ngang (Horizontal Scalability):**
   - Tích hợp `@socket.io/redis-adapter` kết nối Redis Pub/Sub của dự án, cho phép chạy nhiều replica pods mà không làm mất thông báo realtime giữa các client.

---

## 🏗️ Cấu Trúc Thư Mục

```text
services/notification-service/
├── .env.example                     # Mẫu biến môi trường
├── Dockerfile                       # Multi-stage Docker build
├── package.json
├── tsconfig.json
├── README.md                        # Tài liệu hướng dẫn này
└── src/
    ├── main.ts                      # Entrypoint NestJS (Port 3005, Redis Adapter, Prefix)
    ├── app.module.ts                # Root Module kết nối toàn bộ hệ thống
    ├── auth/
    │   └── guards/
    │       ├── trusted-header.guard.ts       # Guard kiểm tra X-User-ID cho HTTP
    │       └── trusted-header.guard.spec.ts
    ├── common/
    │   └── dto/
    │       └── api-response.dto.ts           # Chuẩn hóa ApiResponse[T]
    ├── config/
    │   ├── configuration.ts         # Configuration factory
    │   └── validation.schema.ts     # Joi schema kiểm tra biến môi trường
    ├── gateway/
    │   ├── events.gateway.ts        # WebSocket Gateway Socket.IO (/notifications)
    │   ├── events.gateway.spec.ts
    │   ├── events.module.ts
    │   └── redis-io.adapter.ts      # Redis Adapter cho Socket.IO
    ├── health/
    │   ├── health.controller.ts     # /health (Liveness) & /ready (Readiness)
    │   ├── health.controller.spec.ts
    │   └── health.module.ts
    ├── kafka/
    │   ├── dto/
    │   │   └── payment-processed-event.dto.ts
    │   ├── kafka-consumer.service.ts         # Consumer lắng nghe payment-events
    │   ├── kafka-consumer.service.spec.ts
    │   └── kafka.module.ts
    └── qrcode/
        ├── dto/
        │   └── ticket-qr-payload.dto.ts
        ├── qrcode.service.ts        # Sinh mã QR Base64 PNG
        ├── qrcode.service.spec.ts
        └── qrcode.module.ts
```

---

## ⚙️ Biến Môi Trường (`.env`)

| Biến Môi Trường | Giá Trị Mặc Định | Ý Nghĩa |
|---|---|---|
| `PORT` | `3005` | Cổng HTTP / WebSocket của service |
| `KAFKA_BROKERS` | `localhost:9092` | Danh sách Kafka broker (phân cách bằng dấu phẩy) |
| `KAFKA_CLIENT_ID` | `notification-service` | Client ID định danh kết nối Kafka |
| `KAFKA_GROUP_ID` | `notification-consumer-group` | Consumer Group ID |
| `KAFKA_TOPIC_PAYMENT_EVENTS`| `payment-events` | Topic lắng nghe sự kiện thanh toán |
| `REDIS_URL` | `redis://:redis_secret_123@localhost:6379/0` | URL kết nối Redis cho Socket.IO Adapter |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:8000` | Danh sách Origin được phép truy cập |

---

## 🚀 Hướng Dẫn Chạy Cục Bộ (Local Development)

### 1. Cài đặt dependencies:
```bash
pnpm install
```

### 2. Khởi chạy ở chế độ phát triển (Hot Reload):
```bash
pnpm run start:dev
```

### 3. Chạy kiểm thử tự động (Unit Tests):
```bash
pnpm run test
```

### 4. Build ứng dụng:
```bash
pnpm run build
```

---

## 🔌 Hướng Dẫn Kết Nối WebSocket Client

Client kết nối tới namespace `/notifications` qua Kong API Gateway (hoặc trực tiếp tới port `3005` khi test):

### Ví dụ Client Node.js / Browser (Socket.IO v4):
```javascript
import { io } from "socket.io-client";

// Khi đi qua Kong Gateway (Port 8000)
const socket = io("http://localhost:8000/notifications", {
  extraHeaders: {
    "X-User-ID": "usr-123456" // Do Kong Gateway inject sau khi verify JWT
  }
});

socket.on("connect", () => {
  console.log("✅ Đã kết nối WebSocket Gateway:", socket.id);
});

// Lắng nghe sự kiện xác nhận vé điện tử kèm mã QR
socket.on("BookingConfirmed", (data) => {
  console.log("🎟️ Nhận được vé điện tử:", data);
  console.log("Mã đơn:", data.bookingId);
  console.log("QR Code (Base64):", data.qrCode);
  // Hiển thị trực tiếp lên thẻ <img>: <img src={data.qrCode} />
});

socket.on("error", (err) => {
  console.error("❌ Lỗi kết nối:", err);
});
```

---

## 🩺 Endpoints Kiểm Tra Sức Khỏe (Health Check)

- **Liveness Probe:** `GET /api/v1/notifications/health`
  - Trả về mã HTTP `200` và `{ "status": "UP", "service": "notification-service" }`.
- **Readiness Probe:** `GET /api/v1/notifications/health/ready`
  - Kiểm tra trạng thái sẵn sàng của kết nối tới Redis và Kafka Consumer.
