/**
 * Regression: PR #103 / Issue #102.
 *
 * 「`/tilesets` 一覧で自分の非公開タイルセットが表示されない」バグの再発防止。
 *
 * 修正前は admin UI が `api.listTilesets()` を `include_private` 無しで呼んでおり、
 * 認証済みユーザーであっても自分の private タイルセットを一覧で見られなかった。
 * fix: `api.listTilesets({ include_private: true })` を渡すように変更。
 */
import { test, expect } from "../fixtures/authenticated-test";
import { resetDatabase } from "../utils/reset-db";
import { createTileset } from "../fixtures/factories";
import { loginAsAdmin } from "../utils/session";

test.beforeAll(async () => {
  await loginAsAdmin();
  await resetDatabase();
});

test("TS-13 @regression 自分の非公開 tileset が /tilesets 一覧に表示される (#102)", async ({
  page,
}) => {
  await createTileset({
    name: "private-regression",
    type: "vector",
    isPublic: false,
  });
  await page.goto("/tilesets");
  await expect(page.getByText("private-regression")).toBeVisible({
    timeout: 10_000,
  });
});
