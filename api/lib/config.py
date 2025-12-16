"""
Configuration settings for geo-base API.

Supports multiple deployment environments:
- Local development
- Vercel (serverless)
- Fly.io (containerized)
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
    log_level: str = "INFO"

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/geo_base"

    # Supabase (optional, for production)
    supabase_url: Optional[str] = None
    supabase_anon_key: Optional[str] = None
    supabase_service_role_key: Optional[str] = None
    
    # Supabase Auth settings
    supabase_jwt_secret: Optional[str] = None  # JWT secret for verification

    # Supabase Storage settings
    supabase_storage_bucket: str = "geo-tiles"  # Default bucket name for COG/PMTiles files
    supabase_storage_public_url: Optional[str] = None  # Public URL for storage

    # Vercel Blob (optional, for production)
    blob_read_write_token: Optional[str] = None

    # Server
    cors_origins: List[str] = ["*"]
    port: int = 8080  # Default port for Fly.io

    # Tile settings
    default_tile_cache_ttl: int = 86400  # 24 hours

    # Raster tile settings
    raster_default_scale_min: float = 0
    raster_default_scale_max: float = 3000
    raster_default_format: str = "png"
    raster_max_preview_size: int = 1024
    raster_tile_size: int = 256
    
    # PMTiles settings
    pmtiles_default_cache_ttl: int = 86400  # 24 hours

    # Connection pool settings (for Fly.io)
    db_pool_min_size: int = 2
    db_pool_max_size: int = 20

    @property
    def is_vercel(self) -> bool:
        """Check if running on Vercel."""
        return os.environ.get("VERCEL") == "1"

    @property
    def is_fly(self) -> bool:
        """Check if running on Fly.io."""
        return os.environ.get("FLY_APP_NAME") is not None

    @property
    def is_serverless(self) -> bool:
        """Check if running in a serverless environment (Vercel, Lambda, etc.)."""
        return (
            self.is_vercel 
            or "AWS_LAMBDA_FUNCTION_NAME" in os.environ
        )

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return (
            self.environment == "production" 
            or self.is_vercel 
            or self.is_fly
        )

    @property
    def deployment_platform(self) -> str:
        """Get the current deployment platform name."""
        if self.is_vercel:
            return "vercel"
        elif self.is_fly:
            return "fly"
        elif "AWS_LAMBDA_FUNCTION_NAME" in os.environ:
            return "lambda"
        else:
            return "local"

    @property
    def supabase_storage_base_url(self) -> Optional[str]:
        """Get Supabase Storage base URL for public access."""
        if self.supabase_storage_public_url:
            return self.supabase_storage_public_url
        if self.supabase_url:
            # Default Supabase Storage URL pattern
            return f"{self.supabase_url}/storage/v1/object/public/{self.supabase_storage_bucket}"
        return None
    
    @property
    def jwt_secret(self) -> Optional[str]:
        """Get JWT secret for token verification."""
        # Supabase JWT secret takes precedence
        if self.supabase_jwt_secret:
            return self.supabase_jwt_secret
        return None


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
