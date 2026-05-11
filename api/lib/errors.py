"""Structured API error responses for i18n Phase 2 (#106).

このモジュールは、API エラーレスポンスを `{error: {code, message, details?}}`
の構造化 envelope で返すためのヘルパを提供する。Phase 3 (Admin UI next-intl)
が `code` をキーに翻訳できるようにすることが目的。

## 使い方

```python
from lib.errors import ErrorCode, api_error

# 新しいやり方 (推奨、envelope を返す)
raise api_error(
    404,
    ErrorCode.TILESET_NOT_FOUND,
    "Tileset not found",
    details={"tileset_id": tileset_id},
)

# 旧来の HTTPException(detail=...) も依然動作する (envelope 化されず
# `{detail: "..."}` を返す)。段階移行のため Phase 2b 期間中は混在 OK。
raise HTTPException(status_code=404, detail="Tileset not found")
```

## レスポンス形状

`api_error()` 経由は:

```json
{
  "error": {
    "code": "tileset_not_found",
    "message": "Tileset not found",
    "details": { "tileset_id": "abc-123" }   // optional
  }
}
```

`HTTPException(detail="...")` 経由は従来通り `{detail: "..."}` のまま。
クライアント (Admin UI) は両形を許容する: `body.error?.code` があれば
新形、無ければ legacy として `body.detail` を読む。
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from fastapi import HTTPException


class ErrorCode(str, Enum):
    """Machine-readable error code (`<domain>_<reason>` snake_case)。

    Admin UI (Phase 3 / next-intl) は本 enum 値をキーに翻訳する。
    新規 code 追加時は対応する UI 翻訳キー (`app/src/lib/api-errors.ts` の
    `JA_MESSAGES`、後の Phase 3 で `app/src/locales/ja/api-errors.json`)
    を同時に追加すること。
    """

    # --- auth (lib/routers/auth.py) ---
    AUTH_INVALID_CREDENTIALS = "auth_invalid_credentials"
    AUTH_FORBIDDEN = "auth_forbidden"
    AUTH_UNAUTHORIZED = "auth_unauthorized"
    AUTH_TOKEN_EXPIRED = "auth_token_expired"
    AUTH_TOKEN_INVALID = "auth_token_invalid"
    AUTH_REFRESH_FAILED = "auth_refresh_failed"
    AUTH_RATE_LIMITED = "auth_rate_limited"
    AUTH_USER_ALREADY_EXISTS = "auth_user_already_exists"
    AUTH_USER_NOT_FOUND = "auth_user_not_found"
    AUTH_WEAK_PASSWORD = "auth_weak_password"
    AUTH_ORIGIN_NOT_ALLOWED = "auth_origin_not_allowed"
    AUTH_INVITATION_NOT_FOUND = "auth_invitation_not_found"
    AUTH_INVITATION_INVALID = "auth_invitation_invalid"
    AUTH_INVITATION_EXPIRED = "auth_invitation_expired"
    AUTH_PROVIDER_ERROR = "auth_provider_error"

    # --- tileset ---
    TILESET_NOT_FOUND = "tileset_not_found"
    TILESET_FORBIDDEN = "tileset_forbidden"
    TILESET_NAME_CONFLICT = "tileset_name_conflict"
    TILESET_LAYER_NOT_FOUND = "tileset_layer_not_found"
    TILESET_INVALID = "tileset_invalid"

    # --- feature ---
    FEATURE_NOT_FOUND = "feature_not_found"
    FEATURE_INVALID_GEOMETRY = "feature_invalid_geometry"
    FEATURE_FORBIDDEN = "feature_forbidden"

    # --- datasource ---
    DATASOURCE_NOT_FOUND = "datasource_not_found"
    DATASOURCE_FORBIDDEN = "datasource_forbidden"
    DATASOURCE_UPLOAD_FAILED = "datasource_upload_failed"
    DATASOURCE_UNSUPPORTED_FORMAT = "datasource_unsupported_format"
    DATASOURCE_INVALID = "datasource_invalid"
    DATASOURCE_ALREADY_EXISTS = "datasource_already_exists"

    # --- team ---
    TEAM_NOT_FOUND = "team_not_found"
    TEAM_FORBIDDEN = "team_forbidden"
    TEAM_OWNER_REQUIRED = "team_owner_required"
    TEAM_MEMBER_EXISTS = "team_member_exists"
    TEAM_MEMBER_NOT_FOUND = "team_member_not_found"
    TEAM_TILESET_ALREADY_SHARED = "team_tileset_already_shared"
    TEAM_INVITATION_NOT_FOUND = "team_invitation_not_found"
    TEAM_INVITATION_EXPIRED = "team_invitation_expired"
    TEAM_INVITATION_ALREADY_USED = "team_invitation_already_used"
    TEAM_INVITATION_ALREADY_EXISTS = "team_invitation_already_exists"
    TEAM_INVITATION_EMAIL_MISMATCH = "team_invitation_email_mismatch"
    TEAM_INVITATION_INVALID_STATUS = "team_invitation_invalid_status"
    TEAM_INVALID = "team_invalid"

    # --- api_key ---
    API_KEY_NOT_FOUND = "api_key_not_found"
    API_KEY_FORBIDDEN = "api_key_forbidden"
    API_KEY_REVOKED = "api_key_revoked"
    API_KEY_EXPIRED = "api_key_expired"
    API_KEY_INVALID_SCOPE = "api_key_invalid_scope"
    API_KEY_INVALID = "api_key_invalid"

    # --- tiles (raster / pmtiles / mbtiles / dynamic) ---
    TILE_NOT_FOUND = "tile_not_found"
    TILE_INVALID_COORDINATE = "tile_invalid_coordinate"
    TILE_RENDER_FAILED = "tile_render_failed"
    TILE_SOURCE_UNAVAILABLE = "tile_source_unavailable"
    TILE_SERVICE_UNAVAILABLE = "tile_service_unavailable"

    # --- colormap ---
    COLORMAP_NOT_FOUND = "colormap_not_found"

    # --- validation / generic ---
    VALIDATION_FIELD_REQUIRED = "validation_field_required"
    VALIDATION_INVALID_VALUE = "validation_invalid_value"
    VALIDATION_OUT_OF_RANGE = "validation_out_of_range"
    VALIDATION_INVALID = "validation_invalid"

    # --- internal / infrastructure ---
    INTERNAL_DB_ERROR = "internal_db_error"
    INTERNAL_STORAGE_ERROR = "internal_storage_error"
    INTERNAL_UNEXPECTED = "internal_unexpected"


# `HTTPException(detail=<dict with "error" key>)` 形式は本モジュールの
# envelope レスポンスを意味するためのマーカー。Starlette の default
# HTTPException handler を main.py で差し替えて、`detail.error` が
# あればそれをそのまま JSONResponse の body にする (詳細は main.py)。
ENVELOPE_MARKER_KEY = "error"


def api_error(
    status_code: int,
    code: ErrorCode,
    message: str,
    *,
    details: Optional[dict[str, Any]] = None,
) -> HTTPException:
    """構造化エラー envelope を持つ HTTPException を返す。

    通常 `raise api_error(...)` の形で使う。レスポンス body は
    `{error: {code: ..., message: ..., details: ...?}}` になる
    (default `HTTPException` 経由の `{detail: "..."}` と区別される)。

    Args:
        status_code: HTTP ステータスコード (400, 404, 403, 500 等)
        code: ErrorCode enum 値
        message: 英語の人間可読メッセージ (Admin UI 側で `code` を
            キーに翻訳するため、本 message は英語固定で OK)
        details: 構造化詳細情報 (任意)。tileset_id, feature_id 等の
            context を入れる。

    Returns:
        HTTPException with envelope-shaped detail dict.

    Example:
        raise api_error(
            404,
            ErrorCode.TILESET_NOT_FOUND,
            "Tileset not found",
            details={"tileset_id": tileset_id},
        )
    """
    if not isinstance(code, ErrorCode):
        raise TypeError(
            f"api_error code must be ErrorCode enum, got {type(code).__name__}"
        )
    envelope: dict[str, Any] = {
        ENVELOPE_MARKER_KEY: {"code": code.value, "message": message}
    }
    if details:
        envelope[ENVELOPE_MARKER_KEY]["details"] = details
    return HTTPException(status_code=status_code, detail=envelope)


def is_envelope_detail(detail: Any) -> bool:
    """`HTTPException.detail` が本モジュールの envelope 形式か判定。

    main.py の exception handler が、`detail.error.code` がある場合は
    body をそのまま (= `{error: {...}}`) で返し、そうでなければ default
    の `{detail: ...}` を返すために使う。
    """
    if not isinstance(detail, dict):
        return False
    inner = detail.get(ENVELOPE_MARKER_KEY)
    if not isinstance(inner, dict):
        return False
    return "code" in inner and "message" in inner
