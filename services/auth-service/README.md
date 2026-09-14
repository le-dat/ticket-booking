# 🔐 Auth Service - Ticket Booking System

Dịch vụ Xác thực và Phân quyền (Authentication & Role-Based Access Control - RBAC) cho hệ thống Đặt vé xem phim / sự kiện.

---

## 🛠️ Công Nghệ Sử Dụng

- **Runtime & Framework:** Python 3.12+ (quản lý bởi `uv`), FastAPI (Async/Await)
- **Cơ sở dữ liệu & Caching:** PostgreSQL (`auth_db`), Redis 7 (`ticket-booking-redis`), SQLAlchemy 2.0 Async, `asyncpg`, Alembic Async, `redis-py` async
- **Kiến trúc:** Layered Clean Architecture (`core`, `repositories`, `services`, `routers`, `middleware`, `models`, `schemas`)
- **Bảo mật:**
  - Mật khẩu: **Bcrypt** (cost factor 12) kèm xác thực giả lập (`DUMMY_BCRYPT_HASH`) chống Timing Attacks / User Enumeration
  - Token: **JWT Access Token** (HS256, 15 phút, kèm claim `jti` duy nhất) + **Refresh Token** (64 ký tự hex ngẫu nhiên, lưu hash SHA-256 trong PostgreSQL, 7 ngày)
  - Cơ chế **Token Rotation** & **Token Reuse Detection** (tự động huỷ toàn bộ phiên đăng nhập khi phát hiện Replay Attack)
  - Thu hồi tức thì (**Instant Token Revocation**): **Redis JTI Blacklist** huỷ Access Token ngay lập tức khi Logout mà không cần chờ hết hạn 15 phút (tự động dọn RAM qua TTL)
  - Giới hạn tần suất (**Rate Limiting**): **Redis Sliding Window** chạy bằng Lua script nguyên tử (chặn Brute-Force & DoS CPU tại `/login`, `/register`, `/refresh` với mã HTTP 429 và header `Retry-After`)
- **Truy vết (Observability):** `CorrelationIdMiddleware` tự động lan truyền `X-Request-ID` qua HTTP headers, application logs và cấu trúc response

---

## 🔄 Luồng Xác Thực, Xoay Vòng & Thu Hồi Token (Auth & RBAC Flow)

```mermaid
flowchart TD
    subgraph Auth["🔐 1. Đăng Nhập & Cấp Token"]
        A[Client] -->|POST /login| B[AuthService]
        B -->|Verify Bcrypt| DB[(PostgreSQL)]
        B -->|Trả về Access Token 15m + Refresh Token 7d| A
    end

    subgraph Refresh["🔄 2. Token Rotation & Chống Replay Attack"]
        A -->|POST /refresh| C[AuthService]
        C -->|Hash SHA-256 & kiểm tra| D{Trạng thái Token}
        D -->|Hợp lệ| E[Revoke token cũ & cấp cặp token mới] --> A
        D -->|Đã bị revoke trước đó| F[Phát hiện token bị lộ: Revoke toàn bộ token của User] --> A
    end

    subgraph RBAC["🛡️ 3. Xác Thực & Thu Hồi Tức Thì"]
        A -->|Request + Header: Bearer Token| G[get_current_user]
        G -->|Kiểm tra Redis| R{JTI Blacklist?}
        R -->|Nằm trong Blacklist| RJ[401 TOKEN_REVOKED]
        R -->|Hợp lệ| H{require_roles}
        H -->|Khớp vai trò| I[Xử lý Request: 200 OK]
        H -->|Không đủ quyền| J[403 FORBIDDEN]
    end

    subgraph Logout["🚪 4. Đăng Xuất & Thu Hồi Kép"]
        A -->|POST /logout| L[AuthService.logout]
        L -->|Lưu jti vào Redis với TTL = thời gian còn lại| RD[(Redis Blacklist)]
        L -->|Đánh dấu is_revoked = True| DB
        L -->|200 OK: Đăng xuất thành công| A
    end
```

### Điểm nổi bật về bảo mật:
1. **Đăng ký (`POST /register`):** Mặc định gán `role = CUSTOMER` chống leo quyền. Bắt ngoại lệ `IntegrityError` chống Race Condition khi đăng ký đồng thời. Bảo vệ bởi Redis Rate Limiter (3 req/phút).
2. **Đăng nhập (`POST /login`):** Tính toán hash Bcrypt giả lập (`DUMMY_BCRYPT_HASH`) khi email không tồn tại để chuẩn hóa thời gian phản hồi, ngăn chặn User Enumeration. Bảo vệ bởi Redis Rate Limiter (5 req/phút).
3. **Xoay vòng Token (`POST /refresh`):** Mỗi Refresh Token chỉ dùng 1 lần (Single-Use). Nếu phát hiện token cũ đã revoke được dùng lại, hệ thống lập tức hủy tất cả token của người dùng trên mọi thiết bị. Bảo vệ bởi Redis Rate Limiter (10 req/phút).
4. **Đăng xuất tức thì (`POST /logout`):** Đưa `jti` của Access Token vào Redis Blacklist (với TTL bằng thời gian sống còn lại), đồng thời đánh dấu `is_revoked = True` cho Refresh Token trong PostgreSQL. Chặn hoàn toàn việc tái sử dụng Access Token ngay sau khi đăng xuất.

---

## 📑 Danh Sách API Endpoints

Base URL: `http://localhost:3001`

| Phương thức | Endpoint | Yêu cầu Auth | Quyền hạn (RBAC) | Giới hạn (Rate Limit) | Mô tả |
|:---|:---|:---:|:---:|:---:|:---|
| `GET` | `/health` | ❌ Public | Bất kỳ | Không giới hạn | Liveness probe kiểm tra service & kết nối PostgreSQL |
| `POST` | `/api/v1/auth/register` | ❌ Public | Bất kỳ | 3 req / 60s | Đăng ký tài khoản người dùng mới (Mặc định `CUSTOMER`) |
| `POST` | `/api/v1/auth/login` | ❌ Public | Bất kỳ | 5 req / 60s | Đăng nhập, nhận Access Token (15m) & Refresh Token (7d) |
| `POST` | `/api/v1/auth/refresh` | ❌ Public | Bất kỳ | 10 req / 60s | Cấp cặp token mới (Token Rotation & chống Replay Attack) |
| `POST` | `/api/v1/auth/logout` | 🟡 Tuỳ chọn Bearer | Bất kỳ | Không giới hạn | Thu hồi Access Token vào Redis Blacklist & hủy Refresh Token trong DB |
| `GET` | `/api/v1/auth/me` | ✅ Bearer JWT | Bất kỳ | Không giới hạn | Lấy thông tin tài khoản đang đăng nhập |
| `GET` | `/api/v1/auth/admin-dashboard` | ✅ Bearer JWT | Chỉ `ADMIN` | Không giới hạn | Endpoint mẫu kiểm tra phân quyền RBAC |

---

## 🛑 Chuẩn Hóa Phản Hồi & Mã Lỗi Nghiệp Vụ

Tất cả phản hồi đều tuân theo cấu trúc Envelope chuẩn:
- **Thành công:** `{ "success": true, "data": ..., "message": "...", "request_id": "...", "timestamp": "..." }`
- **Thất bại:** `{ "success": false, "error": { "code": "...", "message": "...", "details": ... }, "request_id": "...", "timestamp": "..." }`

**Bảng mã lỗi (`ErrorCode`):**
- `RATE_LIMIT_EXCEEDED` (429): Vượt quá giới hạn số request cho phép (trả về kèm header `Retry-After`)
- `EMAIL_ALREADY_EXISTS` (409): Email đã tồn tại khi đăng ký
- `INVALID_CREDENTIALS` (401): Sai email hoặc mật khẩu
- `TOKEN_INVALID` (401): Token không hợp lệ, sai chữ ký hoặc sai định dạng
- `TOKEN_EXPIRED` (401): Token đã hết hạn sử dụng
- `TOKEN_REVOKED` (401): Token đã bị thu hồi (Logout hoặc phát hiện Replay Attack)
- `USER_NOT_FOUND` (401): Người dùng không tồn tại trong CSDL
- `FORBIDDEN` (403): Không đủ quyền thực thi thao tác (vi phạm RBAC)
- `VALIDATION_ERROR` (422): Sai cấu trúc dữ liệu gửi lên (validation form)
- `SERVICE_UNAVAILABLE` (503): Mất kết nối tới PostgreSQL hoặc lỗi hệ thống nội bộ

---

## ⚙️ Cấu Hình Biến Môi Trường (`.env`)

| Biến | Giá Trị Mẫu | Bắt Buộc | Mô Tả |
|:---|:---|:---:|:---|
| `PORT` | `3001` | Không | Cổng HTTP của Auth Service |
| `DATABASE_URL` | `postgresql+asyncpg://auth_user:auth_pass_secret_123@localhost:5432/auth_db` | Có | Chuỗi kết nối PostgreSQL async (asyncpg driver) |
| `REDIS_URL` | `redis://:redis_secret_123@localhost:6379/0` | Có | Chuỗi kết nối Redis cho Rate Limiting và JTI Blacklist |
| `JWT_SECRET` | `super_secret_jwt_key_ticket_booking_2026_very_long_and_secure` | Có | Khóa bí mật dùng để ký và giải mã JWT |
| `JWT_ALGORITHM` | `HS256` | Không | Thuật toán ký JWT |
| `JWT_ACCESS_EXPIRES_IN_MINUTES` | `15` | Không | Thời hạn sống của Access Token (phút) |
| `JWT_REFRESH_EXPIRES_IN_DAYS` | `7` | Không | Thời hạn sống của Refresh Token (ngày) |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:8000` | Không | Danh sách domain được phép gọi API (CORS) |
| `RATE_LIMIT_LOGIN_MAX` | `5` | Không | Giới hạn số lần gọi Login trong 1 chu kỳ |
| `RATE_LIMIT_LOGIN_WINDOW` | `60` | Không | Độ dài chu kỳ Rate Limit Login (giây) |
| `RATE_LIMIT_REGISTER_MAX` | `3` | Không | Giới hạn số lần đăng ký trong 1 chu kỳ |
| `RATE_LIMIT_REGISTER_WINDOW` | `60` | Không | Độ dài chu kỳ Rate Limit Đăng ký (giây) |
| `RATE_LIMIT_REFRESH_MAX` | `10` | Không | Giới hạn số lần refresh token trong 1 chu kỳ |
| `RATE_LIMIT_REFRESH_WINDOW` | `60` | Không | Độ dài chu kỳ Rate Limit Refresh (giây) |

---

## 🚀 Hướng Dẫn Khởi Chạy Nhanh

```bash
# 1. Cài đặt môi trường & dependencies
uv sync

# 2. Cấu hình biến môi trường
cp .env.example .env

# 3. Chạy Migration Database (yêu cầu PostgreSQL đang chạy)
uv run alembic upgrade head

# 4. Khởi chạy server
uv run uvicorn src.main:app --host 0.0.0.0 --port 3001 --reload
```

- **Swagger UI tương tác:** `http://localhost:3001/docs`
- **ReDoc:** `http://localhost:3001/redoc`
- **Health Check Probe:** `http://localhost:3001/health`

---

## 📖 Chi Tiết Triển Khai
Xem tài liệu hướng dẫn từng bước chi tiết tại [docs/milestone-2-auth-service.md](../../docs/milestone-2-auth-service.md).
