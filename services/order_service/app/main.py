"""
Order Service - Main Application Entry Point
Processes orders, tracks status, and manages order history.
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import db_manager
from app.routers import orders
from app.consumers import payment_consumer


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    print(f"Starting {settings.app_name}...")
    await db_manager.create_tables()
    
    # Start payment event consumer as background task
    consumer_task = asyncio.create_task(payment_consumer.start())
    print("Payment event consumer started")
    
    yield
    
    # Shutdown
    print(f"Shutting down {settings.app_name}...")
    await payment_consumer.stop()
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass
    await db_manager.close()


app = FastAPI(
    title=settings.app_name,
    description="Order processing and management service",
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

app.include_router(orders.router, prefix="/api/v1/orders", tags=["Orders"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "order-service", "version": "1.0.0"}


@app.get("/")
async def root():
    return {"message": "Welcome to Order Service", "docs": "/docs"}
