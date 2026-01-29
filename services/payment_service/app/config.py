"""Payment Service Configuration

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
    """Payment Service specific settings."""
    
    app_name: str = "Payment Service"
    
    db_host: str = Field(default="localhost", alias="PAYMENT_DB_HOST")
    db_port: int = Field(default=5432, alias="PAYMENT_DB_PORT")
    db_name: str = Field(default="payment_service", alias="PAYMENT_DB_NAME")
    db_user: str = Field(default="ecommerce", alias="PAYMENT_DB_USER")
    db_password: str = Field(default="ecommerce_secret", alias="PAYMENT_DB_PASSWORD")
    
    # JWT settings
    jwt_secret_key: str = Field(default="your-super-secret-jwt-key", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    
    # Stripe
    stripe_secret_key: str = Field(default="sk_test_xxx", alias="STRIPE_SECRET_KEY")
    stripe_webhook_secret: str = Field(default="whsec_xxx", alias="STRIPE_WEBHOOK_SECRET")
    
    # Order service
    order_service_url: str = Field(default="http://order_service:8004", alias="ORDER_SERVICE_URL")
    
    # RabbitMQ for event publishing
    rabbitmq_url: str = Field(default="amqp://ecommerce:ecommerce_secret@rabbitmq:5672/", alias="RABBITMQ_URL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
        populate_by_name = True


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
