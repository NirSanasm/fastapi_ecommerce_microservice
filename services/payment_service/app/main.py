"""
Payment Service - Main Application Entry Point
Handles payment processing with Stripe integration.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import db_manager
from app.routers import payments


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"Starting {settings.app_name}...")
    await db_manager.create_tables()
    yield
    print(f"Shutting down {settings.app_name}...")
    await db_manager.close()


app = FastAPI(
    title=settings.app_name,
    description="Payment processing service with Stripe",
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

app.include_router(payments.router, prefix="/api/v1/payments", tags=["Payments"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "payment-service", "version": "1.0.0"}


@app.get("/")
async def root():
    return {"message": "Welcome to Payment Service", "docs": "/docs"}
