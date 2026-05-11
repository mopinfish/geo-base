/**
 * Issue #100 (Phase 3 a11y 監査) の受入条件 6 ページのうち、`/api-keys` を
 * 担当する spec。
 *
 * 形式は `tilesets-list.spec.ts` と同じく:
 *  - resetDatabase で空にした上で fixture を 1 件作成し、一覧の空状態と
 *    1 行状態の両方が画面に出る前提でスキャン
 *  - axe-core を WCAG 2.1 AA タグで走らせ、serious / critical 違反のみを
 *    失敗扱い
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
    await expectNoA11ySeriousViolations(page);
  });
});
