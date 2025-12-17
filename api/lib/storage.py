"""
Supabase Storage integration for geo-base API.

Features:
- COG file upload to Supabase Storage
- Presigned URL generation
- File validation and metadata extraction
"""

import os
import hashlib
import logging
from typing import Optional, BinaryIO
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urljoin

import httpx

from lib.config import get_settings

# Logger
logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

# Supported file extensions for COG uploads
COG_EXTENSIONS = {".tif", ".tiff", ".geotiff"}

# Maximum file size (500MB)
MAX_FILE_SIZE = 500 * 1024 * 1024

# Default bucket name
DEFAULT_BUCKET = "geo-tiles"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class UploadResult:
    """Result of a file upload operation."""
    success: bool
    url: Optional[str] = None
    path: Optional[str] = None
    size: Optional[int] = None
    content_type: Optional[str] = None
    error: Optional[str] = None


@dataclass
class COGMetadata:
    """Metadata extracted from a COG file."""
    bounds: Optional[list[float]] = None
    center: Optional[list[float]] = None
    crs: Optional[str] = None
    band_count: Optional[int] = None
    band_descriptions: Optional[list[str]] = None
    width: Optional[int] = None
    height: Optional[int] = None
    min_zoom: Optional[int] = None
    max_zoom: Optional[int] = None
    statistics: Optional[dict] = None


# =============================================================================
# Supabase Storage Client
# =============================================================================


class SupabaseStorageClient:
    """
    Client for Supabase Storage operations.
    
    Uses the Supabase REST API for file uploads and management.
    """
    
    def __init__(
        self,
        supabase_url: Optional[str] = None,
        service_role_key: Optional[str] = None,
        bucket: str = DEFAULT_BUCKET,
    ):
        """
        Initialize the storage client.
        
        Args:
            supabase_url: Supabase project URL
            service_role_key: Supabase service role key (for server-side operations)
            bucket: Storage bucket name
        """
        settings = get_settings()
        
        self.supabase_url = supabase_url or settings.supabase_url
        self.service_role_key = service_role_key or settings.supabase_service_role_key
        self.bucket = bucket or settings.supabase_storage_bucket or DEFAULT_BUCKET
        
        if not self.supabase_url:
            raise ValueError("Supabase URL is required")
        
        # Build storage API base URL
        self.storage_url = f"{self.supabase_url}/storage/v1"
        
        # HTTP client with auth headers
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def _headers(self) -> dict:
        """Get headers for API requests."""
        headers = {
            "Content-Type": "application/json",
        }
        if self.service_role_key:
            headers["Authorization"] = f"Bearer {self.service_role_key}"
            headers["apikey"] = self.service_role_key
        return headers
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=60.0,
                headers=self._headers,
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    def _generate_file_path(
        self,
        filename: str,
        tileset_id: str,
        user_id: Optional[str] = None,
    ) -> str:
        """
        Generate a unique file path for storage.
        
        Path format: {user_id}/{tileset_id}/{timestamp}_{filename}
        """
        # Sanitize filename
        safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-")
        if not safe_filename:
            safe_filename = "cog.tif"
        
        # Generate timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        # Build path
        if user_id:
            return f"{user_id}/{tileset_id}/{timestamp}_{safe_filename}"
        else:
            return f"public/{tileset_id}/{timestamp}_{safe_filename}"
    
    def get_public_url(self, path: str) -> str:
        """
        Get the public URL for a file.
        
        Args:
            path: File path in the bucket
            
        Returns:
            Public URL for the file
        """
        return f"{self.storage_url}/object/public/{self.bucket}/{path}"
    
    async def upload_file(
        self,
        file: BinaryIO,
        filename: str,
        tileset_id: str,
        user_id: Optional[str] = None,
        content_type: str = "image/tiff",
    ) -> UploadResult:
        """
        Upload a file to Supabase Storage.
        
        Args:
            file: File-like object to upload
            filename: Original filename
            tileset_id: Parent tileset ID
            user_id: User ID (for path organization)
            content_type: MIME type of the file
            
        Returns:
            UploadResult with URL or error
        """
        try:
            # Generate storage path
            path = self._generate_file_path(filename, tileset_id, user_id)
            
            # Read file content
            file.seek(0)
            content = file.read()
            file_size = len(content)
            
            # Check file size
            if file_size > MAX_FILE_SIZE:
                return UploadResult(
                    success=False,
                    error=f"File size ({file_size} bytes) exceeds maximum ({MAX_FILE_SIZE} bytes)"
                )
            
            # Upload using Supabase Storage API
            client = await self._get_client()
            
            upload_url = f"{self.storage_url}/object/{self.bucket}/{path}"
            
            response = await client.post(
                upload_url,
                content=content,
                headers={
                    **self._headers,
                    "Content-Type": content_type,
                    "x-upsert": "true",  # Overwrite if exists
                },
            )
            
            if response.status_code in (200, 201):
                public_url = self.get_public_url(path)
                logger.info(f"Uploaded file to {path}, public URL: {public_url}")
                
                return UploadResult(
                    success=True,
                    url=public_url,
                    path=path,
                    size=file_size,
                    content_type=content_type,
                )
            else:
                error_msg = f"Upload failed: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return UploadResult(success=False, error=error_msg)
                
        except Exception as e:
            error_msg = f"Upload error: {str(e)}"
            logger.exception(error_msg)
            return UploadResult(success=False, error=error_msg)
    
    async def delete_file(self, path: str) -> bool:
        """
        Delete a file from storage.
        
        Args:
            path: File path in the bucket
            
        Returns:
            True if deleted successfully
        """
        try:
            client = await self._get_client()
            
            delete_url = f"{self.storage_url}/object/{self.bucket}/{path}"
            
            response = await client.delete(delete_url)
            
            if response.status_code in (200, 204):
                logger.info(f"Deleted file: {path}")
                return True
            else:
                logger.error(f"Delete failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.exception(f"Delete error: {e}")
            return False
    
    async def file_exists(self, path: str) -> bool:
        """
        Check if a file exists in storage.
        
        Args:
            path: File path in the bucket
            
        Returns:
            True if file exists
        """
        try:
            client = await self._get_client()
            
            # Try HEAD request
            url = f"{self.storage_url}/object/{self.bucket}/{path}"
            response = await client.head(url)
            
            return response.status_code == 200
            
        except Exception:
            return False


# =============================================================================
# COG Metadata Extraction
# =============================================================================


def extract_cog_metadata(cog_url: str) -> COGMetadata:
    """
    Extract metadata from a COG file.
    
    Args:
        cog_url: URL or path to the COG file
        
    Returns:
        COGMetadata object with extracted information
    """
    try:
        # Import rio-tiler (may not be available)
        from lib.raster_tiles import get_cog_info, get_cog_statistics, is_rasterio_available
        
        if not is_rasterio_available():
            logger.warning("rio-tiler not available, returning empty metadata")
            return COGMetadata()
        
        # Get COG info
        info = get_cog_info(cog_url)
        
        # Build metadata
        metadata = COGMetadata(
            bounds=info.get("bounds"),
            crs=info.get("crs"),
            band_count=info.get("count"),
            band_descriptions=info.get("band_descriptions"),
            width=info.get("width"),
            height=info.get("height"),
            min_zoom=info.get("minzoom"),
            max_zoom=info.get("maxzoom"),
        )
        
        # Calculate center from bounds
        if metadata.bounds and len(metadata.bounds) == 4:
            west, south, east, north = metadata.bounds
            center_lon = (west + east) / 2
            center_lat = (south + north) / 2
            center_zoom = metadata.min_zoom or 10
            metadata.center = [center_lon, center_lat, center_zoom]
        
        # Get statistics
        try:
            stats = get_cog_statistics(cog_url)
            metadata.statistics = stats
        except Exception as e:
            logger.warning(f"Could not get COG statistics: {e}")
        
        return metadata
        
    except Exception as e:
        logger.exception(f"Error extracting COG metadata: {e}")
        return COGMetadata()


# =============================================================================
# Validation Functions
# =============================================================================


def validate_cog_file(filename: str, file_size: int) -> tuple[bool, Optional[str]]:
    """
    Validate a COG file before upload.
    
    Args:
        filename: Original filename
        file_size: File size in bytes
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check file extension
    ext = os.path.splitext(filename.lower())[1]
    if ext not in COG_EXTENSIONS:
        return False, f"Invalid file type. Allowed: {', '.join(COG_EXTENSIONS)}"
    
    # Check file size
    if file_size > MAX_FILE_SIZE:
        max_mb = MAX_FILE_SIZE / (1024 * 1024)
        return False, f"File size exceeds maximum ({max_mb:.0f} MB)"
    
    if file_size == 0:
        return False, "File is empty"
    
    return True, None


def is_cloud_optimized(file_bytes: bytes) -> bool:
    """
    Check if a GeoTIFF file is Cloud Optimized.
    
    This is a basic check that looks for COG-specific internal tiling.
    
    Args:
        file_bytes: First few KB of the file
        
    Returns:
        True if the file appears to be a COG
    """
    try:
        # COGs typically have BigTIFF or regular TIFF magic bytes
        # with internal tiling enabled
        
        # Check TIFF magic bytes
        if len(file_bytes) < 8:
            return False
        
        # Little-endian TIFF: 49 49 2A 00
        # Big-endian TIFF: 4D 4D 00 2A
        # BigTIFF LE: 49 49 2B 00
        # BigTIFF BE: 4D 4D 00 2B
        magic = file_bytes[:4]
        
        is_tiff = magic in (b'II\x2a\x00', b'MM\x00\x2a', b'II\x2b\x00', b'MM\x00\x2b')
        
        if not is_tiff:
            return False
        
        # For a more thorough check, we'd need to parse TIFF tags
        # For now, we assume any TIFF with correct magic is potentially a COG
        return True
        
    except Exception:
        return False


# =============================================================================
# Singleton Storage Client
# =============================================================================


_storage_client: Optional[SupabaseStorageClient] = None


def get_storage_client() -> SupabaseStorageClient:
    """Get or create the singleton storage client."""
    global _storage_client
    
    if _storage_client is None:
        _storage_client = SupabaseStorageClient()
    
    return _storage_client


async def close_storage_client():
    """Close the storage client."""
    global _storage_client
    
    if _storage_client:
        await _storage_client.close()
        _storage_client = None
