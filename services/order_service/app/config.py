"""Order Service Configuration

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
    """Order Service specific settings."""
    
    app_name: str = "Order Service"
    
    db_host: str = Field(default="localhost", alias="ORDER_DB_HOST")
    db_port: int = Field(default=5432, alias="ORDER_DB_PORT")
    db_name: str = Field(default="order_service", alias="ORDER_DB_NAME")
    db_user: str = Field(default="ecommerce", alias="ORDER_DB_USER")
    db_password: str = Field(default="ecommerce_secret", alias="ORDER_DB_PASSWORD")
    
    # JWT settings
    jwt_secret_key: str = Field(
        default="your-super-secret-jwt-key-change-in-production",
        alias="JWT_SECRET_KEY"
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    
    # Other services
    cart_service_url: str = Field(default="http://cart_service:8003", alias="CART_SERVICE_URL")
    product_service_url: str = Field(default="http://product_service:8002", alias="PRODUCT_SERVICE_URL")
    payment_service_url: str = Field(default="http://payment_service:8005", alias="PAYMENT_SERVICE_URL")
    notification_service_url: str = Field(default="http://notification_service:8006", alias="NOTIFICATION_SERVICE_URL")
    
    # Note: RabbitMQ URL is provided by BaseSettings.rabbitmq_url property
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
        populate_by_name = True


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
