"""Tests for `lib.errors` envelope shape and the main.py exception handler.

i18n Phase 2b (#106) で導入した構造化エラー envelope の正常系・互換性を検証する。
"""

from __future__ import annotations

import importlib

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from lib.errors import ENVELOPE_MARKER_KEY, ErrorCode, api_error, is_envelope_detail


def test_api_error_returns_http_exception_with_envelope():
    err = api_error(404, ErrorCode.TILESET_NOT_FOUND, "Tileset not found")
    assert isinstance(err, HTTPException)
    assert err.status_code == 404
    assert err.detail == {
        ENVELOPE_MARKER_KEY: {
            "code": "tileset_not_found",
            "message": "Tileset not found",
        }
    }


def test_api_error_with_details():
    err = api_error(
        400,
        ErrorCode.AUTH_INVALID_CREDENTIALS,
        "Bad credentials",
        details={"hint": "check password length"},
    )
    assert err.detail[ENVELOPE_MARKER_KEY]["details"] == {
        "hint": "check password length"
    }


def test_api_error_without_details_omits_key():
    err = api_error(404, ErrorCode.FEATURE_NOT_FOUND, "Feature missing")
    assert "details" not in err.detail[ENVELOPE_MARKER_KEY]


def test_api_error_rejects_non_enum_code():
    with pytest.raises(TypeError):
        api_error(404, "tileset_not_found", "x")  # type: ignore[arg-type]


def test_is_envelope_detail_positive():
    assert is_envelope_detail(
        {"error": {"code": "x", "message": "y"}}
    )
    assert is_envelope_detail(
        {"error": {"code": "x", "message": "y", "details": {"a": 1}}}
    )


def test_is_envelope_detail_negative_cases():
    assert not is_envelope_detail("plain string")
    assert not is_envelope_detail({"detail": "x"})
    assert not is_envelope_detail({"error": "x"})  # error must be dict
    assert not is_envelope_detail({"error": {}})  # missing code/message
    assert not is_envelope_detail({"error": {"code": "x"}})  # missing message
    assert not is_envelope_detail(None)
    assert not is_envelope_detail([1, 2])


def test_is_envelope_detail_rejects_non_string_code_or_message():
    """Copilot PR #126 round 2 指摘: code/message が string でない場合は
    envelope と認識しない。"""
    # code が int
    assert not is_envelope_detail({"error": {"code": 123, "message": "ok"}})
    # message が dict
    assert not is_envelope_detail({"error": {"code": "x", "message": {}}})
    # message が None
    assert not is_envelope_detail({"error": {"code": "x", "message": None}})


def test_is_envelope_detail_rejects_non_dict_details():
    """details が ある場合は dict であることを要求 (Copilot PR #126 round 2)。"""
    assert not is_envelope_detail(
        {"error": {"code": "x", "message": "y", "details": "not a dict"}}
    )
    assert not is_envelope_detail(
        {"error": {"code": "x", "message": "y", "details": [1, 2]}}
    )
    # details が None でも reject (実用上不要なら is_envelope_detail を呼ぶ前に
    # del すべき。本 guard では invalid 扱い)
    assert not is_envelope_detail(
        {"error": {"code": "x", "message": "y", "details": None}}
    )


# --- exception handler integration ---


def _build_test_app() -> FastAPI:
    """main.py の例外ハンドラを使うミニ FastAPI app。

    main.py 全体を import すると router import の副作用 (DB pool 等) が重いため、
    ここでは handler の挙動だけ確認するために再現実装する。

    NOTE: 実 main.py の同名 handler と挙動が逐字一致するよう、必要なら main を
    import すべきだが、本テストの目的は handler のロジック (envelope 判定) で
    あり、JSONResponse の組み立ては FastAPI 標準なので再実装で十分。
    """
    from fastapi.responses import JSONResponse
    from starlette.exceptions import HTTPException as StarletteHTTPException

    app = FastAPI()

    @app.exception_handler(StarletteHTTPException)
    async def handler(request, exc):
        if is_envelope_detail(exc.detail):
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.get("/envelope")
    def envelope_route():
        raise api_error(
            404,
            ErrorCode.TILESET_NOT_FOUND,
            "Tileset not found",
            details={"tileset_id": "abc"},
        )

    @app.get("/legacy")
    def legacy_route():
        raise HTTPException(status_code=400, detail="Old style error")

    @app.get("/dict-detail-not-envelope")
    def dict_detail_route():
        # detail が dict だが envelope 形式ではないケース (誤って dict を渡した等)
        raise HTTPException(status_code=400, detail={"foo": "bar"})

    return app


def test_handler_returns_envelope_unwrapped():
    client = TestClient(_build_test_app())
    res = client.get("/envelope")
    assert res.status_code == 404
    body = res.json()
    assert body == {
        "error": {
            "code": "tileset_not_found",
            "message": "Tileset not found",
            "details": {"tileset_id": "abc"},
        }
    }
    # 旧 detail 構造が混入していないこと
    assert "detail" not in body


def test_handler_falls_back_to_legacy_detail_for_string():
    client = TestClient(_build_test_app())
    res = client.get("/legacy")
    assert res.status_code == 400
    assert res.json() == {"detail": "Old style error"}


def test_handler_falls_back_to_legacy_for_non_envelope_dict():
    client = TestClient(_build_test_app())
    res = client.get("/dict-detail-not-envelope")
    assert res.status_code == 400
    # envelope 形式でない dict は default 通り {detail: <dict>} で返る
    assert res.json() == {"detail": {"foo": "bar"}}


# --- main.py の handler が登録されていることの sanity check ---


def test_main_module_registers_envelope_handler(monkeypatch):
    """E2E_MODE=1 で reload する別テストの副作用を受けないよう独立で reload。

    main.py の app に StarletteHTTPException 用 handler が 1 件以上
    登録されていることを確認する (lifespan / middleware と独立)。
    """
    monkeypatch.setenv("E2E_MODE", "0")
    import lib.main as main_module
    importlib.reload(main_module)
    from starlette.exceptions import HTTPException as StarletteHTTPException

    handlers = main_module.app.exception_handlers
    assert StarletteHTTPException in handlers, (
        "main.py must register an exception_handler for StarletteHTTPException "
        "to unwrap envelope-shaped api_error responses."
    )
