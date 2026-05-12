export class AuthApiError extends Error {
  constructor(public status: number, public detail: string) {
    super(detail);
  }
}

export class InvalidCredentialsError extends AuthApiError {}
export class RateLimitedError extends AuthApiError {}
export class UnauthorizedError extends AuthApiError {}
export class WeakPasswordError extends AuthApiError {}
export class UserAlreadyExistsError extends AuthApiError {}

function normalizeDetail(raw: unknown, fallback: string): string {
  if (typeof raw === "string") return raw;
  if (Array.isArray(raw)) {
    // FastAPI/Pydantic の 422 は [{type, loc, msg, input, ctx}, ...] という配列
    const parts = raw
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object") {
          const obj = item as Record<string, unknown>;
          const loc = Array.isArray(obj.loc) ? obj.loc.join(".") : "";
          const msg = typeof obj.msg === "string" ? obj.msg : "";
          return loc && msg ? `${loc}: ${msg}` : msg || JSON.stringify(item);
        }
        return String(item);
      })
      .filter(Boolean);
    return parts.length > 0 ? parts.join("; ") : fallback;
  }
  if (raw && typeof raw === "object") {
    return JSON.stringify(raw);
  }
  return fallback;
}

/**
 * i18n Phase 2b (#106): API レスポンスが envelope `{error: {code, message}}`
 * 形式の場合、`code` をキーに `api-errors.ts` の日本語 map で訳出してから
 * AuthApiError に詰める。ない場合は従来の `{detail: ...}` パスにフォールバック。
 *
 * これにより login / signup / password reset / accept invitation 等の
 * 既存 catch (`err instanceof AuthApiError ? err.detail : ...`) はそのまま
 * 日本語表示される。
 */
async function readErrorBody(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

export async function parseAuthError(response: Response): Promise<AuthApiError> {
  // dynamic import で循環依存を避ける (api-errors.ts 側はこのファイルに
  // 依存しない予定なので実害はないが、bundle 単位の独立性を保つ意味で)。
  const { extractApiError, translateApiError } = await import(
    "../api-errors"
  );

  const body = await readErrorBody(response);
  const extracted = extractApiError(body);

  let detail: string;
  if (extracted) {
    // envelope or legacy detail string — どちらも translateApiError で
    // 日本語に変換される (legacy は `err.message` がそのまま使われる)
    detail = translateApiError(extracted);
  } else {
    detail = normalizeDetail(
      (body as { detail?: unknown } | null)?.detail,
      "Authentication error",
    );
  }

  switch (response.status) {
    case 401:
      return new UnauthorizedError(401, detail);
    case 429:
      return new RateLimitedError(429, detail);
    case 400:
      if (detail.toLowerCase().includes("password")) {
        return new WeakPasswordError(400, detail);
      }
      return new AuthApiError(400, detail);
    case 409:
      return new UserAlreadyExistsError(409, detail);
    default:
      return new AuthApiError(response.status, detail);
  }
}
