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

/**
 * 一覧フィルタ系のコアケース (FT-02 / FT-03 / FT-04)。
 *
 * 上の FT-01 用 beforeAll とは独立に、各テストが冒頭で resetDatabase() してから
 * シードを作る方針。テスト順序に依存しない。
 *
 * 注: /features の tileset / limit セレクタはネイティブ <select> で実装されて
 * いる (Radix UI のポータル問題回避)。Tilesets 側 (Radix Select) と異なり、
 * Playwright の `selectOption()` がそのまま使える。
 */
test.describe("Features list filters", () => {
  test.beforeAll(async () => {
    await loginAsAdmin();
  });

  test("FT-02 tileset でフィルタ", async ({ page }) => {
    await resetDatabase();
    const tilesetA = await createTileset({
      name: "ft-filter-a",
      type: "vector",
      isPublic: true,
    });
    const tilesetB = await createTileset({
      name: "ft-filter-b",
      type: "vector",
      isPublic: true,
    });
    for (let i = 0; i < 2; i++) {
      await createFeature({
        tilesetId: tilesetA.id,
        layer: "points",
        geometry: { type: "Point", coordinates: [139.767 + i * 0.001, 35.681] },
        properties: { source: "A", idx: i },
      });
    }
    for (let i = 0; i < 2; i++) {
      await createFeature({
        tilesetId: tilesetB.id,
        layer: "points",
        geometry: { type: "Point", coordinates: [135.502 + i * 0.001, 34.693] },
        properties: { source: "B", idx: i },
      });
    }

    await page.goto("/features");
    // 初期表示は「すべてのタイルセット」= public 全件 = 4 件。
    await expect(page.getByTestId("feature-list-row")).toHaveCount(4, {
      timeout: 10_000,
    });

    // ネイティブ <select>: selectOption で value (tileset.id) を指定。
    await page
      .getByTestId("feature-filter-tileset")
      .selectOption(tilesetA.id);
    await expect(page.getByTestId("feature-list-row")).toHaveCount(2, {
      timeout: 5_000,
    });
  });

  test("FT-03 プロパティ検索でフィルタ", async ({ page }) => {
    await resetDatabase();
    const tileset = await createTileset({
      name: "ft-search",
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
    await createFeature({
      tilesetId: tileset.id,
      layer: "points",
      geometry: { type: "Point", coordinates: [136.882, 35.181] },
      properties: { name: "Nagoya" },
    });

    await page.goto("/features");
    // 3 件 hydrate されるのを待ってから検索する。
    await expect(page.getByTestId("feature-list-row")).toHaveCount(3, {
      timeout: 10_000,
    });

    // 検索はクライアント側フィルタ (page.tsx の filteredFeatures)。
    // properties の JSON 全体に対する部分一致なので "Tokyo" でヒットするのは 1 件。
    await page.getByTestId("feature-search-input").fill("Tokyo");
    await expect(page.getByTestId("feature-list-row")).toHaveCount(1, {
      timeout: 5_000,
    });
  });

  test("FT-04 limit セレクタで件数変更", async ({ page }) => {
    await resetDatabase();
    const tileset = await createTileset({
      name: "ft-limit",
      type: "vector",
      isPublic: true,
    });
    // 50 件 bulk 作成。座標を微妙にずらして valid な geometry にする。
    for (let i = 0; i < 50; i++) {
      await createFeature({
        tilesetId: tileset.id,
        layer: "points",
        geometry: {
          type: "Point",
          coordinates: [139.767 + i * 0.001, 35.681],
        },
        properties: { idx: i },
      });
    }

    await page.goto("/features");
    // 既定 limit は 50 (page.tsx の useState(50))。最初に 50 件を待つ。
    await expect(page.getByTestId("feature-list-row")).toHaveCount(50, {
      timeout: 15_000,
    });

    // limit を 10 に。
    await page.getByTestId("feature-limit-select").selectOption("10");
    await expect(page.getByTestId("feature-list-row")).toHaveCount(10, {
      timeout: 5_000,
    });

    // limit を 50 に戻す。
    await page.getByTestId("feature-limit-select").selectOption("50");
    await expect(page.getByTestId("feature-list-row")).toHaveCount(50, {
      timeout: 10_000,
    });
  });
});
