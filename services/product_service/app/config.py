"""Product Service Configuration

Environment variables are loaded in order of priority:
1. OS environment variables (from Docker, Kubernetes, or shell)
2. .env file (for local development)
"""

import sys
from pathlib import Path
from functools import lru_cache

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from pydantic import Field
from shared.config import BaseSettings, DatabaseSettings


class Settings(BaseSettings, DatabaseSettings):
    """Product Service specific settings."""
    
    app_name: str = "Product Service"
    
    db_host: str = Field(default="localhost", alias="PRODUCT_DB_HOST")
    db_port: int = Field(default=5432, alias="PRODUCT_DB_PORT")
    db_name: str = Field(default="product_service", alias="PRODUCT_DB_NAME")
    db_user: str = Field(default="ecommerce", alias="PRODUCT_DB_USER")
    db_password: str = Field(default="ecommerce_secret", alias="PRODUCT_DB_PASSWORD")
    
    # RabbitMQ for event publishing
    rabbitmq_url: str = Field(default="amqp://ecommerce:ecommerce_secret@rabbitmq:5672/", alias="RABBITMQ_URL")
    
    # Inventory thresholds
    low_stock_threshold: int = Field(default=10, alias="LOW_STOCK_THRESHOLD")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
        populate_by_name = True


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
