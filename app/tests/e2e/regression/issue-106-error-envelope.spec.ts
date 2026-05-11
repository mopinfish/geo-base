/**
 * Issue #106 (i18n Phase 2b) — API レスポンスが `{error: {code, message}}`
 * envelope に切り替わったあとも、Admin UI のエラー表示が日本語化される
 * (英語 `message` がそのまま画面に出てこない) ことを確認する regression。
 *
 * 旧来 (Phase 2a まで) は API が `{detail: "..."}` の英語文字列を返し、
 * UI は `new Error(detail)` でそのまま画面表示していた。Phase 2b 以降は
 * `app/src/lib/api-errors.ts` の `translateApiError()` 経由で日本語に
 * 変換するため、AUTH-02 相当 (誤資格情報) の login error が日本語表示
 * されることをスナップ的に検証する。
 */

import { test, expect } from "@playwright/test";

import { resetDatabase } from "../utils/reset-db";

test.describe("Issue #106 regression — envelope error → JA translation", () => {
  test.beforeAll(async () => {
    await resetDatabase();
  });

  test("@regression 誤資格情報のログインで日本語エラーが表示される", async ({
    page,
  }) => {
    await page.goto("/login");
    await page.getByTestId("login-email").fill("wrong@example.com");
    await page.getByTestId("login-password").fill("wrong-password-XXX");
    await page.getByTestId("login-submit").click();

    // 日本語 fallback ("メールアドレスまたはパスワードが正しくありません") が
    // 表示されること。英語の "Invalid email or password" がそのまま出ていた
    // 旧挙動の回帰防止。
    await expect(page.getByTestId("login-error")).toContainText(
      /メールアドレスまたはパスワード/,
      { timeout: 5_000 },
    );
  });
});
