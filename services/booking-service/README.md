# Booking Service

[🇻🇳 Tiếng Việt](README_VN.md)

High-performance Booking & Seat Reservation microservice for the Ticket Booking Platform, built with Go Clean Architecture.

---

## 🏛️ Architecture & Highlights

- **Port:** HTTP REST API on `3003`
- **Redis Distributed Hold Engine:** High-concurrency seat locking (`SET lock:show:{show_id}:seat:{seat_id} {user_id} NX PX {ttl}`) with Lua atomic releases to eliminate overselling / double-booking.
- **gRPC Integration:** Synchronous seat verification and hold persistence with `event-service` on port `50052`.
- **Transactional Outbox Pattern:** Atomic persistence of `bookings`, `booking_items`, and `outbox_events` in a single PostgreSQL transaction; background worker dispatches events to Kafka (`booking-events`).
- **Expiry Engine:** Periodic background poller scanning pending bookings older than 10 minutes (`FOR UPDATE SKIP LOCKED`), marking them `EXPIRED`, and releasing held seats via Saga compensation.
- **Payment Consumer:** Kafka consumer listening on `payment-events` (`PaymentProcessed` -> `CONFIRMED`).

---

## 🚀 API Endpoints (v1)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/v1/bookings` | Create booking, lock seats (Redis + gRPC), and record Outbox event |
| `GET` | `/v1/bookings/:id` | Get booking details and items |
| `POST` | `/v1/bookings/:id/cancel` | Cancel pending booking and release held seats |
| `GET` | `/healthz` | Health check endpoint |
| `GET` | `/metrics` | Prometheus metrics |

---

## 🛠️ Quick Start

```bash
# Run migrations and start service
make run
```
