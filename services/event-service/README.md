# Event Service

[🇻🇳 Tiếng Việt](README_VN.md)

High-performance Event Management microservice for the Ticket Booking Platform, built with **Clean Architecture** in Golang.

---

## 🏗️ Tech Stack & Libraries

- **Language:** Go 1.22+
- **Web Framework:** [Fiber](https://github.com/gofiber/fiber) (REST API)
- **RPC Transports:** gRPC, AMQP RPC (RabbitMQ), NATS RPC (NATS)
- **Database:** PostgreSQL with [Squirrel](https://github.com/Masterminds/squirrel) query builder & `golang-migrate`
- **Observability:** OpenTelemetry (Distributed Tracing), Prometheus (Metrics), ZeroLog (Structured Logging)
- **Testing & Mocking:** Testify & Go Mock

---

## 🏛️ Domain & Features

Event Service manages event catalogs, venues, showtimes, and seat layouts for ticket bookings:

- **Venues:** Manage concert halls, stadiums, and performance locations.
- **Events:** Manage event listings, metadata, banners, and statuses (`DRAFT`, `PUBLISHED`, `CANCELLED`).
- **Shows:** Manage scheduled showtimes for events.
- **Seats:** Manage seating maps and real-time seat availability for shows.

### API Endpoints (REST v1)

| Operation | Method & Path | Description |
| :--- | :--- | :--- |
| List Events | `GET /v1/events` | Get all published events |
| Event Detail | `GET /v1/events/:id` | Get event details and shows |
| Show Seats | `GET /v1/shows/:id/seats` | Get seat map and availability for a show |
| Create Venue | `POST /v1/venues` | Create a new venue (Admin) |
| Create Event | `POST /v1/events` | Create a new event (Admin) |
| Create Show | `POST /v1/events/:id/shows` | Schedule a show for an event (Admin) |

---

## 🚀 Quick Start

### 1. Start Infrastructure (From Monorepo Root)

From the monorepo root, start the shared infrastructure (PostgreSQL, Kafka, Redis, Kong, RabbitMQ, NATS):

```sh
# Root directory
pnpm install
pnpm infra:up
```

Verify infrastructure health:
```sh
pnpm infra:test
```

### 2. Run Event Service Locally

```sh
cd services/event-service
# Run app with automatic database migrations
make run
```

---

## 📊 Observability

Distributed tracing is provided by **OpenTelemetry** with OTLP export to Jaeger. Metrics are exposed at `/metrics` for Prometheus scraping. Structured logging is handled via **ZeroLog**.

Configuration (.env):
- `TRACING_ENABLED=true`
- `TRACING_OTLP_ENDPOINT=localhost:4317`
- `PG_URL=postgres://user:password@localhost:5432/event_db`
