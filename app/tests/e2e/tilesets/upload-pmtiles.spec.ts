import path from "node:path";

import { test, expect } from "../fixtures/authenticated-test";

import { resetDatabase } from "../utils/reset-db";
import { loginAsAdmin } from "../utils/session";
import { createTileset } from "../fixtures/factories";

/**
 * TS-12: PMTiles 直接アップロード → moto S3 保存 → datasource 詳細ページ。
 *
 * プランは `/tilesets/new` で PMTiles ファイル input を扱う前提だったが、
 * 実 UI は 2 段階フロー:
 *   1. 親 tileset (type=pmtiles) を作る (本テストは factories.createTileset で短縮)
 *   2. `/datasources/new` で type=PMTiles → 対象 tileset → 「ファイルをアップロード」
 *      → setInputFiles → submit
 *   3. API `POST /api/datasources/pmtiles/upload?tileset_id=<id>` が moto S3 に保存
 *   4. 成功時は 1 秒 setTimeout を挟んで `/datasources/<id>` に router.push
 *
 * 期待: CI ワークフロー (e2e-full.yml / e2e-nightly.yml) で
 *   S3_ENDPOINT_URL=http://localhost:5000, S3_BUCKET=geo-base-e2e
 * を渡し、`scripts/start-moto.sh` が moto を起動済みであること。
 */

const SAMPLE_PMTILES = path.resolve(__dirname, "../fixtures/sample.pmtiles");

test.describe("Tilesets PMTiles upload (moto S3)", () => {
  test.beforeAll(async () => {
    await loginAsAdmin();
    await resetDatabase();
  });

  test("TS-12 PMTiles 直接アップロード → moto S3 保存 → 詳細ページ", async ({
    page,
  }) => {
    // 親 tileset を factories で作成 (type=pmtiles)。UI 経由でも作れるが、
    // 本テストはアップロード経路の検証に集中するため API で短縮する。
    const tileset = await createTileset({
      name: "ts-12-pmtiles-upload",
      type: "pmtiles",
      isPublic: false,
    });

    await page.goto("/datasources/new");

    // データソースタイプは pmtiles が既定だが、明示的に選んで遷移を安定化させる。
    // shadcn Select は trigger を click → option を role で選ぶ。
    await page.getByTestId("datasource-form-type").click();
    await page.getByRole("option", { name: /^PMTiles$/i }).click();

    // タイルセット選択。`<SelectItem value={ts.id}>` なので id を表示名でなく
    // option label (= タイルセット名) で当てる。
    await page.getByTestId("datasource-form-tileset").click();
    await page.getByRole("option", { name: /ts-12-pmtiles-upload/i }).click();

    // 入力モードを「ファイルをアップロード」に切替。
    await page.getByTestId("datasource-form-mode").click();
    await page.getByRole("option", { name: /ファイルをアップロード/ }).click();

    // ファイル input は uncontrolled だが、`key` に inputMode を含めているので
    // ここで存在する。setInputFiles で fixture を流し込む。
    await page
      .getByTestId("datasource-form-file")
      .setInputFiles(SAMPLE_PMTILES);

    // submit → アップロード → 1 秒 setTimeout 後に /datasources/<id> に router.push。
    await page.getByTestId("datasource-form-submit").click();

    // moto S3 への PUT + aiopmtiles メタデータ取得 + DB INSERT を含むので
    // タイムアウトは長めに。`/datasources/new` から離れた URL を待つ。
    await page.waitForURL(/\/datasources\/(?!new)[^/]+(\?|$)/, {
      timeout: 30_000,
    });

    // 詳細ページの heading は `{tileset_name}` を表示する (page.tsx:217)。
    await expect(
      page.getByRole("heading", { name: /ts-12-pmtiles-upload/ }),
    ).toBeVisible({ timeout: 15_000 });

    // 詳細ページの「接続テスト」ボタンも見える = ページ初期 fetch 完了の追加サニティ。
    await expect(
      page.getByTestId("datasource-test-connection-button"),
    ).toBeVisible();

    // データソースが作成された結果、親 tileset 経由で参照できることも別途確認したいが、
    // それは regression 領域に任せる。本 test はアップロード成功までを担当。

    // 念のため tileset.id を assertion に絡める (DB resetDatabase で他テスト由来の
    // ノイズが入らないことの確認)。
    expect(tileset.id).toBeTruthy();
  });
});
