import { test, expect } from "@playwright/test";

import { resetDatabase } from "../utils/reset-db";
import {
  E2E_ADMIN_EMAIL,
  E2E_ADMIN_PASSWORD,
} from "../utils/session";

test.beforeAll(async () => {
  // resetDatabase は認証不要なので unauthenticated project から直接呼べる。
  await resetDatabase();
});

test("AUTH-01 @smoke ログイン成功で / にリダイレクトされる", async ({ page }) => {
  await page.goto("/login");
  await page.getByTestId("login-email").fill(E2E_ADMIN_EMAIL);
  await page.getByTestId("login-password").fill(E2E_ADMIN_PASSWORD);
  await page.getByTestId("login-submit").click();

  await page.waitForURL("/");
  await expect(page).toHaveURL("/");
});

test("AUTH-04 @smoke ログアウトで /login に遷移しセッションがクリアされる", async ({
  page,
}) => {
  await page.goto("/login");
  await page.getByTestId("login-email").fill(E2E_ADMIN_EMAIL);
  await page.getByTestId("login-password").fill(E2E_ADMIN_PASSWORD);
  await page.getByTestId("login-submit").click();
  await page.waitForURL("/");

  // dashboard が hydrate 完了するまで待つ。これを入れずに即 click すると
  // React のイベントハンドラがバインドされる前にクリックが流れて
  // handleLogout が起動しないことがある。
  await expect(page.getByTestId("sidebar-logout")).toBeEnabled();

  // クリックと URL 遷移を並行で監視（race を避ける）
  await Promise.all([
    page.waitForURL(/\/login(\?|$)/, { timeout: 15_000 }),
    page.getByTestId("sidebar-logout").click(),
  ]);

  // セッションがクリアされていることを protected route で確認
  await page.goto("/tilesets");
  await page.waitForURL(/\/login(\?|$)/, { timeout: 10_000 });
  await expect(page).toHaveURL(/\/login(\?|$)/);
});
