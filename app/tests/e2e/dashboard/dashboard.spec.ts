import { test, expect } from "../fixtures/authenticated-test";

import { resetDatabase } from "../utils/reset-db";
import { createTileset, createDatasource } from "../fixtures/factories";
import { loginAsAdmin } from "../utils/session";

test.beforeAll(async () => {
  await loginAsAdmin();
  await resetDatabase();
  await createTileset({ name: "smoke-tileset-1", type: "vector" });
  await createTileset({ name: "smoke-tileset-2", type: "raster" });
  await createDatasource({
    name: "smoke-ds-1",
    url: "https://example.com/sample.pmtiles",
    type: "pmtiles",
  });
});

test("DASH-01 @smoke ダッシュボードに各カウントが表示される", async ({ page }) => {
  await page.goto("/");

  const tilesetsCount = page.getByTestId("dashboard-tilesets-count");
  const featuresCount = page.getByTestId("dashboard-features-count");
  const datasourcesCount = page.getByTestId("dashboard-datasources-count");

  await expect(tilesetsCount).toBeVisible();
  await expect(featuresCount).toBeVisible();
  await expect(datasourcesCount).toBeVisible();

  // tilesets は 2 件 + datasource 用に auto 作成された 1 件 = 3 件以上
  await expect(tilesetsCount).toHaveText(/[2-9]|\d{2,}/);
});

test("DASH-02 更新ボタンで件数が再取得される", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("dashboard-tilesets-count")).toBeVisible();

  // ボタンクリックで /api/tilesets が再 fetch されることを network 監視で確認。
  // dashboard は API 直叩き (`api.listTilesets`) なので
  // `/api/tilesets` (Fly API or proxied) への GET を監視する。
  const tilesetsRequest = page.waitForRequest(
    (req) => req.url().includes("/api/tilesets") && req.method() === "GET",
  );
  await page.getByTestId("dashboard-refresh").click();
  await tilesetsRequest;

  // 再取得後もカウントが visible
  await expect(page.getByTestId("dashboard-tilesets-count")).toBeVisible();
});
