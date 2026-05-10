import { test, expect } from "../fixtures/authenticated-test";

import { resetDatabase } from "../utils/reset-db";
import { createTileset, createFeature } from "../fixtures/factories";
import { loginAsAdmin } from "../utils/session";

/**
 * Features の CRUD: 新規作成 (Point/Polygon) / 編集 / 詳細 (FT-09〜FT-12)。
 *
 * FT-09 と FT-10: FeatureForm は MapLibre GL ベースの GeometryEditor で
 * 座標を入力する設計 (`@/components/map/GeometryEditor`)。マウスクリックや
 * マーカードラッグが必要で、Playwright で安定して操作するのが難しい (E2E
 * における flakiness の典型)。GeoJSON を文字列で直接入力するモードは
 * 現状の UI に存在せず、新規追加は本タスクの範囲外。Phase 3 で
 *   - FeatureForm に "GeoJSON 文字列入力" モードを追加するか
 *   - GeometryEditor を test-only に "fillCoordinates" hook 経由で操作する
 * のどちらかで対応する想定。今は test.skip。
 *
 * FT-11 と FT-12 は factory で feature を作成し、編集ページのプロパティ
 * 行 input と詳細ページのマップ要素を確認する形で実装している。
 */
test.describe("Features CRUD", () => {
  test.beforeAll(async () => {
    await loginAsAdmin();
  });

  test.skip(
    "FT-09 Point geometry で新規作成",
    // Reason: FeatureForm は MapLibre GL の GeometryEditor (マウスクリックで
    // 座標を打つ UI) のみで、Playwright から安定して座標を入れる手段が無い。
    // GeoJSON 文字列直接入力のフォールバックを追加してから本テストを有効化する
    // (Phase 3 予定)。
    () => {},
  );

  test.skip(
    "FT-10 Polygon geometry で新規作成",
    // Reason: FT-09 と同様。GeometryEditor のマウス操作 (連続クリックで頂点を
    // 打つ UI) を Playwright で stable に再現できないため、Phase 3 で
    // GeoJSON 直接入力モードを追加してから有効化する。
    () => {},
  );

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
    await expect(page.getByText("new-edited")).toBeVisible({
      timeout: 10_000,
    });
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
