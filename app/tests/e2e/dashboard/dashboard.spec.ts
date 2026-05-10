import { test, expect } from "@playwright/test";

import { resetDatabase } from "../utils/reset-db";
import { createTileset, createDatasource } from "../fixtures/factories";

test.beforeAll(async () => {
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
