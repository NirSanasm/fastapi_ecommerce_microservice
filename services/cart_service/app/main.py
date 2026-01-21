"""
Shopping Cart Service - Main Application Entry Point
Manages user shopping carts using Redis for fast access.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.redis_client import redis_client
from app.routers import cart


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    print(f"Starting {settings.app_name}...")
    await redis_client.connect()
    yield
    print(f"Shutting down {settings.app_name}...")
    await redis_client.close()


app = FastAPI(
    title=settings.app_name,
    description="Shopping cart management service with Redis",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cart.router, prefix="/api/v1/cart", tags=["Cart"])


@app.get("/health")
async def health_check():
    redis_status = "healthy" if redis_client.is_connected else "unhealthy"
    return {
        "status": "healthy",
        "service": "cart-service",
        "version": "1.0.0",
        "dependencies": {"redis": redis_status},
    }


@app.get("/")
async def root():
    return {"message": "Welcome to Cart Service", "docs": "/docs"}
