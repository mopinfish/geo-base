"""
S3 互換ストレージ統合（COG / PMTiles のアップロード backend）。

既定で Fly Tigris (https://fly.storage.tigris.dev) を想定するが、boto3 の
S3 client を使うので AWS S3 / Cloudflare R2 / MinIO 等 S3 API 互換のサービスを
endpoint URL の差し替えで利用できる（`AWS_ENDPOINT_URL_S3` env または
`settings.s3_endpoint_url` で設定）。

Issue #72 で旧 SupabaseStorageClient から本実装に移行 (PR #88)。

Features:
- COG ファイルの S3 互換 storage へのアップロード
- 公開 URL 生成（bucket public 化前提）
- COG メタデータ抽出（rio-tiler 経由）
- ファイル形式 / サイズ検証
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import BinaryIO, Optional

import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import BotoCoreError, ClientError

from lib.config import get_settings

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

# Supported file extensions for COG uploads
COG_EXTENSIONS = {".tif", ".tiff", ".geotiff"}

# Maximum file size (500MB)
MAX_FILE_SIZE = 500 * 1024 * 1024


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
# S3 互換 Storage Client
# =============================================================================


class S3StorageClient:
    """S3 API 互換 storage（既定: Fly Tigris）への薄いラッパ。

    boto3 を sync で呼ぶ。FastAPI handler で呼ぶ場合は `def` ハンドラ経由で
    threadpool 実行に乗せること（issue #64 Option A と同じ方針）。

    認証情報は標準の AWS credential resolver（環境変数 / IAM role / ~/.aws）
    に委ねる。本リポジトリの想定では以下の env を `fly secrets set` する:

    - AWS_ACCESS_KEY_ID            (boto3 が直接読む)
    - AWS_SECRET_ACCESS_KEY        (boto3 が直接読む)
    - S3_ENDPOINT_URL              (`lib.config.Settings.s3_endpoint_url`、既定値 Tigris)
    - S3_REGION                    (`lib.config.Settings.s3_region`、既定 `auto`)
    - S3_BUCKET                    (`lib.config.Settings.s3_bucket`)
    - S3_PUBLIC_BASE_URL           (任意。設定なしなら endpoint+bucket を使う)
    """

    def __init__(
        self,
        bucket: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        region: Optional[str] = None,
        public_base_url: Optional[str] = None,
    ):
        settings = get_settings()
        self.bucket = bucket or settings.s3_bucket
        self.endpoint_url = endpoint_url or settings.s3_endpoint_url
        self.region = region or settings.s3_region
        self._public_base_url = public_base_url or settings.s3_public_base_url

        # boto3 client は遅延初期化（test 等で endpoint 差し替え時に再生成しやすい）
        self._client = None

    # -- internal --

    def _get_client(self):
        if self._client is None:
            self._client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,
                region_name=self.region,
                # Tigris などは path-style URL を要求するケースがある。virtual-hosted
                # も path-style も受け付けるので、互換性最大化のため virtual を既定に。
                config=BotoConfig(
                    signature_version="s3v4",
                    s3={"addressing_style": "virtual"},
                    retries={"max_attempts": 3, "mode": "standard"},
                ),
            )
        return self._client

    # -- public API --

    def get_public_url(self, path: str) -> str:
        """指定 path の public URL を返す（bucket が public 化されている前提）。"""
        if self._public_base_url:
            base = self._public_base_url.rstrip("/")
        else:
            base = f"{self.endpoint_url.rstrip('/')}/{self.bucket}"
        return f"{base}/{path.lstrip('/')}"

    def upload_file(
        self,
        path: str,
        content: bytes,
        content_type: str = "application/octet-stream",
    ) -> Optional[str]:
        """`content` を `path` に PUT する。成功時は public URL を返し、失敗時は None。

        この sync インターフェースは `api/lib/routers/datasources.py` の COG
        アップロード経路と整合させたもの。Bytes をオンメモリで扱う前提（最大
        MAX_FILE_SIZE = 500MB）なので大ファイル multipart upload は別途。
        """
        if len(content) > MAX_FILE_SIZE:
            logger.error(
                f"upload_file: content size {len(content)} exceeds MAX_FILE_SIZE {MAX_FILE_SIZE}"
            )
            return None

        try:
            client = self._get_client()
            client.put_object(
                Bucket=self.bucket,
                Key=path,
                Body=content,
                ContentType=content_type,
            )
        except (ClientError, BotoCoreError) as e:
            logger.exception(f"S3 put_object failed: {e}")
            return None

        url = self.get_public_url(path)
        logger.info(f"Uploaded {len(content)} bytes to s3://{self.bucket}/{path} ({url})")
        return url

    def upload_fileobj(
        self,
        file: BinaryIO,
        filename: str,
        tileset_id: str,
        user_id: Optional[str] = None,
        content_type: str = "image/tiff",
    ) -> UploadResult:
        """File-like を path 自動生成で upload する版（旧 API 互換）。

        path は `<user_id|public>/<tileset_id>/<timestamp>_<safe_filename>`。
        """
        path = self._generate_file_path(filename, tileset_id, user_id)

        file.seek(0)
        content = file.read()
        url = self.upload_file(path, content, content_type)
        if url is None:
            return UploadResult(success=False, error="upload failed")
        return UploadResult(
            success=True,
            url=url,
            path=path,
            size=len(content),
            content_type=content_type,
        )

    def delete_file(self, path: str) -> bool:
        try:
            self._get_client().delete_object(Bucket=self.bucket, Key=path)
            return True
        except (ClientError, BotoCoreError) as e:
            logger.exception(f"S3 delete_object failed: {e}")
            return False

    def file_exists(self, path: str) -> bool:
        try:
            self._get_client().head_object(Bucket=self.bucket, Key=path)
            return True
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code")
            if code in ("404", "NoSuchKey", "NotFound"):
                return False
            logger.exception(f"S3 head_object failed: {e}")
            return False
        except BotoCoreError as e:
            logger.exception(f"S3 head_object error: {e}")
            return False

    # -- helpers --

    def _generate_file_path(
        self,
        filename: str,
        tileset_id: str,
        user_id: Optional[str] = None,
    ) -> str:
        safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-")
        if not safe_filename:
            safe_filename = "cog.tif"
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        prefix = user_id if user_id else "public"
        return f"{prefix}/{tileset_id}/{timestamp}_{safe_filename}"


# =============================================================================
# COG Metadata Extraction
# =============================================================================


def extract_cog_metadata(cog_url: str) -> COGMetadata:
    """COG ファイルからメタデータ抽出（rio-tiler 経由、optional dependency）。"""
    try:
        from lib.raster_tiles import (
            get_cog_info,
            get_cog_statistics,
            is_rasterio_available,
        )

        if not is_rasterio_available():
            logger.warning("rio-tiler not available, returning empty metadata")
            return COGMetadata()

        info = get_cog_info(cog_url)

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

        if metadata.bounds and len(metadata.bounds) == 4:
            west, south, east, north = metadata.bounds
            metadata.center = [
                (west + east) / 2,
                (south + north) / 2,
                metadata.min_zoom or 10,
            ]

        try:
            metadata.statistics = get_cog_statistics(cog_url)
        except Exception as e:
            logger.warning(f"Could not get COG statistics: {e}")

        return metadata
    except Exception as e:
        logger.exception(f"Error extracting COG metadata: {e}")
        return COGMetadata()


# =============================================================================
# Validation Functions
# =============================================================================


def validate_cog_file(file_bytes: bytes) -> tuple[bool, Optional[str]]:
    """COG ファイルの簡易検証（magic bytes + サイズ）。

    呼び出し側は既に bytes を read 済みの状態で渡す。署名検証等の厳密チェックは
    `is_cloud_optimized` で行うが、本関数は簡易ガードとして:

    - サイズが MAX_FILE_SIZE 以下
    - 0 byte でない
    - TIFF magic bytes を持つ
    """
    if not file_bytes:
        return False, "File is empty"

    if len(file_bytes) > MAX_FILE_SIZE:
        max_mb = MAX_FILE_SIZE / (1024 * 1024)
        return False, f"File size exceeds maximum ({max_mb:.0f} MB)"

    if not is_cloud_optimized(file_bytes):
        return (
            False,
            "File does not appear to be a valid TIFF / GeoTIFF (magic bytes mismatch)",
        )

    return True, None


def validate_cog_filename(filename: str, file_size: int) -> tuple[bool, Optional[str]]:
    """ファイル名 + サイズだけで簡易検証する別バリエーション（multipart upload 前用）。"""
    ext = os.path.splitext(filename.lower())[1]
    if ext not in COG_EXTENSIONS:
        return False, f"Invalid file type. Allowed: {', '.join(COG_EXTENSIONS)}"

    if file_size > MAX_FILE_SIZE:
        max_mb = MAX_FILE_SIZE / (1024 * 1024)
        return False, f"File size exceeds maximum ({max_mb:.0f} MB)"

    if file_size == 0:
        return False, "File is empty"

    return True, None


def is_cloud_optimized(file_bytes: bytes) -> bool:
    """ファイル先頭が TIFF / BigTIFF magic bytes を持つかチェック（簡易判定）。"""
    if len(file_bytes) < 8:
        return False

    magic = file_bytes[:4]
    return magic in (b"II\x2a\x00", b"MM\x00\x2a", b"II\x2b\x00", b"MM\x00\x2b")


# =============================================================================
# Singleton Storage Client
# =============================================================================


_storage_client: Optional[S3StorageClient] = None


def get_storage_client() -> S3StorageClient:
    """Get or create the singleton storage client."""
    global _storage_client
    if _storage_client is None:
        _storage_client = S3StorageClient()
    return _storage_client


def close_storage_client() -> None:
    """Reset the singleton（boto3 client は明示 close 不要だが、再生成のため）。"""
    global _storage_client
    _storage_client = None
