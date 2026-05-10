import { test, expect } from "@playwright/test";

import { resetDatabase } from "../utils/reset-db";
import { E2E_ADMIN_EMAIL, E2E_ADMIN_PASSWORD } from "../utils/session";

test.beforeAll(async () => {
  await resetDatabase();
});

test("AUTH-02 誤った認証情報 → エラー表示、/login 留まる", async ({ page }) => {
  await page.goto("/login");
  await page.getByTestId("login-email").fill(E2E_ADMIN_EMAIL);
  await page.getByTestId("login-password").fill("wrong-password!");
  await page.getByTestId("login-submit").click();

  await expect(page.getByTestId("login-error")).toBeVisible({ timeout: 5_000 });
  await expect(page).toHaveURL(/\/login(\?|$)/);
});

test("AUTH-03 /login?next=/tilesets ログイン後 → /tilesets にリダイレクト", async ({
  page,
}) => {
  await page.goto("/login?next=/tilesets");
  await page.getByTestId("login-email").fill(E2E_ADMIN_EMAIL);
  await page.getByTestId("login-password").fill(E2E_ADMIN_PASSWORD);
  await page.getByTestId("login-submit").click();

  await page.waitForURL(/\/tilesets(\?|$)/, { timeout: 15_000 });
});

test("AUTH-05 未認証で /tilesets → /login?next=/tilesets にリダイレクト", async ({
  page,
}) => {
  // unauthenticated project なので cookie なし
  await page.goto("/tilesets");
  await page.waitForURL(/\/login\?next=/, { timeout: 10_000 });
  const url = new URL(page.url());
  expect(url.searchParams.get("next")).toBe("/tilesets");
});
