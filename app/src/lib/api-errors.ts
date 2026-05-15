/**
 * API error code → localized message mapping (i18n Phase 3 / Issue #107)。
 *
 * Backend (`api/lib/errors.py`) は `{error: {code, message, details?}}` の
 * envelope を返す。本モジュールは `code` をキーに `app/src/locales/<locale>/api-errors.json`
 * から locale に応じたメッセージへ訳出する。
 *
 * 旧来の `{detail: "..."}` レスポンスも依然返り得る (Phase 2b 期間中の段階
 * 移行 + 401 など `headers=` 保持のため意図的に envelope 化見送りの 15 件)
 * ので、`extractApiError()` は両方を許容する形にしている。
 */

import enMessages from "@/locales/en/api-errors.json";
import jaMessages from "@/locales/ja/api-errors.json";

import {
  FALLBACK_LOCALE_FOR_ACCEPT_LANGUAGE,
  type Locale,
} from "@/i18n/config";

/** Backend `{error: {code, message, details?}}` の構造 */
export interface ApiErrorPayload {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

/** UI が catch しやすいよう Error を継承 */
export class ApiClientError extends Error {
  readonly code: string;
  readonly details?: Record<string, unknown>;

  constructor(payload: ApiErrorPayload) {
    super(payload.message);
    this.name = "ApiClientError";
    this.code = payload.code;
    this.details = payload.details;
  }
}

const API_ERROR_MESSAGES: Record<Locale, Record<string, string>> = {
  en: enMessages,
  ja: jaMessages,
};

function normalizeLocale(value: string | null | undefined): Locale {
  const primary = value?.split("-")[0]?.toLowerCase();
  return primary === "en" || primary === "ja"
    ? primary
    : FALLBACK_LOCALE_FOR_ACCEPT_LANGUAGE;
}

function resolveLocale(locale?: Locale): Locale {
  if (locale) return locale;

  if (typeof document !== "undefined") {
    return normalizeLocale(document.documentElement.lang);
  }

  return FALLBACK_LOCALE_FOR_ACCEPT_LANGUAGE;
}

function getApiErrorMessages(locale?: Locale): Record<string, string> {
  return API_ERROR_MESSAGES[resolveLocale(locale)];
}

/**
 * fetch のレスポンス JSON から API error を抽出する。
 *
 * 戻り値の優先順:
 * 1. envelope `{error: {code, message, details?}}` → ApiClientError
 * 2. legacy `{detail: "..."}` → 通常の Error (code 無し)
 * 3. それ以外 → null (呼び出し側で fallback メッセージ)
 */
export function extractApiError(body: unknown): ApiClientError | Error | null {
  if (!body || typeof body !== "object") return null;
  const obj = body as Record<string, unknown>;

  // envelope shape
  const envelope = obj.error;
  if (envelope && typeof envelope === "object") {
    const env = envelope as Record<string, unknown>;
    if (typeof env.code === "string" && typeof env.message === "string") {
      return new ApiClientError({
        code: env.code,
        message: env.message,
        details: (env.details ?? undefined) as
          | Record<string, unknown>
          | undefined,
      });
    }
  }

  // legacy `detail` shape
  if (typeof obj.detail === "string") {
    return new Error(obj.detail);
  }

  return null;
}

/**
 * ApiClientError または一般 Error をユーザー向け日本語メッセージに変換する。
 *
 * - `ApiClientError` で `code` が catalog にあれば locale に応じた訳文を返す
 * - `code` が未知なら英語 `message` をそのまま返す (forward-compat)
 * - `ApiClientError` でなければ `error.message` をそのまま返す
 * - `locale` 省略時は client-side helper として `<html lang>` を参照し、
 *   `document` がない環境では既定 locale に fallback する
 */
export function translateApiError(err: unknown, locale?: Locale): string {
  if (err instanceof ApiClientError) {
    return getApiErrorMessages(locale)[err.code] ?? err.message;
  }
  if (err instanceof Error) return err.message;
  return getApiErrorMessages(locale).internal_unexpected ?? "Unexpected error occurred";
}
