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

    # S3 互換 storage (COG/PMTiles のアップロード先)
    # 既定で Fly Tigris 互換: https://fly.io/docs/tigris/
    # AWS S3 / Cloudflare R2 等を使う場合は s3_endpoint_url / s3_region を上書き。
    # アクセスキーは標準の AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY 環境変数で渡す
    # （boto3 のデフォルト credential resolver に乗る）。
    s3_endpoint_url: str = "https://fly.storage.tigris.dev"
    s3_region: str = "auto"
    s3_bucket: str = "geo-base-tiles"
    # public な配信に使う base URL（任意）。設定された場合は upload 後の url を
    # この prefix で組み立てる。Tigris の場合は通常 endpoint URL の bucket 配下が
    # public 化されるが、別途 CDN を挟む構成では指定が必要。
    s3_public_base_url: Optional[str] = None

    # Auth provider
    auth_provider: str = "local"  # 現状 local のみ。Supabase Auth は #72 で廃止済み

    # JWT
    jwt_secret: Optional[str] = None  # local モードでは必須
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

    # API key rate limit backend (Issue #56)
    # "db": 既存実装。`api_key_rate_limits` テーブルに INSERT/UPDATE で集計。
    # "redis": Redis ベース実装。INCR で per-minute / per-day カウンタを管理。
    # Redis 失敗時は fail-open（warn ログ + リクエスト通過）。
    # 既定は "db" — backward compatibility のため。本番で "redis" に切り替えるには
    # `fly secrets set RATE_LIMIT_BACKEND=redis` を実行する。
    rate_limit_backend: str = "db"

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
    def s3_storage_base_url(self) -> str:
        """S3 互換 storage の public 配信用 base URL。

        s3_public_base_url が明示設定されていればそれを返す。未設定の場合は
        endpoint_url / bucket から組み立てる（Tigris などは bucket public 化で
        `<endpoint_url>/<bucket>` が公開 URL になる）。
        """
        if self.s3_public_base_url:
            return self.s3_public_base_url.rstrip("/")
        return f"{self.s3_endpoint_url.rstrip('/')}/{self.s3_bucket}"

    @property
    def effective_jwt_secret(self) -> Optional[str]:
        """JWT 検証に使う実効的な secret。

        以前は SUPABASE_JWT_SECRET をフォールバックしていたが、Supabase Auth
        プロバイダ廃止 (#72) により単純に JWT_SECRET を返すだけになった。
        既存の呼び出し箇所を変えないようプロパティ自体は残している。
        """
        return self.jwt_secret

    @model_validator(mode='after')
    def validate_auth_config(self) -> 'Settings':
        if self.auth_provider == "local":
            if not self.jwt_secret:
                raise ValueError("AUTH_PROVIDER=local requires JWT_SECRET")
        else:
            raise ValueError(
                f"Unknown AUTH_PROVIDER: {self.auth_provider} "
                "(only 'local' is supported)"
            )

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
