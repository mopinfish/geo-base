"""
Pydantic models for Datasource operations.
"""

from typing import Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class DatasourceType(str, Enum):
    """Datasource type enum."""
    pmtiles = "pmtiles"
    cog = "cog"


class StorageProvider(str, Enum):
    """Storage provider enum."""
    supabase = "supabase"
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
