"""
User Service - Main Application Entry Point
Handles user registration, authentication, and profile management.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import db_manager
from app.routers import auth, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown events."""
    # Startup
    print(f"Starting {settings.app_name}...")
    await db_manager.create_tables()
    yield
    # Shutdown
    print(f"Shutting down {settings.app_name}...")
    await db_manager.close()


app = FastAPI(
    title=settings.app_name,
    description="User authentication and profile management service",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "user-service",
        "version": "1.0.0",
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Welcome to User Service", "docs": "/docs"}
