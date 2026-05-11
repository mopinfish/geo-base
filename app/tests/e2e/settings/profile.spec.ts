import { test, expect } from "../fixtures/authenticated-test";

import { resetDatabase } from "../utils/reset-db";
import { loginAsAdmin } from "../utils/session";

/**
 * ST-01: /settings/profile で name を更新できる。
 *
 * useAuth() の値は authClient.refresh() 経由でセットされるため、
 * フィールドが反映されるまで待ってから操作する。
 */
test.describe("Settings - profile", () => {
  test.beforeAll(async () => {
    await loginAsAdmin();
    await resetDatabase();
    // resetDatabase は admin user を再作成するため再ログインしておく。
    await loginAsAdmin();
  });

  test("ST-01 プロフィール名を更新できる (再読み込み後も反映)", async ({ page }) => {
    await page.goto("/settings/profile");

    const nameInput = page.getByTestId("profile-name");
    await expect(nameInput).toBeVisible({ timeout: 10_000 });

    const newName = `E2E Admin (${Date.now()})`;
    await nameInput.fill(newName);
    await page.getByTestId("profile-submit").click();

    await expect(page.getByTestId("profile-success")).toBeVisible();

    // 再読み込みしても新しい値が残る。
    await page.reload();
    await expect(page.getByTestId("profile-name")).toHaveValue(newName, {
      timeout: 10_000,
    });
  });
});
