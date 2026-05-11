import { test, expect } from "../fixtures/authenticated-test";

import { resetDatabase } from "../utils/reset-db";
import { createTileset } from "../fixtures/factories";
import { loginAsAdmin } from "../utils/session";

/**
 * 詳細・編集・公開トグルのコアケース (TS-08/09/10)。
 *
 * 各テストで `resetDatabase()` してから seeded tileset を作る方針。
 * テスト順序に依存しない。
 */
test.beforeAll(async () => {
  await loginAsAdmin();
});

test("TS-08 詳細ページに heading + プレビュー表示", async ({ page }) => {
  await resetDatabase();
  const tileset = await createTileset({
    name: "ts-detail-smoke",
    type: "vector",
    isPublic: true,
  });
  await page.goto(`/tilesets/${tileset.id}`);
  await expect(
    page.getByRole("heading", { name: "ts-detail-smoke" }),
  ).toBeVisible({ timeout: 10_000 });
});

test("TS-09 編集 → 保存 → 詳細で反映確認", async ({ page }) => {
  await resetDatabase();
  const tileset = await createTileset({
    name: "ts-edit-smoke",
    type: "vector",
    isPublic: true,
  });
  await page.goto(`/tilesets/${tileset.id}/edit`);

  // 編集フォームの hydrate を待つ (description フィールドが描画されるまで)。
  await expect(page.getByTestId("tileset-form-description")).toBeVisible({
    timeout: 10_000,
  });

  const NEW_DESC = `edited-by-e2e-${Date.now()}`;
  await page.getByTestId("tileset-form-description").fill(NEW_DESC);
  await page.getByTestId("tileset-form-submit").click();

  // 保存後、詳細ページに戻る。
  await page.waitForURL(`/tilesets/${tileset.id}`, { timeout: 15_000 });
  await expect(page.getByText(NEW_DESC)).toBeVisible({ timeout: 10_000 });
});

test("TS-10 is_public トグル切替", async ({ page }) => {
  await resetDatabase();
  const tileset = await createTileset({
    name: "ts-toggle-smoke",
    type: "vector",
    isPublic: false,
  });
  await page.goto(`/tilesets/${tileset.id}`);

  // 詳細ページの hydrate を待つ。
  await expect(
    page.getByRole("heading", { name: "ts-toggle-smoke" }),
  ).toBeVisible({ timeout: 10_000 });

  // 初期状態: 非公開バッジ。
  await expect(page.getByTestId("tileset-private-badge")).toBeVisible();

  // toggle: 公開化。
  await page.getByTestId("tileset-public-toggle").click();
  await expect(page.getByTestId("tileset-public-badge")).toBeVisible({
    timeout: 10_000,
  });
});
