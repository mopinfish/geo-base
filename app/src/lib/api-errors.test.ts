import { describe, it, expect } from "vitest";

import {
  ApiClientError,
  extractApiError,
  translateApiError,
} from "./api-errors";

describe("extractApiError", () => {
  it("envelope `{error: {code, message}}` を ApiClientError に変換する", () => {
    const result = extractApiError({
      error: { code: "tileset_not_found", message: "Tileset not found" },
    });
    expect(result).toBeInstanceOf(ApiClientError);
    const err = result as ApiClientError;
    expect(err.code).toBe("tileset_not_found");
    expect(err.message).toBe("Tileset not found");
    expect(err.details).toBeUndefined();
  });

  it("envelope の `details` も保持する", () => {
    const result = extractApiError({
      error: {
        code: "tileset_not_found",
        message: "Tileset not found",
        details: { tileset_id: "abc-123" },
      },
    });
    const err = result as ApiClientError;
    expect(err.details).toEqual({ tileset_id: "abc-123" });
  });

  it("legacy `{detail: '...'}` は普通の Error にする (code 無し)", () => {
    const result = extractApiError({ detail: "Old style error" });
    expect(result).toBeInstanceOf(Error);
    expect(result).not.toBeInstanceOf(ApiClientError);
    expect((result as Error).message).toBe("Old style error");
  });

  it("error フィールドが文字列など不正形なら null を返す", () => {
    expect(extractApiError({ error: "wrong type" })).toBeNull();
    expect(extractApiError({ error: {} })).toBeNull();
    expect(extractApiError({ error: { code: "x" } })).toBeNull();
    expect(extractApiError({ error: { message: "y" } })).toBeNull();
  });

  it("空または null は null を返す", () => {
    expect(extractApiError(null)).toBeNull();
    expect(extractApiError(undefined)).toBeNull();
    expect(extractApiError({})).toBeNull();
    expect(extractApiError("plain string")).toBeNull();
  });
});

describe("translateApiError", () => {
  it("既知 code は日本語訳に変換する", () => {
    const err = new ApiClientError({
      code: "tileset_not_found",
      message: "Tileset not found",
    });
    expect(translateApiError(err)).toBe("タイルセットが見つかりません");
  });

  it("明示 locale が渡された場合はその locale の訳文を返す", () => {
    const err = new ApiClientError({
      code: "tileset_not_found",
      message: "Tileset not found",
    });
    expect(translateApiError(err, "en")).toBe("Tileset not found.");
  });

  it("locale 未指定かつ document がない場合は既定 locale にフォールバックする", () => {
    expect(globalThis.document).toBeUndefined();
    const err = new ApiClientError({
      code: "tileset_not_found",
      message: "Tileset not found",
    });
    expect(translateApiError(err)).toBe("タイルセットが見つかりません");
  });

  it("複数 domain の code がそれぞれ訳出される (smoke)", () => {
    const cases: Array<[string, string]> = [
      ["auth_invalid_credentials", "メールアドレスまたはパスワードが正しくありません"],
      ["team_not_found", "チームが見つかりません"],
      ["api_key_revoked", "この API キーは無効化されています"],
      ["validation_field_required", "必須項目が入力されていません"],
      ["internal_db_error", "データベースエラーが発生しました"],
    ];
    for (const [code, expected] of cases) {
      const err = new ApiClientError({ code, message: "ignored" });
      expect(translateApiError(err)).toBe(expected);
    }
  });

  it("未知 code は英語 message を fallback で返す (forward-compat)", () => {
    const err = new ApiClientError({
      code: "some_future_code_not_in_map",
      message: "Future error message",
    });
    expect(translateApiError(err)).toBe("Future error message");
  });

  it("locale 未指定でも未知 code は元 message を返す", () => {
    expect(globalThis.document).toBeUndefined();
    const err = new ApiClientError({
      code: "unknown_server_code",
      message: "Unknown server message",
    });
    expect(translateApiError(err)).toBe("Unknown server message");
  });

  it("ApiClientError 以外の Error は message をそのまま返す", () => {
    expect(translateApiError(new Error("legacy detail"))).toBe("legacy detail");
  });

  it("Error 以外は generic 日本語にフォールバック", () => {
    expect(translateApiError(null)).toBe("予期しないエラーが発生しました");
    expect(translateApiError("string")).toBe("予期しないエラーが発生しました");
    expect(translateApiError(undefined)).toBe("予期しないエラーが発生しました");
  });
});

describe("ApiClientError", () => {
  it("name と Error 継承", () => {
    const err = new ApiClientError({
      code: "tileset_forbidden",
      message: "Access denied",
    });
    expect(err.name).toBe("ApiClientError");
    expect(err instanceof Error).toBe(true);
    expect(err instanceof ApiClientError).toBe(true);
  });
});
