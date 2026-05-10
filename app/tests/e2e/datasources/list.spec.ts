import { test, expect } from "../fixtures/authenticated-test";

import { resetDatabase } from "../utils/reset-db";
import { createDatasource } from "../fixtures/factories";
import { loginAsAdmin } from "../utils/session";

test.beforeAll(async () => {
  await loginAsAdmin();
  await resetDatabase();
  await createDatasource({
    name: "ds-pmtiles-smoke",
    url: "https://example.com/sample.pmtiles",
    type: "pmtiles",
  });
  await createDatasource({
    name: "ds-cog-smoke",
    url: "https://example.com/sample.tif",
    type: "cog",
  });
});

test("DS-01 @smoke データソース一覧と type フィルタが動く", async ({ page }) => {
  await page.goto("/datasources");

  const rows = page.getByTestId("datasource-list-row");
  await expect(rows).toHaveCount(2);

  // type フィルタは <select> ではなくボタン群 (variant トグル) なので、
  // PMTiles ボタンをクリックして絞り込む。
  await page.getByTestId("datasource-filter-type-pmtiles").click();
  await expect(rows).toHaveCount(1);
  await expect(page.getByText("ds-pmtiles-smoke")).toBeVisible();
});
