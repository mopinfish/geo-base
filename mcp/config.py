"""
Configuration management for geo-base MCP Server.

Provides type-safe settings using Pydantic BaseSettings with
environment variable support and .env file loading.
"""

import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """MCP Server settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Tile Server API configuration
    tile_server_url: str = Field(
        default="http://localhost:3000",
        description="Base URL of the geo-base tile server API",
    )

    # Authentication (optional - for accessing private tilesets)
    api_token: str | None = Field(
        default=None,
        description="JWT token for authenticated API requests",
    )

    # MCP Server configuration
    server_name: str = Field(
        default="geo-base",
        description="MCP server name",
    )
    server_version: str = Field(
        default="0.2.5",
        description="MCP server version",
    )

    # HTTP client configuration
    http_timeout: float = Field(
        default=30.0,
        description="HTTP request timeout in seconds",
    )

    # Environment
    environment: str = Field(
        default="development",
        description="Environment (development/production)",
    )

    # Debug mode
    debug: bool = Field(
        default=False,
        description="Enable debug mode",
    )

    # Logging configuration
    log_level: str = Field(
        default="INFO",
        description="Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
