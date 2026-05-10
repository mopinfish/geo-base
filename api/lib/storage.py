"""
S3 互換ストレージ統合（COG / PMTiles のアップロード backend）。

既定で Fly Tigris (https://fly.storage.tigris.dev) を想定するが、boto3 の
S3 client を使うので AWS S3 / Cloudflare R2 / MinIO 等 S3 API 互換のサービスを
endpoint URL の差し替えで利用できる（`S3_ENDPOINT_URL` env →
`lib.config.Settings.s3_endpoint_url` 経由で読まれる）。

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
from urllib.parse import urlparse

import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import BotoCoreError, ClientError

from lib.config import get_settings

logger = logging.getLogger(__name__)


# =============================================================================
# URL normalization helpers (Issue #101)
# =============================================================================

def s3_uri_to_gdal_path(url: str) -> str:
    """`s3://bucket/key` を rasterio/GDAL が認識する `/vsis3/bucket/key` に変換する。

    `s3://` 以外の URL（`https://`, `http://`, `/vsis3/...`, ローカルパス）はそのまま
    返すので、boundary で安全に呼べる。

    GDAL の `/vsis3/` driver は `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` /
    `AWS_S3_ENDPOINT` (host のみ、スキームなし) / `AWS_HTTPS` / `AWS_VIRTUAL_HOSTING`
    等の env で endpoint を解決する。boto3 標準の `AWS_ENDPOINT_URL_S3` (スキーム付)
    とは異なる名前なので、`_setup_gdal_s3_env()` でブリッジする。
    """
    if url.startswith("s3://"):
        return "/vsis3/" + url[len("s3://") :]
    return url


def _setup_gdal_s3_env() -> None:
    """boto3 標準の `AWS_ENDPOINT_URL_S3` から GDAL 用 `AWS_S3_ENDPOINT` を導出する。

    Tigris や R2 のような S3 互換 storage に対して rasterio/GDAL の `/vsis3/` を
    使うために必要な env を設定。すでに `AWS_S3_ENDPOINT` が立っていれば触らない。
    """
    if os.environ.get("AWS_S3_ENDPOINT"):
        return
    boto3_endpoint = (
        os.environ.get("AWS_ENDPOINT_URL_S3")
        or os.environ.get("S3_ENDPOINT_URL")
        or get_settings().s3_endpoint_url
    )
    if not boto3_endpoint:
        return
    parsed = urlparse(boto3_endpoint)
    host = parsed.netloc or parsed.path  # `host:port` 部分
    if not host:
        return
    os.environ["AWS_S3_ENDPOINT"] = host
    os.environ.setdefault("AWS_HTTPS", "YES" if parsed.scheme != "http" else "NO")
    # virtual-hosted は Tigris / 多くの S3 互換で動くが、互換性最大化のため
    # 既に明示されていない場合のみ FALSE (path-style) を既定にする。
    os.environ.setdefault("AWS_VIRTUAL_HOSTING", "FALSE")


# モジュール import 時に実行（`raster_tiles` が rasterio を import するより前に
# env を立てておく必要があるため）。
_setup_gdal_s3_env()


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

    def get_s3_uri(self, path: str) -> str:
        """指定 path の `s3://bucket/key` 形式の URI を返す（DB に保存する正規形）。

        Issue #101 で導入。aiopmtiles / rio-tiler は `s3://` を boto3 経由で
        読めるため、Tigris bucket が private のままタイル配信を維持できる。
        """
        return f"s3://{self.bucket}/{path.lstrip('/')}"

    def get_https_url(self, path: str) -> str:
        """指定 path の `https://endpoint/bucket/key` 形式の URL を返す（表示用）。

        Admin UI 等で「ユーザーに見せる URL」として使う。bucket が public 化
        されていなければ anonymous fetch は 403 を返すので、書き込み保存先には
        `get_s3_uri()` を使うこと。
        """
        if self._public_base_url:
            base = self._public_base_url.rstrip("/")
        else:
            base = f"{self.endpoint_url.rstrip('/')}/{self.bucket}"
        return f"{base}/{path.lstrip('/')}"

    def get_public_url(self, path: str) -> str:
        """**Deprecated**: `get_https_url()` のエイリアス。後方互換のため残置。"""
        return self.get_https_url(path)

    def upload_file(
        self,
        path: str,
        content: bytes,
        content_type: str = "application/octet-stream",
    ) -> Optional[str]:
        """`content` を `path` に PUT する。成功時は **`s3://bucket/key`** 形式の
        URI を返し、失敗時は None を返す。

        Issue #101 で戻り値を `https://...` から `s3://...` に変更（DB に保存する
        正規形）。表示用 https URL が必要な場合は `get_https_url(path)` を使う。

        Bytes をオンメモリで扱う前提（最大 MAX_FILE_SIZE = 500MB）なので大ファイル
        multipart upload は別途。
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

        s3_uri = self.get_s3_uri(path)
        logger.info(f"Uploaded {len(content)} bytes to {s3_uri}")
        return s3_uri

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


# Issue #101: PMTiles upload 用バリデータ。
# PMTiles v3 spec (https://github.com/protomaps/PMTiles/blob/main/spec/v3/spec.md):
# - 先頭 7 バイト = 'PMTiles' (0x50 0x4D 0x54 0x69 0x6C 0x65 0x73)
# - 8 バイト目 = spec version (現行 3、過去に 1/2 もある)
PMTILES_MAGIC = b"PMTiles"


def is_pmtiles_file(file_bytes: bytes) -> bool:
    """ファイル先頭が PMTiles magic を持つかチェック（v1/v2/v3 すべて同じ magic）。"""
    if len(file_bytes) < 8:
        return False
    return file_bytes[: len(PMTILES_MAGIC)] == PMTILES_MAGIC


def validate_pmtiles_file(file_bytes: bytes) -> tuple[bool, Optional[str]]:
    """PMTiles ファイルの簡易検証（magic bytes + サイズ）。

    `validate_cog_file` と同じ流儀で、router の upload ハンドラから呼び出して
    upload 前に rejection できる軽量チェック。詳細メタデータは aiopmtiles で
    取得する。
    """
    if not file_bytes:
        return False, "File is empty"

    if len(file_bytes) > MAX_FILE_SIZE:
        max_mb = MAX_FILE_SIZE / (1024 * 1024)
        return False, f"File size exceeds maximum ({max_mb:.0f} MB)"

    if not is_pmtiles_file(file_bytes):
        return (
            False,
            "File does not appear to be a valid PMTiles archive (magic bytes mismatch)",
        )

    # spec version は v1 / v2 / v3 を許容（aiopmtiles は v3 メインだが互換あり）
    return True, None


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
