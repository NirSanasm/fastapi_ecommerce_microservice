"""
Base configuration management for all microservices.
Uses pydantic-settings for environment variable loading.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings as PydanticBaseSettings
from pydantic import Field


class BaseSettings(PydanticBaseSettings):
    """
    Base settings class that all service configs should inherit from.
    Automatically loads values from environment variables.
    """
    
    # Application
    app_name: str = "E-commerce Service"
    debug: bool = Field(default=False, description="Enable debug mode")
    
    # JWT Configuration
    jwt_secret_key: str = Field(
        default="your-super-secret-jwt-key-change-in-production",
        description="Secret key for JWT encoding/decoding"
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(
        default=30, 
        description="Access token expiration time in minutes"
    )
    refresh_token_expire_days: int = Field(
        default=7,
        description="Refresh token expiration time in days"
    )
    
    # RabbitMQ Configuration
    rabbitmq_host: str = Field(default="rabbitmq", alias="RABBITMQ_HOST", description="RabbitMQ host")
    rabbitmq_port: int = Field(default=5672, alias="RABBITMQ_PORT", description="RabbitMQ port")
    rabbitmq_user: str = Field(default="ecommerce", alias="RABBITMQ_USER", description="RabbitMQ username")
    rabbitmq_password: str = Field(default="ecommerce_secret", alias="RABBITMQ_PASSWORD", description="RabbitMQ password")
    
    @property
    def rabbitmq_url(self) -> str:
        """Get RabbitMQ connection URL."""
        return f"amqp://{self.rabbitmq_user}:{self.rabbitmq_password}@{self.rabbitmq_host}:{self.rabbitmq_port}/"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra fields from env


class DatabaseSettings(PydanticBaseSettings):
    """
    Database-specific settings mixin.
    Services that need a database should inherit from this.
    """
    
    db_host: str = Field(default="localhost", description="Database host")
    db_port: int = Field(default=5432, description="Database port")
    db_name: str = Field(default="ecommerce", description="Database name")
    db_user: str = Field(default="postgres", description="Database user")
    db_password: str = Field(default="postgres", description="Database password")
    db_ssl_mode: str = Field(default="require", description="SSL mode for database connection (require, disable, etc.)")
    
    @property
    def database_url(self) -> str:
        """Get async database URL for SQLAlchemy with SSL support."""
        # For cloud databases like Neon, SSL is required
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}?ssl={self.db_ssl_mode}"
    
    @property
    def sync_database_url(self) -> str:
        """Get sync database URL for Alembic migrations."""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}?sslmode={self.db_ssl_mode}"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


class RedisSettings(PydanticBaseSettings):
    """
    Redis-specific settings mixin.
    Services that need Redis should inherit from this.
    """
    
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_password: str = Field(default="", description="Redis password")
    redis_db: int = Field(default=0, description="Redis database number")
    
    @property
    def redis_url(self) -> str:
        """Get Redis connection URL."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
