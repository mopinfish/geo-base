"""
Configuration settings for geo-base API.
"""

import os
from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Environment
    environment: str = "development"
    debug: bool = True

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/geo_base"

    # Supabase (optional, for production)
    supabase_url: Optional[str] = None
    supabase_anon_key: Optional[str] = None
    supabase_service_role_key: Optional[str] = None

    # Vercel Blob (optional, for production)
    blob_read_write_token: Optional[str] = None

    # Server
    cors_origins: List[str] = ["*"]

    # Tile settings
    default_tile_cache_ttl: int = 86400  # 24 hours

    @property
    def is_vercel(self) -> bool:
        """Check if running on Vercel."""
        return os.environ.get("VERCEL") == "1"

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production" or self.is_vercel


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
