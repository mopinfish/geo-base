import { test, expect } from "../fixtures/authenticated-test";

import { resetDatabase } from "../utils/reset-db";
import { createDatasource } from "../fixtures/factories";
import { loginAsAdmin } from "../utils/session";

/**
 * DS-07: データソース詳細画面の「接続テスト」ボタン。
 *
 * 接続テストは API 側で実際に PMTiles / COG ファイルを HTTP fetch しに行く
 * (api/lib/routers/datasources.py の test_datasource_connection)。E2E では
 * 外部 URL に依存させると CI で flaky になるため、`example.com/...` のような
 * 実在しない URL を投入してエラー応答が UI に出ることだけを確認する。
 *
 * 「成功 indicator が出るか」までは外部 fixture が必要なので Phase 3 移管。
 */
test.describe("Datasources test-connection", () => {
  test.beforeAll(async () => {
    await loginAsAdmin();
    await resetDatabase();
  });

  test("DS-07 接続テストボタンを押すと結果アラートが表示される", async ({
    page,
  }) => {
    const ds = await createDatasource({
      name: "ds-test-connection",
      // 外部に実 fixture を置くと flaky になるため、未存在 URL を指定し、
      // backend のエラー応答が UI alert に反映されることだけを検証する。
      url: "https://example.invalid/never-resolves.pmtiles",
      type: "pmtiles",
    });

    await page.goto(`/datasources/${ds.id}`);

    await page
      .getByTestId("datasource-test-connection-button")
      .click();

    // 結果 (成功 or エラー) のいずれかが出ればよい。
    const result = page.getByTestId("datasource-test-connection-result");
    await expect(result).toBeVisible({ timeout: 30_000 });
    // data-status は UI の testResult.status をそのまま流したもの。
    // API は成功時 "success"、失敗時 "error" を返す
    // (api/lib/routers/datasources.py の test_datasource_connection)。
    const status = await result.getAttribute("data-status");
    expect(["success", "error"]).toContain(status);
  });
});
