"""
Product Catalog Service - Main Application Entry Point
Manages product listings, categories, and inventory.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import db_manager
from app.routers import products, categories


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    print(f"Starting {settings.app_name}...")
    await db_manager.create_tables()
    yield
    print(f"Shutting down {settings.app_name}...")
    await db_manager.close()


app = FastAPI(
    title=settings.app_name,
    description="Product catalog and inventory management service",
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

app.include_router(products.router, prefix="/api/v1/products", tags=["Products"])
app.include_router(categories.router, prefix="/api/v1/categories", tags=["Categories"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "product-service", "version": "1.0.0"}


@app.get("/")
async def root():
    return {"message": "Welcome to Product Catalog Service", "docs": "/docs"}
