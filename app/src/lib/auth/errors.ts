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

export async function parseAuthError(response: Response): Promise<AuthApiError> {
  let detail = "Authentication error";
  try {
    const data = await response.json();
    detail = normalizeDetail(data?.detail, detail);
  } catch {
    // ignore
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
