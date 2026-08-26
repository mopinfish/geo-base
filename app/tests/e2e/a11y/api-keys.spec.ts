/**
 * Issue #100 (Phase 3 a11y 監査) の受入条件 6 ページのうち、`/api-keys` を
 * 担当する spec。
 *
 * 形式は `tilesets-list.spec.ts` と同じく:
 *  - resetDatabase で空にした上で fixture を 1 件作成し、一覧 (rows あり)
 *    状態を axe スキャン対象にする
 *  - axe-core を WCAG 2.1 AA タグで走らせ、serious / critical 違反のみを
 *    失敗扱い
 *
 * 空状態 (rows = 0) のスキャンは別 PR で別 describe / 別 test に分けるか
 * 判断する (現状は 1 行ある状態に集中。Copilot PR #130 round 1 で
 * ヘッダーコメントの説明と実装を一致させた)。
 */
import { test } from "../fixtures/authenticated-test";

import { createApiKey } from "../fixtures/factories";
import { resetDatabase } from "../utils/reset-db";
import { loginAsAdmin } from "../utils/session";
import { expectNoA11ySeriousViolations } from "./_helper";

test.describe("a11y: /api-keys", () => {
  test.beforeAll(async () => {
    await loginAsAdmin();
    await resetDatabase();
    await createApiKey({ name: "a11y-fixture-key", scopes: ["read"] });
  });

  test("a11y: /api-keys serious/critical 違反なし", async ({ page }) => {
    await page.goto("/api-keys");
    // /api-keys は `isLoading` 中に「読み込み中...」を描画する。
    // fixture で 1 件作っているので `api-key-row` が visible になったら
    // ローディング完了とみなして axe をかける
    // (Copilot PR #130 round 1 指摘)。
    await expectNoA11ySeriousViolations(page, {
      awaitReady: { testid: "api-key-row" },
    });
  });
});
