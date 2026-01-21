# E-commerce Microservices Platform

A scalable e-commerce platform built with FastAPI microservices architecture and Docker.

## 🏗️ Architecture

This platform consists of 6 core microservices:

| Service | Port | Description |
|---------|------|-------------|
| **User Service** | 8001 | Authentication, registration, profile management |
| **Product Service** | 8002 | Product catalog, categories, inventory |
| **Cart Service** | 8003 | Shopping cart management (Redis-backed) |
| **Order Service** | 8004 | Order processing and management |
| **Payment Service** | 8005 | Payment processing with Stripe |
| **Notification Service** | 8006 | Email/SMS notifications |

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for local development)

### Running with Docker

```bash
# Clone and navigate to project
cd ecommerce-platform

# Copy environment variables
cp .env.example .env

# Start all services
docker-compose up --build

# Access the API Gateway
# http://localhost/api/v1/
```

### Running Individual Services (Development)

```bash
# Navigate to a service
cd services/user_service

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run the service
uvicorn app.main:app --reload --port 8001
```

## 📚 API Documentation

Each service exposes its own Swagger UI:

- User Service: http://localhost:8001/docs
- Product Service: http://localhost:8002/docs
- Cart Service: http://localhost:8003/docs
- Order Service: http://localhost:8004/docs
- Payment Service: http://localhost:8005/docs
- Notification Service: http://localhost:8006/docs

## 🔧 Development

### Project Structure

```
ecommerce-platform/
├── shared/                 # Shared utilities
├── gateway/                # NGINX API Gateway
├── services/
│   ├── user_service/
│   ├── product_service/
│   ├── cart_service/
│   ├── order_service/
│   ├── payment_service/
│   └── notification_service/
├── scripts/                # Utility scripts
└── docker-compose.yml
```

### Adding Business Logic

Look for `# TODO:` comments throughout the codebase. These mark areas where you should implement your business logic.

### Testing

```bash
# Run tests for a specific service
cd services/user_service
pytest -v

# Run all tests with Docker
docker-compose -f docker-compose.test.yml up --build
```

## 📖 Learning Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 Tutorial](https://docs.sqlalchemy.org/en/20/tutorial/)
- [Docker Compose Guide](https://docs.docker.com/compose/)
- [RabbitMQ Tutorials](https://www.rabbitmq.com/tutorials)

## 📝 License

MIT License - feel free to use this for learning!
