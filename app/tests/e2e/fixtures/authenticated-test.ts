/**
 * Authenticated project 用の Playwright test fixture (Issue #110)。
 *
 * 各テスト直前に admin として login し、その時に発行された refresh token cookie
 * を browser context に inject する。これにより:
 *
 * - storageState の共有による refresh token rotation 衝突を回避
 * - api-client の Bearer 用 access_token も都度更新される (utils/session.ts)
 *
 * authenticated 配下のテストファイルは `@playwright/test` ではなく本ファイルから
 * `test, expect` を import する。
 */
import { test as base, expect } from "@playwright/test";

import { loginAsAdmin, getCookies } from "../utils/session";

export const test = base.extend<{ adminAuth: void }>({
  adminAuth: [
    async ({ context }, use) => {
      await loginAsAdmin();
      await context.addCookies(getCookies());
      await use();
    },
    { auto: true },
  ],
});

export { expect };
