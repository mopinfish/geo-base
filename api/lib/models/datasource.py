"""
Pydantic models for Datasource operations.
"""

from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class DatasourceType(str, Enum):
    """Datasource type enum."""
    pmtiles = "pmtiles"
    cog = "cog"


class StorageProvider(str, Enum):
    """Storage provider enum.

    `s3` は S3 API 互換 storage の総称（既定: Fly Tigris、AWS S3 / R2 / MinIO 等
    も同じ enum で扱う）。エンドポイント URL の差異は `lib.config.Settings.s3_*`
    で吸収する。Issue #72 で旧 `supabase` provider は廃止。
    """

    s3 = "s3"
    http = "http"


class DatasourceCreate(BaseModel):
    """Request model for creating a datasource."""
    tileset_id: str = Field(..., description="Parent tileset UUID")
    type: DatasourceType = Field(..., description="Datasource type (pmtiles or cog)")
    url: str = Field(..., min_length=1, description="URL to the data source")
    storage_provider: StorageProvider = Field(StorageProvider.http, description="Storage provider")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class DatasourceUpdate(BaseModel):
    """Request model for updating a datasource."""
    url: Optional[str] = Field(None, min_length=1, description="URL to the data source")
    storage_provider: Optional[StorageProvider] = Field(None, description="Storage provider")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
