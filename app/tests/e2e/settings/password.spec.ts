import { test, expect } from "../fixtures/authenticated-test";
import { request } from "@playwright/test";

import { resetDatabase } from "../utils/reset-db";
import {
  loginAsAdmin,
  E2E_ADMIN_EMAIL,
  E2E_ADMIN_PASSWORD,
} from "../utils/session";

const APP_BASE = process.env.PLAYWRIGHT_BASE_URL || "http://localhost:3000";
const TEMP_PASSWORD = "E2E-temp-7!";

/**
 * ST-02: パスワード変更。
 *
 * 重要: 変更後は API 側で全 refresh token が revoke + フロントが
 * `await authClient.logout(); router.push("/login?password_changed=1")` するため
 * admin session が無効化される。後続テストへの影響を防ぐため、テスト末尾で
 * **必ず元のパスワードに戻す** + loginAsAdmin() で session を再生成する。
 *
 * パスワード変更を 2 回行うため UI ではなく `/api/auth/me/password` を直接叩く
 * 形にしている (UI 経由でも可能だが、リロード/UI ナビゲーションが入ると
 * fixture 側 cookie が古くなり flaky になる)。 UI は 1 回目だけ E2E で踏み、
 * 戻しは API で確実に。
 */
test.describe("Settings - password", () => {
  test.beforeAll(async () => {
    await loginAsAdmin();
    await resetDatabase();
    await loginAsAdmin();
  });

  test("ST-02 パスワードを変更してから元に戻す", async ({ page }) => {
    // --- ステップ 1: UI 経由で TEMP_PASSWORD に変更 -----------------------
    await page.goto("/settings/password");

    await page
      .getByTestId("password-current")
      .fill(E2E_ADMIN_PASSWORD);
    await page.getByTestId("password-next").fill(TEMP_PASSWORD);
    await page.getByTestId("password-submit").click();

    // 変更成功時は /login?password_changed=1 へ遷移する。
    await page.waitForURL(/\/login\?password_changed=1/, { timeout: 15_000 });

    // --- ステップ 2: API で TEMP → 元の admin password に戻す --------------
    // /api/auth/me/password は require_auth のため、まず TEMP_PASSWORD で
    // ログインして access_token を取得する。
    const ctx = await request.newContext({ baseURL: APP_BASE });
    try {
      const loginRes = await ctx.post("/api/auth/login", {
        data: { email: E2E_ADMIN_EMAIL, password: TEMP_PASSWORD },
      });
      expect(loginRes.ok()).toBeTruthy();
      const { access_token } = (await loginRes.json()) as {
        access_token: string;
      };

      const changeRes = await ctx.post("/api/auth/me/password", {
        headers: { Authorization: `Bearer ${access_token}` },
        data: {
          current_password: TEMP_PASSWORD,
          new_password: E2E_ADMIN_PASSWORD,
        },
      });
      // 204 No Content
      expect(changeRes.status()).toBe(204);
    } finally {
      await ctx.dispose();
    }

    // --- ステップ 3: 後続テストのため admin session を作り直す ------------
    await loginAsAdmin();
  });
});
