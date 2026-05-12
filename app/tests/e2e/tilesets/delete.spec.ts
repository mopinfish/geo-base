import { test, expect } from "../fixtures/authenticated-test";

import { resetDatabase } from "../utils/reset-db";
import { createTileset } from "../fixtures/factories";
import { loginAsAdmin } from "../utils/session";

/**
 * 詳細ページからの単体削除 (TS-11)。
 *
 * `DeleteTilesetDialog` は trigger ボタンと AlertDialog の確定の二段階。
 * 確定ボタンは `data-testid="tileset-delete-confirm"` で取得する
 * (Radix Portal × Playwright headless の干渉を避けるため role ベースは使わない)。
 * 確定後 `/tilesets` に遷移し、データベースから消えていれば一覧 0 件。
 */
test.beforeAll(async () => {
  await loginAsAdmin();
});

test("TS-11 詳細ページから削除", async ({ page }) => {
  await resetDatabase();
  const tileset = await createTileset({
    name: "ts-delete-smoke",
    type: "vector",
    isPublic: true,
  });

  await page.goto(`/tilesets/${tileset.id}`);
  await expect(
    page.getByRole("heading", { name: "ts-delete-smoke" }),
  ).toBeVisible({ timeout: 10_000 });

  await page.getByTestId("tileset-delete-button").click();
  // AlertDialog の確定ボタンは data-testid で直接取得する（Radix Portal 回避）。
  await page.getByTestId("tileset-delete-confirm").click();

  await page.waitForURL("/tilesets", { timeout: 15_000 });
  await expect(page.getByTestId("tileset-list-row")).toHaveCount(0, {
    timeout: 10_000,
  });
});
