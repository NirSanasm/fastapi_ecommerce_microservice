"""Cart Service Configuration

Environment variables are loaded in order of priority:
1. OS environment variables (from Docker, Kubernetes, or shell)
2. .env file (for local development)
"""

import sys
from pathlib import Path
from functools import lru_cache

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from pydantic import Field
from shared.config import BaseSettings, RedisSettings


class Settings(BaseSettings, RedisSettings):
    """Cart Service specific settings."""
    
    app_name: str = "Cart Service"
    
    # Cart settings
    cart_ttl_seconds: int = Field(
        default=604800,  # 7 days
        description="Cart expiration time in seconds"
    )
    
    # Product service URL for price validation
    product_service_url: str = Field(
        default="http://product_service:8002",
        alias="PRODUCT_SERVICE_URL"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
        populate_by_name = True


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
