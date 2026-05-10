import { test, expect } from "@playwright/test";

import { resetDatabase } from "../utils/reset-db";
import {
  E2E_ADMIN_EMAIL,
  E2E_ADMIN_PASSWORD,
} from "../globalSetup";

test.beforeAll(async () => {
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

  await page.getByTestId("sidebar-logout").click();
  await page.waitForURL(/\/login(\?|$)/);

  await page.goto("/tilesets");
  await page.waitForURL(/\/login(\?|$)/);
  await expect(page).toHaveURL(/\/login(\?|$)/);
});
