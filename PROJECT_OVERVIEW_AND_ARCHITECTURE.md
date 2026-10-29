# FastAPI E-Commerce Microservices Platform: Comprehensive System Architecture & Operations Manual

---

## 1. Executive Summary

This repository implements a production-grade, event-driven, distributed e-commerce microservices platform built with **FastAPI**, **PostgreSQL**, **Redis**, **RabbitMQ**, and **NGINX**.

The architecture decouples business capabilities into six autonomous microservices, coordinates asynchronous state transitions using RabbitMQ topic exchanges, utilizes Redis for high-throughput cart session management, and leverages async SQLAlchemy 2.0 with PostgreSQL for relational persistence. The entire system is orchestrated via Docker Compose, fronted by an NGINX reverse-proxy gateway that serves both the unified REST API and a vanilla JavaScript single-page application (SPA).

---

## 2. System Architecture & Topology

### 2.1 Global Architecture Diagram

```
                                  +----------------------------------+
                                  |      Client Browser / Postman    |
                                  +-----------------+----------------+
                                                    |
                                         HTTP Port 80
                                                    |
                                                    v
                      +--------------------------------------------------------------+
                      |                 NGINX API Gateway (:80)                      |
                      |   - Static SPA Hosting (/index.html, /index.css, /app.js)    |
                      |   - Reverse Proxy (/api/v1/*, /docs/*)                       |
                      +-----------------------------+--------------------------------+
                                                    |
      +-------------------+-----------------+-------+---------+-----------------+-------------------+
      |                   |                 |                 |                 |                   |
      v                   v                 v                 v                 v                   v
[User Service]   [Product Service]   [Cart Service]    [Order Service]   [Payment Service]   [Notification Service]
   Port: 8001         Port: 8002        Port: 8003        Port: 8004        Port: 8005          Port: 8006
      |                   |                 |                 |                 |                   |
      |                   |                 |                 +--------+--------+                   |
      |                   |                 |                          |                            |
      |                   |                 |              (HTTP Sync: Stock & Cart)                |
      |                   |                 |                          |                            |
      |                   |                 v                          v                            |
      |                   |         +---------------+                  |                            |
      |                   |         | Local Redis   |                  |                            |
      |                   |         |   Port 6379   |                  |                            |
      |                   |         +---------------+                  |                            |
      |                   |                                            |                            |
      v                   v                                            v                            v
+-------------------------------------------------------------------------------------------------------+
|                                    PostgreSQL 15 (Local / Neon Cloud)                                 |
|  Databases: `user_service` | `product_service` | `order_service` | `payment_service` | `ecommerce`  |
+-------------------------------------------------------------------------------------------------------+
      |                   |                                            ^                            ^
      |                   |                                            |                            |
      +-------------------+--------------------+-----------------------+----------------------------+
                                               |
                                     Async AMQP Events
                                               |
                                               v
                                +-----------------------------+
                                |      RabbitMQ (:5672)       |
                                | Management Dashboard :15672 |
                                +-----------------------------+
```

### 2.2 Network & Routing Layout

| Route / Prefix | Target Upstream | Target Internal Port | Purpose |
| :--- | :--- | :--- | :--- |
| `/` | Gateway static mount | Container `/usr/share/nginx/html` | Serves Frontend SPA (`index.html`) |
| `/api/v1/auth` | `user_service` | `8001` | Authentication & token lifecycle |
| `/api/v1/users` | `user_service` | `8001` | Profile management & RBAC |
| `/api/v1/products` | `product_service` | `8002` | Catalog browsing & product CRUD |
| `/api/v1/categories` | `product_service` | `8002` | Category tree management |
| `/api/v1/cart` | `cart_service` | `8003` | Session & authenticated cart management |
| `/api/v1/orders` | `order_service` | `8004` | Order placement, checkout, order history |
| `/api/v1/payments` | `payment_service` | `8005` | Stripe PaymentIntents & webhooks |
| `/api/v1/notifications`| `notification_service` | `8006` | Notification preferences & status |
| `/docs/<service>` | `<service>/docs` | Varied | Proxied OpenAPI Swagger UI per service |
| `/api/info` | NGINX direct response | `80` | Gateway metadata and service directory |

---

## 3. Shared Library Architecture (`shared/`)

To prevent code duplication across microservices, shared cross-cutting concerns reside in the root [`shared/`](file:///Users/jeet/code/fastapi_ecommerce_microservice/shared) module, which is copied into `/app/shared` in every Docker image.

### 3.1 Security & Authentication (`shared/auth.py`)
- **JWT Cryptography**: Uses `PyJWT` with configurable algorithms (`HS256` default). Generates access tokens (`30m` default) and refresh tokens (`7d` default).
- **Password Security**: Direct `bcrypt` integration (`hashpw` and `checkpw`) ensuring salt generation and safe verification without relying on legacy passlib wrappers.
- **Payload Schema (`TokenPayload`)**: Contains `sub` (user ID), `roles` (`customer`, `admin`, `seller`), `iat`, `exp`, and token `type`.
- **RBAC**: Dependency injection helpers for extracting current user and enforcing role restrictions.

### 3.2 Async Persistence (`shared/database.py`)
- **SQLAlchemy 2.0 Async Engine**: Encapsulated in `DatabaseManager` using `create_async_engine` and `async_sessionmaker`.
- **Connection Health**: Configured with `pool_pre_ping=True`, pool size of 5 connections, and overflow up to 10 connections.
- **Naming Conventions**: Enforces standardized constraint names (`ix_`, `uq_`, `ck_`, `fk_`, `pk_`) via metadata conventions for smooth Alembic migrations.
- **Session Lifecycle**: Asynchronous generator yielding `AsyncSession` with automatic `commit()` on success and `rollback()` on unhandled exceptions.

### 3.3 Dynamic Configuration Management (`shared/config.py`)
- **Inheritance Hierarchy**:
  - `BaseSettings`: Global settings (JWT secrets, token lifespans, RabbitMQ host/port/credentials).
  - `DatabaseSettings`: DB parameters (`db_host`, `db_port`, `db_name`, `db_user`, `db_password`, `db_ssl_mode`).
  - `RedisSettings`: Cache parameters (`redis_host`, `redis_port`, `redis_password`, `redis_db`).
- **SSL Negotiation Optimization**:
  - When `db_ssl_mode` is set to `"disable"`, `"none"`, or empty, connection strings are built as `postgresql+asyncpg://user:pass@host:port/db` (omitting SSL query parameters to avoid local asyncpg handshake failures).
  - When set to `"require"`, connection strings automatically append `?ssl=require` (for cloud databases like Neon).

### 3.4 Messaging Abstraction (`shared/messaging.py`)
- **Async Client (`RabbitMQClient`)**: Built on `aio_pika` with `connect_robust()`.
- **Topological Setup**: Declares durable `TOPIC` exchanges, durable queues, prefetch QoS counts, and handles JSON serialization.
- **Canonical Event Format (`EventMessage`)**:
  ```json
  {
    "event_type": "order.created",
    "payload": { ... },
    "source_service": "order_service",
    "timestamp": "2026-10-21T15:00:00.000000",
    "correlation_id": "optional-uuid"
  }
  ```

### 3.5 Contract Envelope Schemas (`shared/schemas.py`)
- `ResponseModel[T]`: Unified response wrapper `{ "success": true, "message": "...", "data": T }`.
- `PaginatedResponse[T]`: Envelope containing `items`, `total`, `page`, `size`, `pages`.
- `PaginationParams`: Query dependency calculating SQL `offset` (`skip`) and `limit`.
- Enums: `OrderStatus`, `PaymentStatus`, `UserRole`.

---

## 4. Deep-Dive Microservice Breakdown

### 4.1 User Service (Port: 8001)
- **Role**: Identity provider, account management, RBAC enforcement.
- **Database**: PostgreSQL database `user_service` (Table: `users`).
- **Key Modules**:
  - `routers/auth.py`: Registration, login, JWT token refresh, password reset endpoints.
  - `routers/users.py`: Profile view/edit (`/me`), admin user queries, role modification.
  - `services/user_service.py`: User entity CRUD, password hashing, verification checks.
  - `events.py`: Publishes `user.registered`, `user.password_reset` to `user_events` exchange.

### 4.2 Product Service (Port: 8002)
- **Role**: Catalog management, hierarchical categories, inventory tracking.
- **Database**: PostgreSQL database `product_service` (Tables: `categories`, `products`, `product_images`).
- **Key Modules**:
  - `routers/products.py`: Product search, filtering by category/price, creation, stock adjustments.
  - `routers/categories.py`: Nested category hierarchies, slug generation, category trees.
  - `services/product_service.py`: Stock validation, low-stock threshold monitoring.
  - `events.py`: Declares `product_events` exchange for stock alerts.

### 4.3 Cart Service (Port: 8003)
- **Role**: Ephemeral, low-latency shopping cart storage for guest sessions and registered users.
- **Persistence**: Local Redis 7 (`ecommerce-redis`).
- **Key Modules**:
  - `app/redis_client.py`: Async Redis client wrapper performing hash operations (`hget`, `hset`, `hgetall`, `delete`, `set`).
  - `routers/cart.py`:
    - Session tracking via header `X-Session-ID` (guest: `guest_<hash>`) or JWT Bearer token (authenticated user).
    - Item additions, quantity increments, deletions, cart flushing.
    - Guest-to-user cart migration and merging upon login.
  - `health`: Directly pings Redis on `/health` and reports dependency health.

### 4.4 Order Service (Port: 8004)
- **Role**: Order orchestration, stock validation, checkout execution, order state lifecycle.
- **Database**: PostgreSQL database `order_service` (Tables: `orders`, `order_items`).
- **Key Integrations**:
  - **Synchronous HTTP**:
    - Validates product stock and pricing with `Product Service` via `httpx`.
    - Clears customer cart with `Cart Service` via `httpx` upon successful placement.
  - **Asynchronous AMQP Consumer (`app/consumers.py`)**:
    - Subscribes to `order_payment_queue` bound to `payment_events` (`payment.completed`, `payment.failed`).
    - Transitions order status from `PENDING` to `CONFIRMED` or `CANCELLED`.
  - **Asynchronous AMQP Producer (`app/events.py`)**:
    - Publishes `order.created`, `order.confirmed`, `order.shipped`, `order.cancelled` to `order_events`.

### 4.5 Payment Service (Port: 8005)
- **Role**: Payment gateway abstraction, Stripe PaymentIntent orchestration, refund processing.
- **Database**: PostgreSQL database `payment_service` (Table: `payments`).
- **Key Modules**:
  - `routers/payments.py`: Payment creation, Stripe client secret issuance, webhook listeners.
  - `services/payment_service.py`: Stripe SDK integration, status tracking (`pending`, `completed`, `failed`, `refunded`).
  - `events.py`: Publishes `payment.completed`, `payment.failed`, `payment.refunded` to `payment_events`.

### 4.6 Notification Service (Port: 8006)
- **Role**: Transactional communications consumer.
- **Email Provider**: Brevo API (formerly Sendinblue).
- **Event Consumer (`app/events.py`)**:
  - Declares queue `notification_queue` bound with `#` (wildcard) to:
    - `order_events`
    - `payment_events`
    - `product_events`
    - `user_events`
  - Automatically fetches user profile data from `User Service` via HTTP and dispatches transactional emails.

---

## 5. Messaging & Event-Driven Workflows

### 5.1 RabbitMQ Topology

```
Exchanges (Topic)             Queues                           Consumers
=================             ======                           =========

[user_events]      --------+-> [notification_queue] --------> Notification Service
                           |
[product_events]   --------+
                           |
[order_events]     --------+
                           |
[payment_events]   --(#)---+
                           |
                     (payment.completed, payment.failed)
                           |
                           +-> [order_payment_queue] -------> Order Service
```

### 5.2 End-to-End Order & Payment Event Flow

```
User / Frontend
     |
     | 1. POST /api/v1/orders/ (Checkout)
     v
[Order Service]
     |--- 2. GET /api/v1/products/{id} (Validate Stock) ---> [Product Service]
     |--- 3. DELETE /api/v1/cart/ (Clear Cart) -----------> [Cart Service]
     |--- 4. Publish `order.created` ---------------------> [RabbitMQ: order_events]
     |                                                              |
     |                                                              +--> [Notification Service] (Email Confirmation)
     v
[Payment Service]
     |--- 5. POST /api/v1/payments/ (Stripe PaymentIntent)
     |--- 6. User Completes Payment on Stripe
     |--- 7. Publish `payment.completed` -----------------> [RabbitMQ: payment_events]
                                                                    |
                                   +--------------------------------+
                                   |
                                   v
                         [Order Service Consumer]
                         - Reads `payment.completed`
                         - Updates order status -> `CONFIRMED`
                         - Publishes `order.confirmed` ----> [RabbitMQ] --> [Notification Service]
```

---

## 6. Storage & Caching Layer

### 6.1 Multi-Database PostgreSQL Architecture
Rather than creating 4 heavy, separate PostgreSQL containers, the platform uses a single PostgreSQL 15 instance (`ecommerce-postgres`) configured with isolated databases per service boundary.

- **Initialization Script ([`scripts/init-db.sh`](file:///Users/jeet/code/fastapi_ecommerce_microservice/scripts/init-db.sh))**:
  Automatically executed on container initialization via `/docker-entrypoint-initdb.d/`:
  - `user_service`
  - `product_service`
  - `order_service`
  - `payment_service`
  - Default database: `ecommerce`
  - Superuser: `ecommerce` / `ecommerce_secret`
- **Tables Auto-Creation**: Every FastAPI service calls `await db_manager.create_tables()` during lifespan startup, generating all tables from SQLAlchemy models if not already present.

### 6.2 Redis Cart Caching
- **Engine**: Redis 7 Alpine.
- **Port**: `6379`.
- **Key Pattern**: `cart:<user_id_or_session_id>`
- **TTL**: 7 days (`604800` seconds).
- **Structure**: JSON-serialized cart records containing item lists, totals, and metadata.

---

## 7. API Gateway & Frontend SPA

### 7.1 NGINX Gateway Configuration ([`gateway/nginx.conf`](file:///Users/jeet/code/fastapi_ecommerce_microservice/gateway/nginx.conf))
- **Worker Configuration**: 1024 connections.
- **Reverse Proxy**: Proxies requests with `Host`, `X-Real-IP`, `X-Forwarded-For`, and `X-Forwarded-Proto` headers.
- **Static Assets & SPA Routing**:
  ```nginx
  location / {
      root /usr/share/nginx/html;
      index index.html;
      try_files $uri $uri/ /index.html;
  }
  ```

### 7.2 Frontend Application ([`frontend/`](file:///Users/jeet/code/fastapi_ecommerce_microservice/frontend))
- **Tech Stack**: Vanilla HTML5, modern CSS3 (custom CSS variables, responsive design, dark navigation), and vanilla JavaScript.
- **State Management**: Client-side hash routing (`#/`, `#/products`, `#/cart`, `#/orders`, `#/login`, `#/register`, `#/profile`), token persistence in `localStorage`, and guest cart persistence.

---

## 8. Operations & Run Guide

### 8.1 Prerequisites
- Docker Engine & Docker Compose (`docker compose version 2.x`+)
- Ports available on host: `80`, `5432`, `6379`, `5672`, `15672`, `8001`, `8002`, `8003`, `8004`, `8005`, `8006`

### 8.2 Environment Configuration
Create or modify [`.env`](file:///Users/jeet/code/fastapi_ecommerce_microservice/.env) from [`.env.example`](file:///Users/jeet/code/fastapi_ecommerce_microservice/.env.example):

```bash
# Security & JWT
JWT_SECRET_KEY=dev-super-secret-jwt-key-minimum-32-characters-for-local-use
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
REFRESH_TOKEN_EXPIRE_DAYS=7

# Local PostgreSQL Configuration
DB_SSL_MODE=disable
POSTGRES_USER=ecommerce
POSTGRES_PASSWORD=ecommerce_secret
POSTGRES_DB=ecommerce
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Service Specific Database Overrides
USER_DB_HOST=postgres
USER_DB_PORT=5432
USER_DB_NAME=user_service
USER_DB_USER=ecommerce
USER_DB_PASSWORD=ecommerce_secret

PRODUCT_DB_HOST=postgres
PRODUCT_DB_PORT=5432
PRODUCT_DB_NAME=product_service
PRODUCT_DB_USER=ecommerce
PRODUCT_DB_PASSWORD=ecommerce_secret

ORDER_DB_HOST=postgres
ORDER_DB_PORT=5432
ORDER_DB_NAME=order_service
ORDER_DB_USER=ecommerce
ORDER_DB_PASSWORD=ecommerce_secret

PAYMENT_DB_HOST=postgres
PAYMENT_DB_PORT=5432
PAYMENT_DB_NAME=payment_service
PAYMENT_DB_USER=ecommerce
PAYMENT_DB_PASSWORD=ecommerce_secret

# Redis (Cart Service)
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=

# RabbitMQ (Message Broker)
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=ecommerce
RABBITMQ_PASSWORD=ecommerce_secret
RABBITMQ_URL=amqp://ecommerce:ecommerce_secret@rabbitmq:5672/

# Service Endpoints
USER_SERVICE_URL=http://user_service:8001
PRODUCT_SERVICE_URL=http://product_service:8002
CART_SERVICE_URL=http://cart_service:8003
ORDER_SERVICE_URL=http://order_service:8004
PAYMENT_SERVICE_URL=http://payment_service:8005
NOTIFICATION_SERVICE_URL=http://notification_service:8006

# Third Party Integrations
STRIPE_SECRET_KEY=sk_test_mock
STRIPE_WEBHOOK_SECRET=whsec_mock
BREVO_API_KEY=
BREVO_FROM_EMAIL=noreply@example.com
BREVO_FROM_NAME=E-Commerce Platform
```

### 8.3 Starting the Platform
To build and boot all 10 containers in detached mode:

```bash
docker compose up -d --build
```

To view live status:
```bash
docker compose ps
```

To tail logs for all or specific services:
```bash
# All services
docker compose logs -f

# Specific services
docker compose logs -f user_service order_service rabbitmq
```

To stop all services:
```bash
docker compose down
```

To reset all data (including volumes):
```bash
docker compose down -v
```

---

## 9. Verification & Live Inspection Commands

### 9.1 Verify Health of All Services
```bash
curl -s http://localhost/health && echo ""
curl -s http://localhost:8001/health && echo ""
curl -s http://localhost:8002/health && echo ""
curl -s http://localhost:8003/health && echo ""
curl -s http://localhost:8004/health && echo ""
curl -s http://localhost:8005/health && echo ""
curl -s http://localhost:8006/health && echo ""
```

### 9.2 Inspect PostgreSQL Databases Directly
```bash
# List all microservice databases
docker exec ecommerce-postgres psql -U ecommerce -d ecommerce -c "\l"

# Inspect User Service tables
docker exec ecommerce-postgres psql -U ecommerce -d user_service -c "\dt"

# Query registered users
docker exec ecommerce-postgres psql -U ecommerce -d user_service -c "SELECT id, email, first_name, role, is_active FROM users;"
```

### 9.3 Inspect Redis Directly
```bash
# Ping Redis
docker exec ecommerce-redis redis-cli ping

# Inspect all active cart keys
docker exec ecommerce-redis redis-cli keys "cart:*"

# Read raw cart payload
docker exec ecommerce-redis redis-cli get "<cart_key>"
```

### 9.4 Inspect RabbitMQ Directly
```bash
# List active AMQP connections
docker exec ecommerce-rabbitmq rabbitmqctl list_connections

# List active topic exchanges
docker exec ecommerce-rabbitmq rabbitmqctl list_exchanges

# List active queues and message backlogs
docker exec ecommerce-rabbitmq rabbitmqctl list_queues

# List consumer subscriptions
docker exec ecommerce-rabbitmq rabbitmqctl list_consumers
```

---

## 10. End-to-End API Walkthrough

### Step 1: Register User
```bash
curl -X POST http://localhost/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "customer@example.com",
    "password": "Password123!",
    "first_name": "Jane",
    "last_name": "Doe"
  }'
```

### Step 2: Login and Extract JWT
```bash
TOKEN=$(curl -s -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "customer@example.com",
    "password": "Password123!"
  }' | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

echo "Access Token: $TOKEN"
```

### Step 3: Access Protected User Profile
```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost/api/v1/users/me
```

### Step 4: Add Sample Product to Catalog
```bash
curl -X POST http://localhost/api/v1/products/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Smart Fitness Watch",
    "description": "Waterproof fitness tracker with heart rate monitor",
    "price": 129.99,
    "compare_at_price": 159.99,
    "sku": "FIT-WATCH-001",
    "stock_quantity": 100,
    "is_featured": true
  }'
```.

### Step 5: Add Product to Cart
```bash
curl -X POST http://localhost/api/v1/cart/items \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 1,
    "product_name": "Smart Fitness Watch",
    "price": 129.99,
    "quantity": 1
  }'
```

### Step 6: Checkout / Place Order
```bash
curl -X POST http://localhost/api/v1/orders/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "shipping_address": {
      "street": "123 Market St",
      "city": "San Francisco",
      "state": "CA",
      "postal_code": "94105",
      "country": "USA"
    },
    "payment_method": "stripe"
  }'
```

---

## 11. Project Maintenance & Development Roadmap

| Area | Current Status | Recommended Next Enhancement |
| :--- | :--- | :--- |
| **Authentication** | Active JWT issuance and password hashing | Implement token verification link callbacks and email token persistence in `routers/auth.py`. |
| **Search & Filtering**| Direct SQL ILIKE filters | Add PostgreSQL Full-Text Search (`tsvector`) or ElasticSearch integration for large product catalogs. |
| **Stripe Payments** | PaymentIntent creation implemented | Add Stripe webhook cryptographic signature verification (`stripe.Webhook.construct_event`) in `routers/payments.py`. |
| **Redis Cart** | Direct async client operations | Add Redis connection pooling and exponential backoff retry policies in `redis_client.py`. |
| **Dead Letter Exchanges**| Errors logged | Add RabbitMQ Dead Letter Exchanges (DLX) for unprocessable messages in `shared/messaging.py`. |
