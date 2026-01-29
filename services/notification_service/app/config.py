"""Notification Service Configuration

Environment variables are loaded in order of priority:
1. OS environment variables (from Docker, Kubernetes, or shell)
2. .env file (for local development)
"""

import sys
from pathlib import Path
from functools import lru_cache

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from pydantic import Field
from shared.config import BaseSettings


class Settings(BaseSettings):
    """Notification Service specific settings."""
    
    app_name: str = "Notification Service"
    
    # Brevo (formerly Sendinblue)
    brevo_api_key: str = Field(default="", alias="BREVO_API_KEY")
    brevo_from_email: str = Field(default="noreply@example.com", alias="BREVO_FROM_EMAIL")
    brevo_from_name: str = Field(default="E-Commerce Platform", alias="BREVO_FROM_NAME")
    
    # RabbitMQ for event consumption
    rabbitmq_url: str = Field(default="amqp://ecommerce:ecommerce_secret@rabbitmq:5672/", alias="RABBITMQ_URL")
    
    # User service for fetching user details
    user_service_url: str = Field(default="http://user_service:8001", alias="USER_SERVICE_URL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
        populate_by_name = True


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
