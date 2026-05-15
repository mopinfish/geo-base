import { defineConfig, devices } from "@playwright/test";

/**
 * E2E test configuration (Issue #110, Phase 1).
 *
 * - 単一の baseURL に対して Playwright を実行する。
 * - 認証が必要なテストは `authenticated` project で動かす。各テストの
 *   beforeEach で都度ログインして cookie を context に注入する設計
 *   (refresh token rotation との衝突を避けるため、storageState を共有しない)。
 * - 認証フロー自体のテストは `unauthenticated` project でログイン状態なし。
 *
 * 各種パスは `tests/e2e/` 配下に集約する。
 * Phase 2 でワーカー並列化 (workers: 4 + ワーカー別 DB) に拡張する。
 */
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false, // Phase 1 は単一 DB のため並列化しない
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",

  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || "http://localhost:3000",
    trace: "on-first-retry",
    video: "retain-on-failure",
  },

  globalSetup: require.resolve("./tests/e2e/globalSetup.ts"),

  projects: [
    {
      name: "unauthenticated",
      testMatch: /tests\/e2e\/auth\/.*\.spec\.ts/,
      use: { ...devices["Desktop Chrome"], locale: "ja-JP" },
    },
    {
      name: "authenticated",
      testIgnore: /tests\/e2e\/auth\/.*\.spec\.ts/,
      use: { ...devices["Desktop Chrome"], locale: "ja-JP" },
    },
  ],

  // ローカル/CI ともに Next.js を `next start` で起動する。
  // CI では composite action で起動済みなので reuseExistingServer: true。
  webServer: process.env.CI
    ? undefined
    : {
        command: "npm run start",
        url: "http://localhost:3000",
        reuseExistingServer: true,
        timeout: 120_000,
      },
});
