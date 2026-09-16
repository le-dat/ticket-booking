# Booking Service (Dịch Vụ Đặt Vé & Giữ Chỗ)


Dịch vụ vi mô quản lý Đặt vé và Giữ chỗ phân tán thời gian thực thuộc hệ thống Bán vé Sự kiện trực tuyến (Ticket Booking Platform), xây dựng theo chuẩn **Go Clean Architecture**.

---

## 🏛️ Kiến Trúc & Tính Năng Trọng Tâm

- **Cổng dịch vụ:** HTTP REST API `3003` (Framework Fiber v2).
- **Redis Distributed Hold Engine:** Giữ ghế độc quyền với độ trễ thấp qua Distributed Lock (`SET lock:show:{show_id}:seat:{seat_id} {user_id} NX PX {ttl}`) và kịch bản atomic Lua giải phóng an toàn, loại trừ triệt để tình trạng bán vượt (overbooking/double-booking).
- **Tích Hợp gRPC Hai Chiều:** Giao tiếp trực tiếp với `event-service` (Port `50052`) qua hai hàm `ValidateAndLockSeats` và `ReleaseSeats`.
- **Transactional Outbox Pattern:** Đảm bảo tính toàn vẹn dữ liệu ACID tuyệt đối giữa DB `booking_db` (PostgreSQL) và Kafka Broker thông qua bảng `outbox_events` và goroutine Outbox Worker đẩy sự kiện sang topic `booking-events`.
- **Động Cơ Quét Hết Hạn (10m Expiry Engine):** Tự động phát hiện và hủy các đơn hàng `PENDING` quá hạn 10 phút bằng cơ chế truy vấn `FOR UPDATE SKIP LOCKED` an toàn cho mô hình chạy đa cụm/pods, đồng thời hoàn trả ghế về trạng thái `AVAILABLE`.
- **Kafka Payment Consumer:** Tự động bắt sự kiện `PaymentProcessed` từ topic `payment-events` (do `payment-service` phát hành) để chuyển đơn hàng sang trạng thái `CONFIRMED`.

---

## 🚀 Danh Sách API (REST v1)

| Phương thức | Đường dẫn | Mô tả |
|---|---|---|
| `POST` | `/v1/bookings` | Tạo đơn đặt vé, khóa ghế (Redis + gRPC) và lưu Outbox Event |
| `GET` | `/v1/bookings/:id` | Xem chi tiết đơn vé và danh sách ghế |
| `POST` | `/v1/bookings/:id/cancel` | Hủy đơn vé chờ thanh toán và nhả lại ghế |
| `GET` | `/healthz` | Kiểm tra trạng thái hoạt động của dịch vụ |
| `GET` | `/metrics` | Cung cấp Prometheus Metrics |

---

## 🛠️ Hướng Dẫn Khởi Chạy

```bash
# 1. Di chuyển vào thư mục service
cd services/booking-service

# 2. Cài đặt biến môi trường
cp .env.example .env

# 3. Chạy service và tự động áp dụng database migration
make run
```
