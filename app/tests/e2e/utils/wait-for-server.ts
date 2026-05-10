/**
 * Polling helper to wait until a URL responds with 2xx.
 *
 * `request` instead of `node:fetch` so it works under Playwright's process
 * without polyfill considerations.
 */
import { request as createRequest } from "@playwright/test";

export async function waitForServer(url: string, timeoutMs = 60_000): Promise<void> {
  const start = Date.now();
  const ctx = await createRequest.newContext();
  try {
    while (Date.now() - start < timeoutMs) {
      try {
        const res = await ctx.get(url);
        if (res.ok()) return;
      } catch {
        // ignore connection refused / etc.
      }
      await new Promise((r) => setTimeout(r, 500));
    }
    throw new Error(`Timeout waiting for ${url} to be ready (${timeoutMs}ms)`);
  } finally {
    await ctx.dispose();
  }
}
