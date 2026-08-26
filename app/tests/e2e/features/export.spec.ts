import { test, expect } from "../fixtures/authenticated-test";

import { resetDatabase } from "../utils/reset-db";
import { createTileset, createFeature } from "../fixtures/factories";
import { loginAsAdmin } from "../utils/session";

/**
 * Features の GeoJSON / CSV エクスポート (FT-07 / FT-08)。
 *
 * 実装はクライアント側で `URL.createObjectURL(blob)` → `<a download>` をクリック
 * する形式 (page.tsx handleExport)。Playwright の `page.waitForEvent('download')`
 * で `<a>` クリック由来の download trigger をキャッチできる。
 *
 * 注: 「エクスポート」ボタンは `selectedTileset === "all"` の間 disabled。先に
 * tileset セレクタで対象 tileset を選択してから dialog を開く必要がある。
 */
test.describe("Features export", () => {
  test.beforeAll(async () => {
    await loginAsAdmin();
  });

  test("FT-07 GeoJSON エクスポート", async ({ page }) => {
    await resetDatabase();
    const tileset = await createTileset({
      name: "ft-export-geojson",
      type: "vector",
      isPublic: true,
    });
    await createFeature({
      tilesetId: tileset.id,
      layer: "points",
      geometry: { type: "Point", coordinates: [139.7, 35.6] },
      properties: { name: "T" },
    });

    await page.goto("/features");
    // 1 件 hydrate を待つ。
    await expect(page.getByTestId("feature-list-row")).toHaveCount(1, {
      timeout: 10_000,
    });

    // tileset を選択 (これでヘッダの「エクスポート」ボタンが有効になる)。
    await page.getByTestId("feature-filter-tileset").selectOption(tileset.id);
    await expect(page.getByTestId("feature-export-open")).toBeEnabled({
      timeout: 5_000,
    });

    // Dialog を開く。
    await page.getByTestId("feature-export-open").click();
    // 既定で GeoJSON が選択されている状態。念のため radio をクリックして固定。
    await page.getByTestId("feature-export-format-geojson").check();

    // download trigger を待ってから submit。
    const downloadPromise = page.waitForEvent("download");
    await page.getByTestId("feature-export-submit").click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/\.geojson$/i);
  });

  test("FT-08 CSV エクスポート", async ({ page }) => {
    await resetDatabase();
    const tileset = await createTileset({
      name: "ft-export-csv",
      type: "vector",
      isPublic: true,
    });
    await createFeature({
      tilesetId: tileset.id,
      layer: "points",
      geometry: { type: "Point", coordinates: [139.7, 35.6] },
      properties: { name: "T" },
    });

    await page.goto("/features");
    await expect(page.getByTestId("feature-list-row")).toHaveCount(1, {
      timeout: 10_000,
    });

    await page.getByTestId("feature-filter-tileset").selectOption(tileset.id);
    await expect(page.getByTestId("feature-export-open")).toBeEnabled({
      timeout: 5_000,
    });

    await page.getByTestId("feature-export-open").click();
    // CSV radio に切り替える。
    await page.getByTestId("feature-export-format-csv").check();

    const downloadPromise = page.waitForEvent("download");
    await page.getByTestId("feature-export-submit").click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/\.csv$/i);
  });
});
