"""Notification Service Configuration"""

import sys
from pathlib import Path
from functools import lru_cache

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from pydantic import Field
from shared.config import BaseSettings

BASE_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_name: str = "Notification Service"
    
    # Brevo (formerly Sendinblue)
    brevo_api_key: str = Field(default="", alias="BREVO_API_KEY")
    brevo_from_email: str = Field(default="noreply@example.com", alias="BREVO_FROM_EMAIL")
    brevo_from_name: str = Field(default="E-Commerce Platform", alias="BREVO_FROM_NAME")
    
    class Config:
        env_file = BASE_DIR / ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
