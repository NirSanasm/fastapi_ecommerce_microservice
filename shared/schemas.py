"""
Common Pydantic schemas used across all microservices.
"""

from typing import TypeVar, Generic, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


# Generic type for response data
T = TypeVar("T")


class ResponseModel(BaseModel, Generic[T]):
    """
    Standard API response wrapper.
    
    Usage:
        @router.get("/items", response_model=ResponseModel[List[ItemSchema]])
        async def get_items():
            items = await get_all_items()
            return ResponseModel(success=True, data=items)
    """
    success: bool = True
    message: str = "Success"
    data: Optional[T] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Success",
                "data": {}
            }
        }


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Paginated response wrapper for list endpoints.
    """
    items: list[T]
    total: int
    page: int
    size: int
    pages: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "items": [],
                "total": 100,
                "page": 1,
                "size": 10,
                "pages": 10
            }
        }


class PaginationParams(BaseModel):
    """
    Pagination query parameters.
    
    Usage:
        @router.get("/items")
        async def get_items(pagination: PaginationParams = Depends()):
            skip = (pagination.page - 1) * pagination.size
            ...
    """
    page: int = Field(default=1, ge=1, description="Page number")
    size: int = Field(default=10, ge=1, le=100, description="Items per page")
    
    @property
    def skip(self) -> int:
        """Calculate offset for database query."""
        return (self.page - 1) * self.size
    
    @property
    def limit(self) -> int:
        """Get limit for database query."""
        return self.size


class ErrorResponse(BaseModel):
    """
    Standard error response.
    """
    success: bool = False
    message: str
    error_code: Optional[str] = None
    details: Optional[dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "message": "An error occurred",
                "error_code": "VALIDATION_ERROR",
                "details": {"field": "email", "reason": "Invalid format"}
            }
        }


class HealthResponse(BaseModel):
    """
    Health check response.
    """
    status: str = "healthy"
    service: str
    version: str = "1.0.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    dependencies: Optional[dict[str, str]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "service": "user-service",
                "version": "1.0.0",
                "timestamp": "2024-01-15T12:00:00Z",
                "dependencies": {
                    "database": "healthy",
                    "redis": "healthy"
                }
            }
        }


class OrderStatus(str, Enum):
    """Order status enum used across services."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentStatus(str, Enum):
    """Payment status enum used across services."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class UserRole(str, Enum):
    """User roles enum."""
    CUSTOMER = "customer"
    ADMIN = "admin"
    SELLER = "seller"


# Base schema for models with timestamps
class TimestampMixin(BaseModel):
    """Mixin for models with created_at and updated_at fields."""
    created_at: datetime
    updated_at: Optional[datetime] = None


class IDMixin(BaseModel):
    """Mixin for models with ID field."""
    id: int
