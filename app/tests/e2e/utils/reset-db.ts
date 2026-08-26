/**
 * DB リセットヘルパー: POST /api/test/reset を呼ぶ。
 *
 * `/api/test/reset` は API 側で認証不要 (E2E_MODE=1 + DB 名チェックの 2 重ガード
 * のみ) のため、本ヘルパーも認証なしの request context で叩く。これにより
 * unauthenticated project の beforeAll などからも安全に呼べる。
 *
 * 安全装置: API 側でも DATABASE_URL の DB 名チェックを行うが、念のため
 * クライアント側でも `PLAYWRIGHT_API_BASE_URL` のホストが localhost / 127.0.0.1
 * 以外なら refuse する。production を誤爆しないため。
 */
import { request } from "@playwright/test";

const API_BASE = process.env.PLAYWRIGHT_API_BASE_URL || "http://localhost:8000";

export async function resetDatabase(): Promise<void> {
  const url = new URL(API_BASE);
  if (!["localhost", "127.0.0.1"].includes(url.hostname)) {
    throw new Error(
      `Refusing to call /api/test/reset against non-local host: ${url.hostname}`,
    );
  }

  const ctx = await request.newContext({ baseURL: API_BASE });
  try {
    const res = await ctx.post("/api/test/reset");
    if (!res.ok()) {
      throw new Error(`Failed to reset DB: ${res.status()} ${await res.text()}`);
    }
  } finally {
    await ctx.dispose();
  }
}
