import { test, expect } from "../fixtures/authenticated-test";

import { resetDatabase } from "../utils/reset-db";
import { createTileset, createFeature } from "../fixtures/factories";
import { loginAsAdmin } from "../utils/session";

/**
 * Features の一括選択 + 一括削除 / 一括更新 (FT-05 / FT-06)。
 *
 * /features の bulk delete は AlertDialog (preview API → 確定) のパターン。
 * bulk update は Dialog で properties JSON を入れて submit する。
 *
 * 全テストで tileset を `isPublic: true` で作成 (API の list_features が
 * tileset_id 未指定時は public のみ返す制約)。
 */
test.describe("Features bulk operations", () => {
  test.beforeAll(async () => {
    await loginAsAdmin();
  });

  test("FT-05 一括選択 + 一括削除", async ({ page }) => {
    await resetDatabase();
    const tileset = await createTileset({
      name: "ft-bulk-delete",
      type: "vector",
      isPublic: true,
    });
    for (let i = 0; i < 5; i++) {
      await createFeature({
        tilesetId: tileset.id,
        layer: "points",
        geometry: {
          type: "Point",
          coordinates: [139.7 + i * 0.001, 35.6],
        },
        properties: { idx: i },
      });
    }

    await page.goto("/features");
    await expect(page.getByTestId("feature-list-row")).toHaveCount(5, {
      timeout: 10_000,
    });

    // ヘッダの全選択 checkbox。
    await page.getByTestId("feature-select-all").click();
    // 一括削除 → preview API → AlertDialog open。
    await page.getByTestId("feature-bulk-delete").click();
    await page.getByTestId("feature-bulk-delete-confirm").click();

    await expect(page.getByTestId("feature-list-row")).toHaveCount(0, {
      timeout: 15_000,
    });
  });

  test("FT-06 一括更新でプロパティを書き換える", async ({ page }) => {
    await resetDatabase();
    const tileset = await createTileset({
      name: "ft-bulk-update",
      type: "vector",
      isPublic: true,
    });
    for (let i = 0; i < 3; i++) {
      await createFeature({
        tilesetId: tileset.id,
        layer: "points",
        geometry: {
          type: "Point",
          coordinates: [139.7 + i * 0.001, 35.6],
        },
        properties: { tag: "old", idx: i },
      });
    }

    await page.goto("/features");
    await expect(page.getByTestId("feature-list-row")).toHaveCount(3, {
      timeout: 10_000,
    });

    await page.getByTestId("feature-select-all").click();
    await page.getByTestId("feature-bulk-update").click();
    // Dialog 内の properties textarea に JSON を入れて submit。
    // mergeProperties チェックボックスは既定 ON なので tag フィールドは
    // "old" → "updated" に置き換わり、他のプロパティ (idx) は残る。
    await page
      .getByTestId("feature-bulk-update-properties")
      .fill('{"tag":"updated"}');
    await page.getByTestId("feature-bulk-update-submit").click();

    // 更新完了後、再 fetch されたリストには成功メッセージが表示される。
    await expect(page.getByTestId("feature-success-message")).toBeVisible({
      timeout: 15_000,
    });

    // リストの行数自体は変わらない (3 件のまま)。
    await expect(page.getByTestId("feature-list-row")).toHaveCount(3);
  });
});
