"""
User Service Configuration

Environment variables are loaded in order of priority:
1. OS environment variables (from Docker, Kubernetes, or shell)
2. .env file (for local development)
"""

import sys
from pathlib import Path
from functools import lru_cache

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from pydantic import Field
from shared.config import BaseSettings, DatabaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings, DatabaseSettings):
    """User Service specific settings."""
    
    app_name: str = "User Service"
    
    # Override database settings with user service specific env vars
    db_host: str = Field(default="localhost", alias="USER_DB_HOST")
    db_port: int = Field(default=5432, alias="USER_DB_PORT")
    db_name: str = Field(default="user_service", alias="USER_DB_NAME")
    db_user: str = Field(default="ecommerce", alias="USER_DB_USER")
    db_password: str = Field(default="ecommerce_secret", alias="USER_DB_PASSWORD")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )
@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
