"""
Notification Service - Main Application Entry Point
Sends email and SMS notifications for various events.
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import notifications
from app.events import event_consumer


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"Starting {settings.app_name}...")
    
    # Start RabbitMQ consumer as background task
    consumer_task = asyncio.create_task(event_consumer.start())
    print("RabbitMQ event consumer started")
    
    yield
    
    # Shutdown
    print(f"Shutting down {settings.app_name}...")
    await event_consumer.stop()
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title=settings.app_name,
    description="Email and SMS notification service",
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

app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["Notifications"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "notification-service", "version": "1.0.0"}


@app.get("/")
async def root():
    return {"message": "Welcome to Notification Service", "docs": "/docs"}
