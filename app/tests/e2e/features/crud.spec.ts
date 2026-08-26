import { test, expect } from "../fixtures/authenticated-test";

import { resetDatabase } from "../utils/reset-db";
import { createTileset, createFeature } from "../fixtures/factories";
import { loginAsAdmin } from "../utils/session";

/**
 * Features の CRUD: 新規作成 (Point/Polygon) / 編集 / 詳細 (FT-09〜FT-12)。
 *
 * FT-09 と FT-10: FeatureForm に Phase 3 で「GeoJSON 直接入力」モード
 * (`feature-form-mode-geojson` タブ + `feature-form-geometry-text` textarea)
 * を追加し、MapLibre のマウス操作に依存せず geometry を入れられるように
 * したので有効化済み。`/features/new` で tileset を選び、GeoJSON 文字列を
 * fill して submit し、詳細ページ (`/features/<id>`) への遷移を待つ。
 *
 * FT-11 と FT-12 は factory で feature を作成し、編集ページのプロパティ
 * 行 input と詳細ページのマップ要素を確認する形で実装している。
 */
test.describe("Features CRUD", () => {
  test.beforeAll(async () => {
    await loginAsAdmin();
  });

  test("FT-09 Point geometry で新規作成", async ({ page }) => {
    await resetDatabase();
    const tileset = await createTileset({
      name: "ft-create-point",
      type: "vector",
      isPublic: true,
    });

    await page.goto("/features/new");
    // フォームの hydrate (tileset list fetch) を待つ。
    await expect(page.getByTestId("feature-form-tileset")).toBeVisible({
      timeout: 15_000,
    });

    // tileset 選択 (shadcn Select は trigger をクリック → option をクリック)。
    await page.getByTestId("feature-form-tileset").click();
    await page.getByRole("option", { name: tileset.name }).click();

    // GeoJSON 直接入力モードに切替えて Point を流し込む。
    await page.getByTestId("feature-form-mode-geojson").click();
    await page
      .getByTestId("feature-form-geometry-text")
      .fill('{"type":"Point","coordinates":[139.767,35.681]}');

    // Submit ボタンが有効になるのを待ってからクリック。
    const submit = page.getByTestId("feature-form-submit");
    await expect(submit).toBeEnabled({ timeout: 5_000 });
    await submit.click();

    // 作成後は `/features/<id>` (edit でも new でもない) に遷移する。
    await page.waitForURL(/\/features\/[a-f0-9-]+$/, { timeout: 15_000 });
  });

  test("FT-10 Polygon geometry で新規作成", async ({ page }) => {
    await resetDatabase();
    const tileset = await createTileset({
      name: "ft-create-polygon",
      type: "vector",
      isPublic: true,
    });

    await page.goto("/features/new");
    await expect(page.getByTestId("feature-form-tileset")).toBeVisible({
      timeout: 15_000,
    });

    await page.getByTestId("feature-form-tileset").click();
    await page.getByRole("option", { name: tileset.name }).click();

    // Polygon の coordinates は [outerRing, ...holes]、外環は閉じた ring。
    const polygon = {
      type: "Polygon",
      coordinates: [
        [
          [139.7, 35.6],
          [139.8, 35.6],
          [139.8, 35.7],
          [139.7, 35.6],
        ],
      ],
    };
    await page.getByTestId("feature-form-mode-geojson").click();
    await page
      .getByTestId("feature-form-geometry-text")
      .fill(JSON.stringify(polygon));

    const submit = page.getByTestId("feature-form-submit");
    await expect(submit).toBeEnabled({ timeout: 5_000 });
    await submit.click();

    await page.waitForURL(/\/features\/[a-f0-9-]+$/, { timeout: 15_000 });
  });

  test("FT-11 プロパティ編集", async ({ page }) => {
    await resetDatabase();
    const tileset = await createTileset({
      name: "ft-edit",
      type: "vector",
      isPublic: true,
    });
    const feature = await createFeature({
      tilesetId: tileset.id,
      layer: "points",
      geometry: { type: "Point", coordinates: [139.7, 35.6] },
      properties: { name: "old" },
    });

    await page.goto(`/features/${feature.id}/edit`);
    // 編集フォームの hydrate を待つ (タイルセット trigger が見えるまで)。
    await expect(page.getByTestId("feature-form-tileset")).toBeVisible({
      timeout: 15_000,
    });

    // FeatureForm は properties を `{key, value}[]` の行入力で扱う
    // (textarea/JSON ではない)。既存プロパティ "name" は initialData から
    // 1 行目に展開済み。value 側の input を上書きして保存する。
    const valueInputs = page.getByTestId("feature-form-property-value");
    await expect(valueInputs).toHaveCount(1, { timeout: 5_000 });
    await valueInputs.first().fill("new-edited");

    await page.getByTestId("feature-form-submit").click();

    // 詳細ページに遷移するのを待つ (`/features/<id>` だが `/edit` で終わら
    // ないこと)。
    await page.waitForURL(`/features/${feature.id}`, { timeout: 15_000 });
    // 詳細ページのプロパティ表示で更新後の値が見える。
    // strict mode 違反を避けるため `feature-property-value` testid に絞る
    // (生 JSON プレビューにも値が出るため getByText では 2 件にマッチする)。
    await expect(
      page.getByTestId("feature-property-value").filter({ hasText: "new-edited" }),
    ).toBeVisible({ timeout: 10_000 });
  });

  test("FT-12 詳細ページにマップ表示", async ({ page }) => {
    await resetDatabase();
    const tileset = await createTileset({
      name: "ft-detail-map",
      type: "vector",
      isPublic: true,
    });
    const feature = await createFeature({
      tilesetId: tileset.id,
      layer: "points",
      geometry: { type: "Point", coordinates: [139.7, 35.6] },
      properties: { name: "T" },
    });

    await page.goto(`/features/${feature.id}`);
    await expect(page.getByTestId("feature-detail-map")).toBeVisible({
      timeout: 15_000,
    });
  });
});
