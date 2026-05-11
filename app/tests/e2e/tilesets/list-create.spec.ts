import { test, expect } from "../fixtures/authenticated-test";

import { resetDatabase } from "../utils/reset-db";
import { createTileset } from "../fixtures/factories";
import { loginAsAdmin } from "../utils/session";

test.beforeAll(async () => {
  await loginAsAdmin();
  await resetDatabase();
});

test("TS-01 @smoke タイルセット一覧が表示される", async ({ page }) => {
  await createTileset({ name: "ts-list-smoke-A", type: "vector" });
  await createTileset({ name: "ts-list-smoke-B", type: "raster" });

  await page.goto("/tilesets");

  const rows = page.getByTestId("tileset-list-row");
  await expect(rows).toHaveCount(2, { timeout: 10_000 });
  await expect(page.getByText("ts-list-smoke-A")).toBeVisible();
  await expect(page.getByText("ts-list-smoke-B")).toBeVisible();
});

test("TS-07 @smoke タイルセット新規作成 → 詳細ページへ遷移", async ({ page }) => {
  await page.goto("/tilesets");
  await page.getByTestId("tileset-create-link").click();
  await page.waitForURL("/tilesets/new");

  await page.getByTestId("tileset-form-name").fill("ts-create-smoke");
  await page.getByTestId("tileset-form-submit").click();

  // `/tilesets/[^/]+` だと現在地の `/tilesets/new` 自体に即マッチしてしまい、
  // フォーム送信前に waitForURL が解決して後続の assertion が壊れる。`new` を
  // 否定先読みで除外して、詳細ページ (`/tilesets/<UUID>`) への遷移だけ待つ。
  await page.waitForURL(/\/tilesets\/(?!new(?:\/|$|\?))[^/]+(\?|$)/, {
    timeout: 15_000,
  });
  // 詳細ページの h1 (`<h1>{tileset.name}</h1>`) が hydrate されるまで待つ。
  // 名前を heading role で待つことで、ローディング状態の他要素にマッチしない。
  await expect(
    page.getByRole("heading", { name: "ts-create-smoke" }),
  ).toBeVisible({ timeout: 15_000 });
});

/**
 * 一覧フィルタ + 一括操作 + バリデーションのコアケース。
 *
 * 既存 TS-01/07 とは別 describe にして beforeAll を分離する。各テストでは
 * `resetDatabase()` してから seeded データを作る方針 (テスト順序に依存しない)。
 *
 * type / public フィルタは shadcn (Radix) の Select なので `<select>` ではなく
 * Listbox ベース。`selectOption` ではなく click → option の role 経由で操作する。
 */
test.describe("Tilesets list filtering and bulk operations", () => {
  test.beforeAll(async () => {
    await loginAsAdmin();
  });

  test("TS-02 名前検索でフィルタ", async ({ page }) => {
    await resetDatabase();
    await createTileset({ name: "alpha", type: "vector", isPublic: true });
    await createTileset({ name: "beta", type: "vector", isPublic: true });
    await createTileset({ name: "gamma", type: "vector", isPublic: true });

    await page.goto("/tilesets");
    // 全件 hydrate するのを待つ。
    await expect(page.getByTestId("tileset-list-row")).toHaveCount(3, {
      timeout: 10_000,
    });

    await page.getByTestId("tileset-search-input").fill("alpha");
    await expect(page.getByTestId("tileset-list-row")).toHaveCount(1, {
      timeout: 5_000,
    });
    await expect(page.getByText("alpha", { exact: true })).toBeVisible();
  });

  test("TS-03 type フィルタ", async ({ page }) => {
    await resetDatabase();
    await createTileset({ name: "v1", type: "vector", isPublic: true });
    await createTileset({ name: "r1", type: "raster", isPublic: true });
    await createTileset({ name: "p1", type: "pmtiles", isPublic: true });

    await page.goto("/tilesets");
    await expect(page.getByTestId("tileset-list-row")).toHaveCount(3, {
      timeout: 10_000,
    });

    // shadcn の Select は trigger を click すると listbox が開き、option を role で取得できる。
    await page.getByTestId("tileset-filter-type").click();
    await page.getByRole("option", { name: "ベクタ" }).click();
    await expect(page.getByTestId("tileset-list-row")).toHaveCount(1);
    await expect(page.getByText("v1", { exact: true })).toBeVisible();

    await page.getByTestId("tileset-filter-type").click();
    await page.getByRole("option", { name: "ラスタ" }).click();
    await expect(page.getByTestId("tileset-list-row")).toHaveCount(1);
    await expect(page.getByText("r1", { exact: true })).toBeVisible();
  });

  test("TS-04 public/private フィルタ", async ({ page }) => {
    await resetDatabase();
    await createTileset({ name: "public-1", type: "vector", isPublic: true });
    await createTileset({
      name: "private-1",
      type: "vector",
      isPublic: false,
    });

    await page.goto("/tilesets");
    // include_private=true なので所有者には 2 件とも見える。
    await expect(page.getByTestId("tileset-list-row")).toHaveCount(2, {
      timeout: 10_000,
    });

    await page.getByTestId("tileset-filter-public").click();
    await page.getByRole("option", { name: "公開", exact: true }).click();
    await expect(page.getByTestId("tileset-list-row")).toHaveCount(1);
    await expect(page.getByText("public-1", { exact: true })).toBeVisible();

    await page.getByTestId("tileset-filter-public").click();
    await page.getByRole("option", { name: "非公開", exact: true }).click();
    await expect(page.getByTestId("tileset-list-row")).toHaveCount(1);
    await expect(page.getByText("private-1", { exact: true })).toBeVisible();
  });

  test("TS-05 一括選択 + 一括削除", async ({ page }) => {
    await resetDatabase();
    await createTileset({ name: "bulk-1", type: "vector", isPublic: true });
    await createTileset({ name: "bulk-2", type: "vector", isPublic: true });

    await page.goto("/tilesets");
    await expect(page.getByTestId("tileset-list-row")).toHaveCount(2, {
      timeout: 10_000,
    });

    // ヘッダの全選択 checkbox。
    await page.getByTestId("tileset-select-all").click();
    await page.getByTestId("tileset-bulk-delete").click();

    // AlertDialog の確定ボタンは「{N}件を削除」というラベル。
    await page
      .getByRole("alertdialog")
      .getByRole("button", { name: /件を削除/ })
      .click();

    await expect(page.getByTestId("tileset-list-row")).toHaveCount(0, {
      timeout: 10_000,
    });
  });

  test("TS-06 新規作成 name 空 → 送信できず /tilesets/new に留まる", async ({
    page,
  }) => {
    await page.goto("/tilesets/new");

    // submit ボタンは name 空のとき disabled。HTML5 required と併せて
    // どちらの場合でもフォーム送信されず /tilesets/new に留まる。
    const submit = page.getByTestId("tileset-form-submit");
    await expect(submit).toBeDisabled();

    // disabled でも force click して、URL が変わらないことを確認する。
    await submit.click({ force: true }).catch(() => {
      // disabled な要素クリックは reject されることがあるが、その場合も /new に留まるので OK。
    });
    // 固定 sleep は遅く・不安定なので使わない。`toHaveURL` の polling timeout が
    // 「クリック後に遅延ナビゲーションが発生しないこと」を実質的に保証する。
    await expect(page).toHaveURL(/\/tilesets\/new$/, { timeout: 3_000 });
  });
});
