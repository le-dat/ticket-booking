# Kế Hoạch & Tiến Độ Triển Khai: Milestone 6 - High-Concurrency Benchmark & End-to-End Smoke Test

> **Mục tiêu:** Xây dựng và tự động hóa toàn bộ quy trình kiểm thử tải tranh chấp ghế (1,000 VUs) với Redis Distributed Lock và kiểm thử E2E Smoke Test khép kín từ Auth -> Booking -> Payment -> Kafka -> Notification E-Ticket QR Code.

---

## 📋 Danh Sách Nhiệm Vụ (Task Checklist)

### Phase 1: Chuẩn Hóa Hạ Tầng & Định Tuyến (Infrastructure & Gateway Alignment)
- [x] Sửa lỗi lệch path prefix giữa Kong Gateway (`/api/v1`) và Go Services (`/v1`):
  - Bổ sung hỗ trợ prefix kép (`/v1` và `/api/v1`) trong `services/booking-service/internal/controller/restapi/router.go`.
  - Bổ sung hỗ trợ prefix kép (`/v1` và `/api/v1`) trong `services/event-service/internal/controller/restapi/router.go`.
- [x] Tối ưu hóa cấu hình Kong Gateway (`infra/kong/kong.yml`):
  - Nâng giới hạn Rate Limit của `booking-routes` từ `minute: 120` lên `minute: 10000` phục vụ stress test.
  - Bổ sung đường dẫn `/socket.io` cho `notification-routes` để hỗ trợ bắt tay WebSocket Socket.IO qua Kong port 8000.

---

### Phase 2: Kịch Bản Seed Dữ Liệu Mẫu (Idempotent Data Seeding)
- [x] Xây dựng script SQL `infra/scripts/seed-data.sql`:
  - Tạo 1 Venue: `National Convention Center` (`c1b07384-d113-4ec6-a56f-958087920701`).
  - Tạo 1 Event: `High-Concurrency Tech Concert 2026` (`c2b07384-d113-4ec6-a56f-958087920702`).
  - Tạo 1 Show: `d3b07384-d113-4ec6-a56f-958087920782`.
  - Tạo 50 Ghế: Ghế VIP `A01` (`e7b07384-d113-4ec6-a56f-958087920799`) và 49 ghế phụ trợ (A02..A10, B01..B10, C01..C10, D01..D10, E01..E10).
  - Đảm bảo tính idempotent: có thể chạy nhiều lần để reset ghế về trạng thái `AVAILABLE`.
- [x] Xây dựng bash runner `infra/scripts/seed-data.sh` tự động nạp SQL vào Docker container `ticket-booking-postgres`.

---

### Phase 3: k6 High-Concurrency Stress Test Script (Redis Lock Contention)
- [x] Xây dựng `infra/scripts/stress-test-seat-lock.js`:
  - Mô phỏng 1,000 VUs đồng thời gửi request giữ cùng một ghế VIP `A01`.
  - Mô phỏng đúng từng Virtual User với định danh `X-User-ID` độc lập để tạo tranh chấp thực tế.
  - Đo lường metrics: `successful_bookings`, `seat_conflicts` (409), và `other_errors`.
  - Thiết lập thresholds: p95 duration < 300ms, tỷ lệ lỗi lạ < 5%.
  - Hỗ trợ tùy biến `TARGET_URL` (direct port 3003 hoặc qua Kong port 8000).

---

### Phase 4: Automated End-to-End Smoke Test Script (E2E Lifecycle)
- [x] Xây dựng `infra/scripts/smoke-test-e2e.sh`:
  - Bước 0: Kiểm tra liveness của 5 microservices (`auth`, `event`, `booking`, `payment`, `notification`).
  - Bước 1: Nạp dữ liệu seed chuẩn bị trước test.
  - Bước 2: Đăng ký tài khoản người dùng test mới (Pydantic `full_name`).
  - Bước 3: Đăng nhập lấy Bearer Token JWT và User ID (`data.access_token`).
  - Bước 4: Tạo booking giữ chỗ ghế VIP `A01` (10 phút) trên `booking-service`.
  - Bước 5: Kiểm chứng trạng thái ghế trên `event-service` đã chuyển sang `HELD`.
  - Bước 6: Khởi tạo thanh toán `checkout` trên `payment-service`.
  - Bước 7: Giả lập webhook đối tác thanh toán thành công kèm chữ ký chuẩn HMAC-SHA512 (`WEBHOOK_SECRET`).
  - Bước 8: Kiểm chứng sự kiện Kafka `PaymentProcessed` được `booking-service` tiêu thụ và cập nhật đơn vé thành `CONFIRMED`.
  - Bước 9: Kiểm chứng `notification-service` sinh mã QR vé điện tử E-Ticket và broadcast WebSocket.

---

### Phase 5: Cập Nhật Tài Liệu Kỹ Thuật
- [x] Cập nhật toàn diện `docs/milestone-6-benchmark-smoke-test.md` với sơ đồ luồng dữ liệu, checklist, hướng dẫn chạy chi tiết và tiêu chí nghiệm thu.

---

## 🎯 Tiêu Chí Hoàn Thành (Definition of Done)
1. Cả 5 microservices build và test thành công.
2. Script seed dữ liệu `seed-data.sh` chạy thông suốt và nạp đúng 50 ghế cùng show mẫu.
3. Kịch bản k6 stress test 1,000 VUs sẵn sàng thực thi và kiểm chứng nguyên lý Zero Double-Booking.
4. Kịch bản E2E Smoke Test `smoke-test-e2e.sh` tự động hóa toàn bộ vòng đời khép kín không phát sinh lỗi.
