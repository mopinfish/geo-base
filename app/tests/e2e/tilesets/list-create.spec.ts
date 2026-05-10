import { test, expect } from "../fixtures/authenticated-test";

import { resetDatabase } from "../utils/reset-db";
import { createTileset } from "../fixtures/factories";
import { loginAsAdmin } from "../utils/session";

test.beforeAll(async () => {
  await loginAsAdmin();
  await resetDatabase();
});

test("TS-01 @smoke タイルセット一覧が表示される", async ({ page }) => {
  await createTileset({ name: "ts-list-smoke-A", type: "vector" });
  await createTileset({ name: "ts-list-smoke-B", type: "raster" });

  await page.goto("/tilesets");

  const rows = page.getByTestId("tileset-list-row");
  await expect(rows).toHaveCount(2, { timeout: 10_000 });
  await expect(page.getByText("ts-list-smoke-A")).toBeVisible();
  await expect(page.getByText("ts-list-smoke-B")).toBeVisible();
});

test("TS-07 @smoke タイルセット新規作成 → 詳細ページへ遷移", async ({ page }) => {
  await page.goto("/tilesets");
  await page.getByTestId("tileset-create-link").click();
  await page.waitForURL("/tilesets/new");

  await page.getByTestId("tileset-form-name").fill("ts-create-smoke");
  await page.getByTestId("tileset-form-submit").click();

  await page.waitForURL(/\/tilesets\/[^/]+(\?|$)/, { timeout: 15_000 });
  // 詳細ページの h1 (`<h1>{tileset.name}</h1>`) が hydrate されるまで待つ。
  // 名前を heading role で待つことで、ローディング状態の他要素にマッチしない。
  await expect(
    page.getByRole("heading", { name: "ts-create-smoke" }),
  ).toBeVisible({ timeout: 15_000 });
});
