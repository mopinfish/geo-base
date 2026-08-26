import path from "node:path";
import { test, expect } from "../fixtures/authenticated-test";

import { resetDatabase } from "../utils/reset-db";
import { createTileset } from "../fixtures/factories";
import { loginAsAdmin } from "../utils/session";

test.beforeAll(async () => {
  await loginAsAdmin();
  await resetDatabase();
});

test("FT-13 @smoke GeoJSON ファイルを drag-drop で import できる", async ({ page }) => {
  const tileset = await createTileset({ name: "ft-import-smoke", type: "vector" });

  await page.goto("/features/import");
  await page.getByTestId("import-tileset-select").selectOption(tileset.id);
  await page
    .getByTestId("import-file-input")
    .setInputFiles(path.resolve(__dirname, "../fixtures/sample.geojson"));
  await page.getByTestId("import-submit").click();

  await expect(page.getByTestId("import-success-message")).toBeVisible({
    timeout: 15_000,
  });
});

test("FT-14 不正な GeoJSON ファイル → エラー表示", async ({ page }) => {
  const tileset = await createTileset({
    name: "ft-import-error",
    type: "vector",
    isPublic: true,
  });

  await page.goto("/features/import");
  await page.getByTestId("import-tileset-select").selectOption(tileset.id);

  // 壊れた GeoJSON を input にセットすると GeoJSONDropzone の parseGeoJSON で
  // JSON.parse が SyntaxError を投げ、`onError` 経由でページ上のエラー表示が出る。
  // 不正ファイルでは parsedGeoJSON が null のため、`import-submit` ボタンは表示されない。
  // (page.tsx で `{parsedGeoJSON && status !== "success" && ...}` で gating されている)。
  await page
    .getByTestId("import-file-input")
    .setInputFiles(path.resolve(__dirname, "../fixtures/sample-broken.geojson"));

  await expect(page.getByTestId("import-error-message")).toBeVisible({
    timeout: 10_000,
  });
});
