/**
 * DB リセットヘルパー: POST /api/test/reset を呼ぶ。
 *
 * 安全装置: API 側でも DATABASE_URL の DB 名チェックを行うが、念のため
 * クライアント側でも `PLAYWRIGHT_API_BASE_URL` のホストが localhost / 127.0.0.1
 * 以外なら refuse する。production を誤爆しないため。
 */
import { createApiClient } from "../fixtures/api-client";

export async function resetDatabase(): Promise<void> {
  const apiBase = process.env.PLAYWRIGHT_API_BASE_URL || "http://localhost:8000";
  const url = new URL(apiBase);
  if (!["localhost", "127.0.0.1"].includes(url.hostname)) {
    throw new Error(
      `Refusing to call /api/test/reset against non-local host: ${url.hostname}`,
    );
  }

  const ctx = await createApiClient();
  try {
    const res = await ctx.post("/api/test/reset");
    if (!res.ok()) {
      throw new Error(`Failed to reset DB: ${res.status()} ${await res.text()}`);
    }
  } finally {
    await ctx.dispose();
  }
}
