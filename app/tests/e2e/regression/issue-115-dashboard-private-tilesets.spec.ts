/**
 * Regression: Issue #115 / PR #116.
 *
 * 「dashboard のカウント表示でも `include_private: true` を渡して自分の
 * 非公開 tileset を含めて数える」要件。修正前は `api.listTilesets()` を
 * include_private なしで呼んでいたため、admin の private が dashboard では
 * 数えられていなかった。
 */
import { test, expect } from "../fixtures/authenticated-test";
import { resetDatabase } from "../utils/reset-db";
import { createTileset } from "../fixtures/factories";
import { loginAsAdmin } from "../utils/session";

test.beforeAll(async () => {
  await loginAsAdmin();
  await resetDatabase();
});

test("DASH-03 @regression dashboard で自分の非公開 tileset も count される (#115)", async ({
  page,
}) => {
  await createTileset({
    name: "dash-private-regression",
    type: "vector",
    isPublic: false,
  });
  await page.goto("/");
  await expect(page.getByTestId("dashboard-tilesets-count")).toHaveText(
    /[1-9]/,
    { timeout: 10_000 },
  );
});
