/**
 * E2E 専用: 直前に発行された team_invitation token を API の test endpoint
 * 経由で取得する（実 email 配信を待たずにテストが進められる）。
 *
 * NOTE: password_reset は token_hash しか DB に残らないため非対応。
 *
 * 安全装置: `/api/test/tokens` は招待 token（実質的に他人のアカウントを
 * 乗っ取れる値）を返すため、`utils/reset-db.ts` と同じく `PLAYWRIGHT_API_BASE_URL`
 * のホストが localhost / 127.0.0.1 でない場合は refuse する。production に
 * 誤って向けることを防ぐ。
 */
import { request } from "@playwright/test";

const API_BASE = process.env.PLAYWRIGHT_API_BASE_URL || "http://localhost:8000";

export type TokenType = "team_invitation";

function assertLocalApiOrDie(): void {
  const url = new URL(API_BASE);
  if (!["localhost", "127.0.0.1"].includes(url.hostname)) {
    throw new Error(
      `Refusing to call /api/test/tokens against non-local host: ${url.hostname}`,
    );
  }
}

export async function fetchRecentToken(
  type: TokenType,
  email: string,
): Promise<string> {
  assertLocalApiOrDie();
  const ctx = await request.newContext({ baseURL: API_BASE });
  try {
    const res = await ctx.get(
      `/api/test/tokens?type=${encodeURIComponent(type)}&email=${encodeURIComponent(email)}`,
    );
    if (!res.ok()) {
      throw new Error(
        `Failed to fetch ${type} token for ${email}: ${res.status()} ${await res.text()}`,
      );
    }
    const body = (await res.json()) as { token: string };
    return body.token;
  } finally {
    await ctx.dispose();
  }
}
