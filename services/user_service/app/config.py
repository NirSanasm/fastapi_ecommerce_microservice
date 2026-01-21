"""
User Service Configuration
"""

import sys
from pathlib import Path
from functools import lru_cache

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from pydantic import Field
from shared.config import BaseSettings, DatabaseSettings


class Settings(BaseSettings, DatabaseSettings):
    """User Service specific settings."""
    
    app_name: str = "User Service"
    
    # Override database settings with user service specific env vars
    db_host: str = Field(default="localhost", alias="USER_DB_HOST")
    db_port: int = Field(default=5432, alias="USER_DB_PORT")
    db_name: str = Field(default="user_service", alias="USER_DB_NAME")
    db_user: str = Field(default="ecommerce", alias="USER_DB_USER")
    db_password: str = Field(default="ecommerce_secret", alias="USER_DB_PASSWORD")
    
    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
