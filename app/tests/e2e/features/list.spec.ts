import { test, expect } from "../fixtures/authenticated-test";

import { resetDatabase } from "../utils/reset-db";
import { createTileset, createFeature } from "../fixtures/factories";
import { loginAsAdmin } from "../utils/session";

test.beforeAll(async () => {
  await loginAsAdmin();
  await resetDatabase();
  // /features ページは tileset_id 未指定 (= 全件タブ) では public tileset の
  // features しか返さない (api/lib/routers/features.py の list_features 参照)。
  // smoke 用に明示的に public で作成する。
  const tileset = await createTileset({
    name: "ft-list-smoke",
    type: "vector",
    isPublic: true,
  });
  await createFeature({
    tilesetId: tileset.id,
    layer: "points",
    geometry: { type: "Point", coordinates: [139.767, 35.681] },
    properties: { name: "Tokyo" },
  });
  await createFeature({
    tilesetId: tileset.id,
    layer: "points",
    geometry: { type: "Point", coordinates: [135.502, 34.693] },
    properties: { name: "Osaka" },
  });
});

test("FT-01 @smoke フィーチャー一覧が表示される", async ({ page }) => {
  await page.goto("/features");

  const rows = page.getByTestId("feature-list-row");
  await expect(rows).toHaveCount(2, { timeout: 10_000 });
});
