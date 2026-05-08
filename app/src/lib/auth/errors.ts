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

export async function parseAuthError(response: Response): Promise<AuthApiError> {
  let detail = "Authentication error";
  try {
    const data = await response.json();
    detail = data.detail || detail;
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
