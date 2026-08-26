/**
 * テスト用ログインセッション管理 (Issue #110)。
 *
 * 背景: refresh token rotation により、storageState 経由で同じ refresh token
 * を 2 回使うと API 側で「reuse detected」とみなされ全 token が revoke される。
 * このため:
 *
 * - globalSetup では admin user の作成だけ行い、ログインはしない。
 * - 各テストファイルの beforeAll / beforeEach で都度ログインし、その都度
 *   発行される refresh token を使う。
 * - api-client は本モジュールの `getAccessToken()` を読み出して Bearer に
 *   セットすることで、API 側で refresh を走らせずに済む。
 */
import { request } from "@playwright/test";

const APP_BASE = process.env.PLAYWRIGHT_BASE_URL || "http://localhost:3000";

export const E2E_ADMIN_EMAIL = "e2e-admin@example.com";
export const E2E_ADMIN_PASSWORD = "E2E-pass-1!";

export interface PlaywrightCookie {
  name: string;
  value: string;
  domain: string;
  path: string;
  expires: number;
  httpOnly: boolean;
  secure: boolean;
  sameSite: "Strict" | "Lax" | "None";
}

interface SessionState {
  accessToken: string;
  cookies: PlaywrightCookie[];
}

let currentSession: SessionState | null = null;

export async function loginAsAdmin(): Promise<SessionState> {
  // /api/auth/login へ Next.js 経由でアクセスする (相対 URL)。
  // これにより HttpOnly cookie が APP_BASE のドメインに紐付き、
  // 後の page.goto と context.addCookies で整合する。
  const ctx = await request.newContext({ baseURL: APP_BASE });
  try {
    const res = await ctx.post("/api/auth/login", {
      data: { email: E2E_ADMIN_EMAIL, password: E2E_ADMIN_PASSWORD },
    });
    if (!res.ok()) {
      throw new Error(
        `Login failed: ${res.status()} ${await res.text()}`,
      );
    }
    const body = (await res.json()) as { access_token: string };
    const state = await ctx.storageState();
    currentSession = {
      accessToken: body.access_token,
      cookies: state.cookies as PlaywrightCookie[],
    };
    return currentSession;
  } finally {
    await ctx.dispose();
  }
}

export function getAccessToken(): string {
  if (!currentSession) {
    throw new Error(
      "No active session. Call loginAsAdmin() in beforeAll/beforeEach first.",
    );
  }
  return currentSession.accessToken;
}

export function getCookies(): PlaywrightCookie[] {
  if (!currentSession) {
    throw new Error(
      "No active session. Call loginAsAdmin() in beforeAll/beforeEach first.",
    );
  }
  return currentSession.cookies;
}
