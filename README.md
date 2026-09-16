# Ticket Booking Platform

Enterprise-grade polyglot microservices monorepo for a high-performance ticket booking system.

## 🏗️ Architecture & Technology Stack

- **Monorepo Management:** Turborepo & PNPM Workspaces
- **Backend Services:**
  - **Auth Service:** Python (FastAPI, SQLAlchemy, Alembic, PostgreSQL, Redis) - JWT authentication, rate limiting, and session management.
  - **Booking Service:** Python (FastAPI) - Event and ticket reservation management.
  - **Payment Service:** Python - Secure payment processing and transaction handling.
  - **Notification Service:** TypeScript (NestJS) - Asynchronous notification processing (Email/SMS/Push via Kafka).
- **Shared Libraries (`libs/`):**
  - **Contracts:** Shared event validation schemas, Protobuf definitions (`event.proto`), and event type definitions (Booking, Payment, Notification).
  - **Common:** Shared TypeScript utilities including Kafka producer/consumer wrappers, correlation ID middleware, authentication guards, and structured logging.
- **Infrastructure (`infra/`):**
  - **Docker Compose:** PostgreSQL, Apache Kafka, Redis, Kong API Gateway.
  - **Scripts:** Infrastructure bootstrap (`bootstrap-vps.sh`), Kafka topic initialization (`init-topics.sh`), and smoke tests (`smoke-test-infra.sh`).

---

## 📁 Monorepo Structure

```text
.
├── services/
│   ├── auth-service/        # FastAPI Auth & User Management
│   ├── booking-service/     # FastAPI Booking Management
│   ├── payment-service/     # FastAPI Payment Processing
│   └── notification-service/ # NestJS Notification Service
├── libs/
│   ├── common/              # Shared TS utilities (Kafka, Logger, Guards, Middleware)
│   └── contracts/           # Shared Event Schemas & Protobuf definitions
└── infra/
    ├── docker/              # Docker compose and container configs
    ├── kong/                # Kong API Gateway configuration
    ├── kafka/               # Kafka topic initialization scripts
    └── scripts/             # VPS bootstrap and smoke testing scripts
```

---

## 🚀 Getting Started

### Prerequisites

- Node.js (v18+)
- PNPM (v9+)
- Python (v3.10+)
- Docker & Docker Compose

### Installation

1. Install workspace dependencies:
   ```bash
   pnpm install
   ```

2. Start infrastructure (PostgreSQL, Kafka, Redis, Kong):
   ```bash
   pnpm infra:up
   ```

3. Verify infrastructure health:
   ```bash
   pnpm infra:test
   ```

---

## 🛠️ Available Scripts

| Command | Description |
| :--- | :--- |
| `pnpm infra:up` | Start infrastructure services via Docker Compose |
| `pnpm infra:down` | Stop infrastructure services |
| `pnpm infra:test` | Run infrastructure smoke tests |
| `pnpm build` | Build all workspace packages and services using Turborepo |
| `pnpm test` | Run test suites across the monorepo |
| `pnpm lint` | Lint codebase across all packages |

---

## 📄 License

UNLICENSED
