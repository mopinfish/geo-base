import { test, expect } from "../fixtures/authenticated-test";

import { resetDatabase } from "../utils/reset-db";
import {
  createDatasource,
  createTileset,
  type CreatedTileset,
} from "../fixtures/factories";
import { loginAsAdmin } from "../utils/session";

/**
 * Datasources 作成テスト。
 *
 * UI フォームは `<input type="url">` + 内部 validate (`http(s)://` のみ許可) のため、
 * `s3://` スキーム経由の作成 (DS-05) はフォームから直接できない。これは upload
 * フローでバックエンドが内部 URL を組み立てる Issue #101 Phase 1 の設計どおり。
 * DS-05 は API 経由 (createDatasource factory) で s3:// URL を投入し、
 * 一覧側で表示できることを検証する形にしている (UI 側のレンダリング検証)。
 */
test.describe("Datasources create - URL form", () => {
  let pmtilesTileset: CreatedTileset;
  let cogTileset: CreatedTileset;

  test.beforeAll(async () => {
    await loginAsAdmin();
    await resetDatabase();
    // フォームの「タイルセット選択」セレクタには
    // datasourceType に応じて (pmtiles / raster) の tileset しか出ない。
    pmtilesTileset = await createTileset({
      name: "Parent PMTiles tileset",
      type: "pmtiles",
    });
    cogTileset = await createTileset({
      name: "Parent COG tileset",
      type: "raster",
    });
  });

  test.beforeEach(async () => {
    // 各テスト前に admin として再ログイン (cookie 注入は fixture 側で実施)。
    await loginAsAdmin();
  });

  test("DS-04 PMTiles URL でデータソースを作成できる", async ({ page }) => {
    await page.goto("/datasources/new");

    // type は pmtiles がデフォルト。tileset を選択する。
    // shadcn/ui の Select (Radix) は role=combobox なのでクリック → option を選ぶ。
    await page.getByTestId("datasource-form-tileset").click();
    await page.getByRole("option", { name: pmtilesTileset.name }).click();

    await page
      .getByTestId("datasource-form-url")
      .fill("https://example.com/sample.pmtiles");

    await page.getByTestId("datasource-form-submit").click();

    // 詳細ページにリダイレクトされる (`router.push(/datasources/{id})`)。
    await page.waitForURL(/\/datasources\/[0-9a-f-]+/, { timeout: 10_000 });

    // 一覧に戻ったら 1 件あることを確認。
    await page.goto("/datasources");
    await expect(page.getByTestId("datasource-list-row")).toHaveCount(1);
    await expect(page.getByText("sample.pmtiles")).toBeVisible();
  });

  test("DS-06 COG URL でデータソースを作成できる", async ({ page }) => {
    // 各テスト独立に DB をリセットしない (beforeAll の setup を共有する) ため、
    // 前のテストの残骸が一覧に残っている前提で「+1 増える」を assert する。
    // `.count()` は描画/ hydrate を待たないので、先に最初の row が visible に
    // なるまで or 0 件確定するまで待ってから数える。
    await page.goto("/datasources");
    const rows = page.getByTestId("datasource-list-row");
    // hydrate 完了の合図として「table 自体」が描画されるのを待つ。
    await expect(page.getByTestId("datasource-list-row").first()).toBeVisible({
      timeout: 10_000,
    });
    const beforeCount = await rows.count();

    await page.goto("/datasources/new");

    // type を cog に切り替え (Radix Select)。
    await page.getByTestId("datasource-form-type").click();
    await page
      .getByRole("option", { name: /COG/ })
      .click();

    // cog tileset を選択。
    await page.getByTestId("datasource-form-tileset").click();
    await page.getByRole("option", { name: cogTileset.name }).click();

    await page
      .getByTestId("datasource-form-url")
      .fill("https://example.com/sample.tif");

    await page.getByTestId("datasource-form-submit").click();

    await page.waitForURL(/\/datasources\/[0-9a-f-]+/, { timeout: 10_000 });

    // 一覧に戻って増えていることを確認。
    await page.goto("/datasources");
    await expect(page.getByTestId("datasource-list-row")).toHaveCount(
      beforeCount + 1,
    );
    await expect(page.getByText("sample.tif")).toBeVisible();
  });
});

test.describe("Datasources create - s3:// scheme (Issue #101 Phase 1)", () => {
  test.beforeAll(async () => {
    await loginAsAdmin();
    await resetDatabase();
  });

  test("DS-05 s3:// URL のデータソースを API 経由で作成し一覧に表示できる", async ({
    page,
  }) => {
    // UI の URL 入力欄は http(s) のみ許可するため、s3:// は createDatasource
    // factory (API 直叩き) で投入する。Phase 1 の検証ポイントは:
    //   - バックエンドが s3:// scheme を保存できる
    //   - 一覧 UI が s3:// URL を表示できる (isOpenableUrl が false でも崩れない)
    const ds = await createDatasource({
      name: "ds-s3-scheme",
      url: "s3://geo-base-tiles/sample.pmtiles",
      type: "pmtiles",
    });
    expect(ds.url).toBe("s3://geo-base-tiles/sample.pmtiles");

    await page.goto("/datasources");
    const rows = page.getByTestId("datasource-list-row");
    await expect(rows).toHaveCount(1);
    // URL カラムは truncate されるが s3:// プレフィックスは見える。
    await expect(page.getByText(/s3:\/\/geo-base-tiles/)).toBeVisible();
  });
});
