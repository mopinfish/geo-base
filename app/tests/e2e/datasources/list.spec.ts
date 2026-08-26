import { test, expect } from "../fixtures/authenticated-test";

import { resetDatabase } from "../utils/reset-db";
import { createDatasource } from "../fixtures/factories";
import { loginAsAdmin } from "../utils/session";

test.describe("Datasources list - smoke", () => {
  test.beforeAll(async () => {
    await loginAsAdmin();
    await resetDatabase();
    await createDatasource({
      name: "ds-pmtiles-smoke",
      url: "https://example.com/sample.pmtiles",
      type: "pmtiles",
    });
    await createDatasource({
      name: "ds-cog-smoke",
      url: "https://example.com/sample.tif",
      type: "cog",
    });
  });

  test("DS-01 @smoke データソース一覧と type フィルタが動く", async ({ page }) => {
    await page.goto("/datasources");

    const rows = page.getByTestId("datasource-list-row");
    await expect(rows).toHaveCount(2);

    // type フィルタは <select> ではなくボタン群 (variant トグル) なので、
    // PMTiles ボタンをクリックして絞り込む。
    await page.getByTestId("datasource-filter-type-pmtiles").click();
    await expect(rows).toHaveCount(1);
    await expect(page.getByText("ds-pmtiles-smoke")).toBeVisible();
  });
});

test.describe("Datasources list - include-private toggle", () => {
  test.beforeAll(async () => {
    await loginAsAdmin();
    await resetDatabase();
    // 親 tileset を public / private で 1 件ずつ作成。
    // datasource 自体には is_public フラグは無く、親 tileset の設定を引き継ぐ。
    await createDatasource({
      name: "ds-public",
      url: "https://example.com/public.pmtiles",
      type: "pmtiles",
      isPublic: true,
    });
    await createDatasource({
      name: "ds-private",
      url: "https://example.com/private.pmtiles",
      type: "pmtiles",
      isPublic: false,
    });
  });

  test("DS-02 include-private トグルで public のみ / 全件を切り替えられる", async ({
    page,
  }) => {
    await page.goto("/datasources");

    const rows = page.getByTestId("datasource-list-row");
    const toggle = page.getByTestId("datasource-include-private-toggle");

    // 初期状態は include_private=true。public + private の両方が見える。
    await expect(toggle).toBeChecked();
    await expect(rows).toHaveCount(2);

    // OFF にすると private が除外されて public のみ残る。
    await toggle.uncheck();
    await expect(rows).toHaveCount(1);
    await expect(page.getByText("ds-public")).toBeVisible();
    await expect(page.getByText("ds-private")).toHaveCount(0);

    // ON に戻すと再び 2 件。
    await toggle.check();
    await expect(rows).toHaveCount(2);
  });
});

test.describe("Datasources list - bulk delete", () => {
  test.beforeAll(async () => {
    await loginAsAdmin();
    await resetDatabase();
    await createDatasource({
      name: "ds-bulk-1",
      url: "https://example.com/bulk1.pmtiles",
      type: "pmtiles",
    });
    await createDatasource({
      name: "ds-bulk-2",
      url: "https://example.com/bulk2.pmtiles",
      type: "pmtiles",
    });
  });

  test("DS-03 全選択 → 一括削除で 0 件になる", async ({ page }) => {
    await page.goto("/datasources");

    const rows = page.getByTestId("datasource-list-row");
    await expect(rows).toHaveCount(2);

    // 全選択 checkbox を ON。一括操作バーが表示される。
    await page.getByTestId("datasource-select-all").check();
    await page.getByTestId("datasource-bulk-delete").click();

    // AlertDialog の confirm。
    await page.getByTestId("datasource-bulk-delete-confirm").click();

    // 削除完了後、一覧が空になる。
    await expect(rows).toHaveCount(0);
    await expect(page.getByTestId("datasource-empty-register-button")).toBeVisible();
  });
});
