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
    
    # Supabase Auth settings
    supabase_jwt_secret: Optional[str] = None  # JWT secret for verification

    # Supabase Storage settings
    supabase_storage_bucket: str = "geo-tiles"  # Default bucket name for COG/PMTiles files
    supabase_storage_public_url: Optional[str] = None  # Public URL for storage

    # Vercel Blob (optional, for production)
    blob_read_write_token: Optional[str] = None

    # Server
    cors_origins: List[str] = ["*"]

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

    @property
    def is_vercel(self) -> bool:
        """Check if running on Vercel."""
        return os.environ.get("VERCEL") == "1"

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production" or self.is_vercel

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
