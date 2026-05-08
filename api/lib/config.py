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

from pydantic import model_validator
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

    # Auth provider
    auth_provider: str = "supabase"  # local | supabase

    # JWT
    jwt_secret: Optional[str] = None  # local モード必須、supabase モードでは SUPABASE_JWT_SECRET にフォールバック
    jwt_audience: str = "authenticated"
    jwt_issuer: str = "geo-base"
    access_token_ttl_seconds: int = 900

    # Email backend
    email_backend: str = "console"  # null | console | smtp
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from: Optional[str] = None
    smtp_use_tls: bool = True

    # Invitation
    invitation_base_url: str = "http://localhost:3000"

    # Cookie
    cookie_samesite: str = "lax"
    cookie_secure: bool = False
    cookie_domain: Optional[str] = None

    # API key log sampling rate (0.0 - 1.0)
    api_key_log_sample_rate: float = 1.0

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
    def effective_jwt_secret(self) -> Optional[str]:
        """JWT_SECRET 優先、SUPABASE_JWT_SECRET にフォールバック（後方互換）"""
        return self.jwt_secret or self.supabase_jwt_secret

    @model_validator(mode='after')
    def validate_auth_config(self) -> 'Settings':
        if self.auth_provider == "local":
            if not self.effective_jwt_secret:
                raise ValueError(
                    "AUTH_PROVIDER=local requires JWT_SECRET (or SUPABASE_JWT_SECRET as fallback)"
                )
        elif self.auth_provider == "supabase":
            if not self.supabase_url:
                raise ValueError("AUTH_PROVIDER=supabase requires SUPABASE_URL")
            if not self.supabase_service_role_key:
                raise ValueError("AUTH_PROVIDER=supabase requires SUPABASE_SERVICE_ROLE_KEY")
            if not self.supabase_jwt_secret:
                raise ValueError("AUTH_PROVIDER=supabase requires SUPABASE_JWT_SECRET")
        else:
            raise ValueError(f"Unknown AUTH_PROVIDER: {self.auth_provider}")

        if self.email_backend == "smtp":
            if not self.smtp_host:
                raise ValueError("EMAIL_BACKEND=smtp requires SMTP_HOST")
            if not self.smtp_from:
                raise ValueError("EMAIL_BACKEND=smtp requires SMTP_FROM")
        elif self.email_backend not in ("null", "console"):
            raise ValueError(f"Unknown EMAIL_BACKEND: {self.email_backend}")

        if self.cookie_samesite == "none" and not self.cookie_secure:
            raise ValueError(
                "COOKIE_SAMESITE=none requires COOKIE_SECURE=true (browser security requirement)"
            )

        return self


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
