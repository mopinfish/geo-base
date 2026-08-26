/**
 * AUTH-06: access token 期限切れ → 自動 refresh で透明に継続。
 *
 * 設計:
 * - access_token_ttl_seconds = 900 (= 15 min) per api/lib/config.py
 * - authClient (app/src/lib/auth/client.ts) は expires_in - 60s で
 *   scheduleRefresh する仕組み。
 * - page.clock.install + fastForward で 16 分進めて refresh を発火させる。
 *
 * NOTE: 本ファイルは authenticated project で実行される必要があるため
 * `tests/e2e/auth/` 配下ではなく `tests/e2e/session/` 配下に置く
 * (`auth/*.spec.ts` は playwright.config.ts で unauthenticated に振り分けられる)。
 */
import { test, expect } from "../fixtures/authenticated-test";

import { resetDatabase } from "../utils/reset-db";
import { loginAsAdmin } from "../utils/session";
import { createTileset } from "../fixtures/factories";

test.describe("Auth token refresh", () => {
  test.beforeAll(async () => {
    await loginAsAdmin();
    await resetDatabase();
  });

  test("AUTH-06 access token 期限切れで自動 refresh される", async ({ page }) => {
    await createTileset({
      name: "auth-06-precheck",
      type: "vector",
      isPublic: true,
    });
    await page.goto("/tilesets");
    await expect(page.getByTestId("tileset-list-row")).toHaveCount(1, {
      timeout: 10_000,
    });

    // `/api/auth/refresh` への POST が実際に発行されたことを assert する
    // (Copilot PR #122 指摘)。`page.clock.fastForward` 中に
    // `authClient.scheduleRefresh()` の setTimeout が発火して refresh が
    // 走ってしまう場合があるため、waitForRequest は時間進行の **前** に
    // 仕掛けて取り逃しを防ぐ (Copilot PR #122 round 3 指摘)。
    const refreshRequest = page.waitForRequest(
      (req) =>
        req.url().includes("/api/auth/refresh") && req.method() === "POST",
      { timeout: 30_000 },
    );

    // 時間を 16 分進めて access token を期限切れにする。
    // install() が既に動いている場合のフォールバックとして runFor も用意。
    try {
      await page.clock.install({ time: new Date() });
      await page.clock.fastForward("16:00");
    } catch {
      await page.clock.runFor(960_000);
    }

    // reload して認証必須の API を再 fetch → authClient が refresh → 続行。
    await page.reload();
    await expect(page.getByTestId("tileset-list-row")).toHaveCount(1, {
      timeout: 15_000,
    });
    await refreshRequest;
  });
});
