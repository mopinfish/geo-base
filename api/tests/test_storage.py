"""Tests for the S3-compatible storage client (lib/storage.py).

Issue #72 (PR #88) で旧 SupabaseStorageClient から S3StorageClient (boto3)
への切替を行った際の動作確認。本番では Fly Tigris に対して PUT / GET / HEAD /
DELETE する想定。本テストは moto[s3] でローカルの in-memory S3 を立ててエンド
ツーエンドに近い形で検証する。
"""

import boto3
import pytest
from moto import mock_aws

import lib.storage as storage_module
from lib.storage import (
    COG_EXTENSIONS,
    MAX_FILE_SIZE,
    S3StorageClient,
    UploadResult,
    is_cloud_optimized,
    validate_cog_file,
    validate_cog_filename,
)


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------

# moto の mock S3 はデフォルトの AWS endpoint で動くので、テスト中は本実装側
# (settings.s3_endpoint_url=tigris) を上書きしてデフォルト endpoint に向ける。
TEST_BUCKET = "geo-base-tiles-test"


@pytest.fixture
def aws_credentials(monkeypatch):
    """moto が拾う dummy credentials を環境変数にセット。"""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_REGION", "us-east-1")


@pytest.fixture
def s3_bucket(aws_credentials):
    """moto で in-memory S3 を起動し、テスト bucket を作成して yield する。"""
    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(
            Bucket=TEST_BUCKET
        )
        yield TEST_BUCKET


@pytest.fixture
def storage_client(s3_bucket):
    """moto-mocked AWS S3 endpoint に向けた S3StorageClient。

    endpoint_url を AWS のデフォルト (`https://s3.amazonaws.com`) に明示する。
    実装の `endpoint_url or settings.s3_endpoint_url` は None を Tigris にフォール
    バックするため、ここでは Tigris を回避するために明示文字列を渡す必要がある。
    """
    storage_module._storage_client = None  # other tests からの汚染を回避
    return S3StorageClient(
        bucket=s3_bucket,
        endpoint_url="https://s3.amazonaws.com",
        region="us-east-1",
    )


# 最小の TIFF magic bytes（is_cloud_optimized が True を返す形）+ パディング。
# 本物の COG ではないが、validate_cog_file の magic byte チェックは通過する。
# is_cloud_optimized は最低 8 バイト要求するので念のため 32 バイト用意する。
_TIFF_MAGIC_LE = b"II\x2a\x00" + b"\x00" * 32


# ---------------------------------------------------------------------------
# is_cloud_optimized
# ---------------------------------------------------------------------------


class TestIsCloudOptimized:
    # is_cloud_optimized は先頭 4 バイトの magic を見るが、長さ 8 未満は False を返すので
    # 各サンプルを 8 バイト以上に padding する。
    def test_recognizes_le_tiff(self):
        assert is_cloud_optimized(b"II\x2a\x00" + b"\x00" * 8) is True

    def test_recognizes_be_tiff(self):
        assert is_cloud_optimized(b"MM\x00\x2a" + b"\x00" * 8) is True

    def test_recognizes_bigtiff_le(self):
        assert is_cloud_optimized(b"II\x2b\x00" + b"\x00" * 8) is True

    def test_rejects_random_bytes(self):
        assert is_cloud_optimized(b"PK\x03\x04" + b"\x00" * 8) is False

    def test_rejects_too_short(self):
        assert is_cloud_optimized(b"II") is False


# ---------------------------------------------------------------------------
# validate_cog_file
# ---------------------------------------------------------------------------


class TestValidateCogFile:
    def test_accepts_valid_tiff(self):
        ok, msg = validate_cog_file(_TIFF_MAGIC_LE)
        assert ok is True
        assert msg is None

    def test_rejects_empty(self):
        ok, msg = validate_cog_file(b"")
        assert ok is False
        assert msg == "File is empty"

    def test_rejects_oversize(self, monkeypatch):
        # MAX_FILE_SIZE そのままで oversize ケースを作ると 500MB のメモリ確保が
        # 走り CI / ローカルで不安定になるため、しきい値を小さく差し替える。
        monkeypatch.setattr("lib.storage.MAX_FILE_SIZE", 1024)
        big = b"II\x2a\x00" + b"\x00" * 2048
        ok, msg = validate_cog_file(big)
        assert ok is False
        assert "exceeds maximum" in msg

    def test_rejects_non_tiff_magic(self):
        ok, msg = validate_cog_file(b"PK\x03\x04not_a_tiff_at_all")
        assert ok is False
        assert "magic bytes" in msg


class TestValidateCogFilename:
    def test_accepts_tiff(self):
        ok, msg = validate_cog_filename("test.tif", 1024)
        assert ok is True
        assert msg is None

    def test_rejects_wrong_extension(self):
        ok, msg = validate_cog_filename("test.png", 1024)
        assert ok is False
        assert ".tif" in msg or "Allowed" in msg

    def test_rejects_zero_size(self):
        ok, msg = validate_cog_filename("test.tif", 0)
        assert ok is False
        assert "empty" in msg.lower()

    def test_recognizes_geotiff_extension(self):
        ok, _ = validate_cog_filename("test.geotiff", 1024)
        assert ok is True
        assert ".geotiff" in COG_EXTENSIONS


# ---------------------------------------------------------------------------
# S3StorageClient (moto-backed)
# ---------------------------------------------------------------------------


class TestS3StorageClient:
    def test_upload_file_returns_s3_uri(self, storage_client, s3_bucket):
        # Issue #101 で戻り値を https から s3:// 形式に変更（DB 保存する正規形）。
        url = storage_client.upload_file("foo/bar.tif", _TIFF_MAGIC_LE, "image/tiff")
        assert url is not None
        assert url == f"s3://{s3_bucket}/foo/bar.tif"

    def test_upload_then_file_exists(self, storage_client):
        path = "exists/here.tif"
        storage_client.upload_file(path, _TIFF_MAGIC_LE, "image/tiff")
        assert storage_client.file_exists(path) is True

    def test_file_does_not_exist(self, storage_client):
        assert storage_client.file_exists("nope/missing.tif") is False

    def test_delete_file(self, storage_client):
        path = "to-delete/x.tif"
        storage_client.upload_file(path, _TIFF_MAGIC_LE, "image/tiff")
        assert storage_client.file_exists(path) is True
        assert storage_client.delete_file(path) is True
        assert storage_client.file_exists(path) is False

    def test_upload_oversize_returns_none(self, storage_client, monkeypatch):
        # MAX_FILE_SIZE そのままだと 500MB のメモリ確保で OOM/遅延の原因になるため、
        # しきい値を小さく差し替えてから oversize 分岐を再現する。
        monkeypatch.setattr("lib.storage.MAX_FILE_SIZE", 1024)
        big = b"II\x2a\x00" + b"\x00" * 2048
        url = storage_client.upload_file("big.tif", big, "image/tiff")
        assert url is None

    def test_get_public_url_uses_public_base_url_when_set(self, s3_bucket):
        client = S3StorageClient(
            bucket=s3_bucket,
            endpoint_url="https://fly.storage.tigris.dev",
            region="auto",
            public_base_url="https://cdn.example.com/tiles",
        )
        assert (
            client.get_public_url("a/b/c.tif")
            == "https://cdn.example.com/tiles/a/b/c.tif"
        )

    def test_get_public_url_falls_back_to_endpoint_plus_bucket(self, s3_bucket):
        client = S3StorageClient(
            bucket=s3_bucket,
            endpoint_url="https://fly.storage.tigris.dev",
            region="auto",
            public_base_url=None,
        )
        assert (
            client.get_public_url("a/b/c.tif")
            == f"https://fly.storage.tigris.dev/{s3_bucket}/a/b/c.tif"
        )

    def test_upload_fileobj_generates_path(self, storage_client):
        import io

        data = io.BytesIO(_TIFF_MAGIC_LE)
        result: UploadResult = storage_client.upload_fileobj(
            file=data,
            filename="my image.tif",
            tileset_id="ts-123",
            user_id="user-abc",
            content_type="image/tiff",
        )
        assert result.success is True
        assert result.path is not None
        # user_id / tileset_id / sanitized filename を含むはず
        assert "user-abc/" in result.path
        assert "ts-123/" in result.path
        # safe_filename: スペースは除去されるが拡張子は残る
        assert result.path.endswith("myimage.tif")
        # Issue #101: result.url も s3:// 形式
        assert result.url is not None
        assert result.url.startswith("s3://")


class TestUrlHelpers:
    """Issue #101: s3:// と https:// URL 変換ヘルパ。"""

    def test_get_s3_uri(self, s3_bucket):
        from lib.storage import S3StorageClient
        c = S3StorageClient(
            bucket=s3_bucket,
            endpoint_url="https://fly.storage.tigris.dev",
            region="auto",
        )
        assert c.get_s3_uri("a/b/c.tif") == f"s3://{s3_bucket}/a/b/c.tif"
        # 先頭 / は剥がす
        assert c.get_s3_uri("/leading/slash.tif") == f"s3://{s3_bucket}/leading/slash.tif"

    def test_get_https_url_with_public_base(self, s3_bucket):
        from lib.storage import S3StorageClient
        c = S3StorageClient(
            bucket=s3_bucket,
            endpoint_url="https://fly.storage.tigris.dev",
            region="auto",
            public_base_url="https://cdn.example.com/tiles",
        )
        assert c.get_https_url("a/b/c.tif") == "https://cdn.example.com/tiles/a/b/c.tif"

    def test_get_https_url_default(self, s3_bucket):
        from lib.storage import S3StorageClient
        c = S3StorageClient(
            bucket=s3_bucket,
            endpoint_url="https://fly.storage.tigris.dev",
            region="auto",
            public_base_url=None,
        )
        assert (
            c.get_https_url("a/b/c.tif")
            == f"https://fly.storage.tigris.dev/{s3_bucket}/a/b/c.tif"
        )

    def test_get_public_url_alias(self, s3_bucket):
        # 後方互換 alias は get_https_url と同じ結果を返す
        from lib.storage import S3StorageClient
        c = S3StorageClient(
            bucket=s3_bucket,
            endpoint_url="https://fly.storage.tigris.dev",
            region="auto",
        )
        assert c.get_public_url("x.tif") == c.get_https_url("x.tif")


class TestValidatePmtilesFile:
    """Issue #101: PMTiles upload 用バリデータ。"""

    # PMTiles v3 magic + version byte + padding
    _PMTILES_MIN = b"PMTiles" + b"\x03" + b"\x00" * 16

    def test_accepts_valid_pmtiles(self):
        from lib.storage import validate_pmtiles_file
        ok, msg = validate_pmtiles_file(self._PMTILES_MIN)
        assert ok is True
        assert msg is None

    def test_rejects_empty(self):
        from lib.storage import validate_pmtiles_file
        ok, msg = validate_pmtiles_file(b"")
        assert ok is False
        assert msg == "File is empty"

    def test_rejects_oversize(self, monkeypatch):
        from lib.storage import validate_pmtiles_file
        monkeypatch.setattr("lib.storage.MAX_FILE_SIZE", 1024)
        big = b"PMTiles\x03" + b"\x00" * 2048
        ok, msg = validate_pmtiles_file(big)
        assert ok is False
        assert "exceeds maximum" in msg

    def test_rejects_non_pmtiles_magic(self):
        from lib.storage import validate_pmtiles_file
        ok, msg = validate_pmtiles_file(b"PK\x03\x04not_pmtiles_at_all" + b"\x00" * 16)
        assert ok is False
        assert "magic bytes" in msg

    def test_rejects_too_short(self):
        from lib.storage import validate_pmtiles_file
        ok, msg = validate_pmtiles_file(b"PM")
        assert ok is False
        # 5 byte だと magic match しないので "magic bytes mismatch"
        assert "magic bytes" in msg

    def test_is_pmtiles_file_helper(self):
        from lib.storage import is_pmtiles_file
        assert is_pmtiles_file(self._PMTILES_MIN) is True
        assert is_pmtiles_file(b"PMTilez\x03" + b"\x00" * 16) is False  # 1 char different
        assert is_pmtiles_file(b"PMTiles") is False  # < 8 bytes
        assert is_pmtiles_file(b"") is False


class TestS3UriToGdalPath:
    """Issue #101: s3:// → /vsis3/ 変換ヘルパ（rasterio / GDAL 互換）。"""

    def test_translates_s3_to_vsis3(self):
        from lib.storage import s3_uri_to_gdal_path
        assert s3_uri_to_gdal_path("s3://bucket/key/path.tif") == "/vsis3/bucket/key/path.tif"

    def test_passthrough_https(self):
        from lib.storage import s3_uri_to_gdal_path
        url = "https://example.com/file.tif"
        assert s3_uri_to_gdal_path(url) == url

    def test_passthrough_local_path(self):
        from lib.storage import s3_uri_to_gdal_path
        assert s3_uri_to_gdal_path("/tmp/file.tif") == "/tmp/file.tif"

    def test_passthrough_already_vsis3(self):
        from lib.storage import s3_uri_to_gdal_path
        assert s3_uri_to_gdal_path("/vsis3/bucket/key.tif") == "/vsis3/bucket/key.tif"


class TestSetupGdalS3Env:
    """Issue #101 round 5: スキーム有無 / ポート付き endpoint の堅牢パース。

    `urlparse("localhost:9000")` は scheme='localhost' / path='9000' と誤解析する
    ため、`_setup_gdal_s3_env` は `://` を含まない値を `//` で補ってから netloc
    として読む。
    """

    GDAL_KEYS = ["AWS_S3_ENDPOINT", "AWS_HTTPS", "AWS_VIRTUAL_HOSTING"]

    def _clean_env(self, monkeypatch):
        # 既存の env を取り除いて関数の挙動を独立に検証する
        for key in [
            *self.GDAL_KEYS,
            "AWS_ENDPOINT_URL_S3",
            "S3_ENDPOINT_URL",
        ]:
            monkeypatch.delenv(key, raising=False)

    def test_https_url_with_explicit_scheme(self, monkeypatch):
        from lib.storage import _setup_gdal_s3_env
        self._clean_env(monkeypatch)
        monkeypatch.setenv("AWS_ENDPOINT_URL_S3", "https://fly.storage.tigris.dev")
        _setup_gdal_s3_env()
        import os
        assert os.environ["AWS_S3_ENDPOINT"] == "fly.storage.tigris.dev"
        assert os.environ["AWS_HTTPS"] == "YES"
        assert os.environ["AWS_VIRTUAL_HOSTING"] == "FALSE"

    def test_http_url_explicit_scheme(self, monkeypatch):
        from lib.storage import _setup_gdal_s3_env
        self._clean_env(monkeypatch)
        monkeypatch.setenv("S3_ENDPOINT_URL", "http://localhost:9000")
        _setup_gdal_s3_env()
        import os
        assert os.environ["AWS_S3_ENDPOINT"] == "localhost:9000"
        assert os.environ["AWS_HTTPS"] == "NO"

    def test_schemeless_host_port(self, monkeypatch):
        """`localhost:9000` のようなスキーム無し endpoint も誤解析しない。"""
        from lib.storage import _setup_gdal_s3_env
        self._clean_env(monkeypatch)
        monkeypatch.setenv("S3_ENDPOINT_URL", "localhost:9000")
        _setup_gdal_s3_env()
        import os
        assert os.environ["AWS_S3_ENDPOINT"] == "localhost:9000"
        # スキーム不明 → HTTPS=YES を既定（production 大半が HTTPS）。
        # ローカル minio で http にしたい場合は AWS_HTTPS を明示で渡す前提。
        assert os.environ["AWS_HTTPS"] == "YES"

    def test_empty_env_does_nothing(self, monkeypatch):
        from lib.storage import _setup_gdal_s3_env
        self._clean_env(monkeypatch)
        _setup_gdal_s3_env()
        import os
        for key in self.GDAL_KEYS:
            assert key not in os.environ

    def test_existing_aws_s3_endpoint_not_overwritten(self, monkeypatch):
        from lib.storage import _setup_gdal_s3_env
        self._clean_env(monkeypatch)
        monkeypatch.setenv("AWS_S3_ENDPOINT", "preset.example.com")
        monkeypatch.setenv("AWS_ENDPOINT_URL_S3", "https://override.example.com")
        _setup_gdal_s3_env()
        import os
        assert os.environ["AWS_S3_ENDPOINT"] == "preset.example.com"
