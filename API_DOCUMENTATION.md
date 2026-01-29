# E-Commerce Platform API Documentation

> **Base URL**: `http://localhost` (via NGINX Gateway)  
> **Version**: 1.0.0

---

## Table of Contents

1. [Authentication](#authentication)
2. [User Service](#user-service-port-8001)
3. [Product Service](#product-service-port-8002)
4. [Cart Service](#cart-service-port-8003)
5. [Order Service](#order-service-port-8004)
6. [Payment Service](#payment-service-port-8005)
7. [Response Format](#response-format)
8. [Error Handling](#error-handling)

---

## Authentication

All protected endpoints require a **Bearer Token** in the Authorization header:

```http
Authorization: Bearer <access_token>
```

### Token Lifecycle

| Token Type | Expiry | Usage |
|------------|--------|-------|
| Access Token | 30 minutes | API requests |
| Refresh Token | 7 days | Get new access token |

---

## User Service (Port 8001)

Base path: `/api/v1`

### Authentication Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/auth/register` | ❌ | Register new user |
| `POST` | `/auth/login` | ❌ | Login and get tokens |
| `POST` | `/auth/refresh` | ❌ | Refresh access token |
| `POST` | `/auth/forgot-password` | ❌ | Request password reset |
| `POST` | `/auth/reset-password` | ❌ | Reset password with token |
| `POST` | `/auth/verify-email/{token}` | ❌ | Verify email address |

---

#### POST `/auth/register`

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "first_name": "John",
  "last_name": "Doe",
  "phone": "+1234567890"
}
```

**Response:** `201 Created`
```json
{
  "success": true,
  "message": "User registered successfully. Please verify your email.",
  "data": {
    "id": 1,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "phone": "+1234567890",
    "role": "customer",
    "is_active": true,
    "is_verified": false,
    "created_at": "2026-01-28T10:00:00Z"
  }
}
```

---

#### POST `/auth/login`

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

---

#### POST `/auth/refresh`

**Request:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:** Returns new access and refresh tokens (same format as login)

---

### User Management Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/users/me` | ✅ | Get current user profile |
| `PUT` | `/users/me` | ✅ | Update profile |
| `POST` | `/users/me/change-password` | ✅ | Change password |
| `DELETE` | `/users/me` | ✅ | Delete account |
| `GET` | `/users/` | 🔐 Admin | List all users |
| `GET` | `/users/{user_id}` | 🔐 Admin | Get user by ID |
| `DELETE` | `/users/{user_id}` | 🔐 Admin | Delete user |

---

#### PUT `/users/me`

**Request:**
```json
{
  "first_name": "John",
  "last_name": "Smith",
  "phone": "+1987654321"
}
```

---

#### POST `/users/me/change-password`

**Request:**
```json
{
  "current_password": "oldpassword123",
  "new_password": "newpassword456"
}
```

---

## Product Service (Port 8002)

Base path: `/api/v1`

### Product Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/products/` | ❌ | List products with filters |
| `GET` | `/products/{product_id}` | ❌ | Get product by ID |
| `GET` | `/products/slug/{slug}` | ❌ | Get product by slug |
| `POST` | `/products/` | 🔐 Admin | Create product |
| `PUT` | `/products/{product_id}` | 🔐 Admin | Update product |
| `DELETE` | `/products/{product_id}` | 🔐 Admin | Delete product |
| `GET` | `/products/{product_id}/stock` | ❌ | Get stock info |
| `PUT` | `/products/{product_id}/stock` | 🔐 Admin | Update stock |
| `POST` | `/products/stock/check` | ❌ | Check stock for multiple products |

---

#### GET `/products/`

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | int | Page number (default: 1) |
| `size` | int | Items per page (default: 10, max: 100) |
| `category_id` | int | Filter by category |
| `min_price` | decimal | Minimum price filter |
| `max_price` | decimal | Maximum price filter |
| `in_stock_only` | bool | Only show in-stock items |
| `is_featured` | bool | Filter featured products |
| `search` | string | Search in name/description |
| `sort_by` | string | Sort field: `name`, `price`, `created_at`, `stock_quantity` |
| `sort_order` | string | `asc` or `desc` |

**Response:**
```json
{
  "success": true,
  "message": "Retrieved 10 products",
  "data": [
    {
      "id": 1,
      "name": "iPhone 15 Pro",
      "slug": "iphone-15-pro",
      "description": "Latest Apple smartphone",
      "price": "999.99",
      "compare_at_price": "1099.99",
      "sku": "IPHONE-15-PRO",
      "stock_quantity": 50,
      "is_active": true,
      "is_featured": true,
      "category_id": 1,
      "images": ["https://example.com/iphone.jpg"],
      "created_at": "2026-01-28T10:00:00Z"
    }
  ]
}
```

---

#### POST `/products/`

**Request:**
```json
{
  "name": "New Product",
  "description": "Product description",
  "price": "99.99",
  "compare_at_price": "129.99",
  "sku": "PROD-001",
  "stock_quantity": 100,
  "is_active": true,
  "is_featured": false,
  "category_id": 1,
  "images": ["https://example.com/image.jpg"]
}
```

---

### Category Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/categories/` | ❌ | List all categories |
| `GET` | `/categories/tree` | ❌ | Get category tree structure |
| `GET` | `/categories/{category_id}` | ❌ | Get category by ID |
| `GET` | `/categories/slug/{slug}` | ❌ | Get category by slug |
| `POST` | `/categories/` | 🔐 Admin | Create category |
| `PUT` | `/categories/{category_id}` | 🔐 Admin | Update category |
| `DELETE` | `/categories/{category_id}` | 🔐 Admin | Delete category |

---

#### GET `/categories/tree`

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "Electronics",
      "slug": "electronics",
      "children": [
        {
          "id": 2,
          "name": "Smartphones",
          "slug": "smartphones",
          "children": []
        }
      ]
    }
  ]
}
```

---

## Cart Service (Port 8003)

Base path: `/api/v1/cart`

> **Note**: Cart works for both authenticated users and guests. Guest carts use temporary IDs.

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/` | ⚡ | Get current cart |
| `POST` | `/items` | ⚡ | Add item to cart |
| `PUT` | `/items/{product_id}` | ⚡ | Update item quantity |
| `DELETE` | `/items/{product_id}` | ⚡ | Remove item from cart |
| `DELETE` | `/` | ⚡ | Clear entire cart |
| `GET` | `/summary` | ⚡ | Get cart summary for checkout |
| `POST` | `/merge` | ✅ | Merge guest cart after login |
| `POST` | `/validate` | ⚡ | Validate cart before checkout |

⚡ = Works with or without authentication

---

#### POST `/items`

**Request:**
```json
{
  "product_id": 1,
  "quantity": 2
}
```

**Response:**
```json
{
  "success": true,
  "message": "Item added to cart",
  "data": {
    "user_id": "user_123",
    "items": [
      {
        "product_id": 1,
        "quantity": 2,
        "price": "999.99",
        "name": "iPhone 15 Pro"
      }
    ],
    "total_items": 2,
    "subtotal": "1999.98"
  }
}
```

---

#### GET `/summary`

**Response:**
```json
{
  "success": true,
  "data": {
    "subtotal": "1999.98",
    "tax": "180.00",
    "shipping": "9.99",
    "total": "2189.97",
    "item_count": 2
  }
}
```

---

#### POST `/merge`

**Request:**
```json
{
  "guest_cart_id": "guest_abc123"
}
```

---

## Order Service (Port 8004)

Base path: `/api/v1/orders`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/` | ✅ | Create new order |
| `GET` | `/` | ✅ | List user's orders |
| `GET` | `/{order_id}` | ✅ | Get order details |
| `GET` | `/number/{order_number}` | ✅ | Get order by order number |
| `POST` | `/{order_id}/cancel` | ✅ | Cancel order |
| `PUT` | `/{order_id}/status` | 🔐 Admin | Update order status |
| `PUT` | `/{order_id}/tracking` | 🔐 Admin | Add tracking info |
| `GET` | `/admin/all` | 🔐 Admin | List all orders |

---

#### POST `/`

**Request:**
```json
{
  "shipping_address": {
    "street": "123 Main St",
    "city": "New York",
    "state": "NY",
    "postal_code": "10001",
    "country": "US"
  },
  "billing_address": {
    "street": "123 Main St",
    "city": "New York",
    "state": "NY",
    "postal_code": "10001",
    "country": "US"
  },
  "notes": "Please leave at door"
}
```

**Response:** `201 Created`
```json
{
  "success": true,
  "message": "Order created successfully",
  "data": {
    "id": 1,
    "order_number": "ORD-20260128-ABC123",
    "status": "pending",
    "items": [...],
    "subtotal": "1999.98",
    "tax": "180.00",
    "shipping": "9.99",
    "total": "2189.97",
    "created_at": "2026-01-28T10:00:00Z"
  }
}
```

---

#### GET `/`

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | int | Page number |
| `size` | int | Items per page |
| `status_filter` | enum | Filter by status: `pending`, `confirmed`, `processing`, `shipped`, `delivered`, `cancelled` |

---

#### PUT `/{order_id}/tracking`

**Request:**
```json
{
  "tracking_number": "1Z999AA10123456784",
  "carrier": "UPS"
}
```

---

## Payment Service (Port 8005)

Base path: `/api/v1/payments`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/create-intent` | ✅ | Create Stripe payment intent |
| `GET` | `/{payment_id}` | ✅ | Get payment details |
| `GET` | `/order/{order_id}` | ✅ | Get payment for order |
| `POST` | `/refund` | 🔐 Admin | Process refund |
| `POST` | `/webhook/stripe` | ❌ | Stripe webhook handler |
| `POST` | `/test/confirm/{payment_id}` | ✅ | [TEST] Confirm payment |

---

#### POST `/create-intent`

**Request:**
```json
{
  "order_id": 1,
  "currency": "usd"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Payment intent created",
  "data": {
    "payment_id": 1,
    "client_secret": "pi_xxx_secret_xxx",
    "amount": 218997,
    "currency": "usd",
    "status": "requires_payment_method"
  }
}
```

> **Frontend Integration**: Use `client_secret` with Stripe.js to complete payment.

---

#### POST `/refund`

**Request:**
```json
{
  "payment_id": 1,
  "amount": 100.00,
  "reason": "Customer requested refund"
}
```

---

## Response Format

All API responses follow this standard format:

```json
{
  "success": boolean,
  "message": "string (optional)",
  "data": object | array | null
}
```

---

## Error Handling

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| `200` | OK |
| `201` | Created |
| `400` | Bad Request (validation error) |
| `401` | Unauthorized (missing/invalid token) |
| `403` | Forbidden (insufficient permissions) |
| `404` | Not Found |
| `422` | Unprocessable Entity |
| `500` | Internal Server Error |

### Error Response Format

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Validation Errors

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## User Roles

| Role | Description |
|------|-------------|
| `customer` | Default role for registered users |
| `admin` | Full access to all endpoints |

---

## Pagination

All list endpoints support pagination:

| Parameter | Default | Max | Description |
|-----------|---------|-----|-------------|
| `page` | 1 | - | Page number |
| `size` | 10 | 100 | Items per page |

---

## OpenAPI/Swagger

Each service exposes interactive API docs:

| Service | Swagger UI | OpenAPI JSON |
|---------|------------|--------------|
| User Service | `http://localhost:8001/docs` | `/openapi.json` |
| Product Service | `http://localhost:8002/docs` | `/openapi.json` |
| Cart Service | `http://localhost:8003/docs` | `/openapi.json` |
| Order Service | `http://localhost:8004/docs` | `/openapi.json` |
| Payment Service | `http://localhost:8005/docs` | `/openapi.json` |
