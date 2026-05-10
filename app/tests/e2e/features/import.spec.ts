import path from "node:path";
import { test, expect } from "@playwright/test";

import { resetDatabase } from "../utils/reset-db";
import { createTileset } from "../fixtures/factories";

test.beforeAll(async () => {
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
