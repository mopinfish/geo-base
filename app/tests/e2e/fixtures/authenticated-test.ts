/**
 * Authenticated project 用の Playwright test fixture (Issue #110, #111)。
 *
 * 各テスト直前に admin として login し、その時に発行された refresh token cookie
 * を browser context に inject する。これにより:
 *
 * - storageState の共有による refresh token rotation 衝突を回避
 * - api-client の Bearer 用 access_token も都度更新される (utils/session.ts)
 *
 * Phase 2 (Issue #111) で workers: 4 に拡張する際は、各 worker が独自の
 * `geo_base_e2e_wN` DB を使う。`process.env.TEST_WORKER_INDEX` で worker index
 * を参照できるようにしてあるが、Phase 2 段階では `workers: 1` のため常に 0。
 */
import { test as base, expect } from "@playwright/test";

import { loginAsAdmin, getCookies } from "../utils/session";

export const test = base.extend<{ adminAuth: void }>({
  adminAuth: [
    async ({ context }, use, testInfo) => {
      // worker index を環境変数経由で session に渡す（将来の per-worker DB 切替用）。
      // Phase 2 の workers: 1 段階ではすべて 0 にフォールバックする。
      process.env.TEST_WORKER_INDEX = String(testInfo.workerIndex);
      await loginAsAdmin();
      await context.addCookies(getCookies());
      await use();
    },
    { auto: true },
  ],
});

export { expect };
