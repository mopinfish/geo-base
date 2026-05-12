/**
 * Issue #100 (Phase 3 a11y 監査) の受入条件 6 ページのうち、`/features` を
 * 担当する spec。
 *
 * 形式は `tilesets-list.spec.ts` / `api-keys.spec.ts` と同じ:
 *  - resetDatabase で空にした上で tileset + feature を 1 件作って、1 行
 *    状態を axe スキャン対象にする
 *  - axe-core を WCAG 2.1 AA タグで走らせ、serious / critical 違反のみを
 *    失敗扱い
 *  - `awaitReady: { testid: "feature-list-row" }` でデータロード完了を待つ
 */
import { test } from "../fixtures/authenticated-test";

import { createFeature, createTileset } from "../fixtures/factories";
import { resetDatabase } from "../utils/reset-db";
import { loginAsAdmin } from "../utils/session";
import { expectNoA11ySeriousViolations } from "./_helper";

test.describe("a11y: /features", () => {
  test.beforeAll(async () => {
    await loginAsAdmin();
    await resetDatabase();
    // /features ページは tileset_id 未指定 (= 全件タブ) では public tileset の
    // features しか返さない (api/lib/routers/features.py の list_features 参照)。
    // a11y spec で `feature-list-row` を visible 待ちするため public で作成。
    // 既存 `tests/e2e/features/list.spec.ts` と同じパターン
    // (Copilot PR #133 round 1 指摘)。
    const tileset = await createTileset({
      name: "a11y-feature-fixture",
      type: "vector",
      isPublic: true,
    });
    await createFeature({
      tilesetId: tileset.id,
      layer: "default",
      geometry: {
        type: "Point",
        coordinates: [139.7671, 35.6812],
      },
      properties: { name: "a11y-feature" },
    });
  });

  test("a11y: /features serious/critical 違反なし", async ({ page }) => {
    await page.goto("/features");
    await expectNoA11ySeriousViolations(page, {
      awaitReady: { testid: "feature-list-row" },
    });
  });
});
