/**
 * Issue #100 (Phase 3 a11y 監査) の受入条件 6 ページのうち、`/teams` を
 * 担当する spec。
 *
 * 形式は `tilesets-list.spec.ts` / `api-keys.spec.ts` と同じ:
 *  - resetDatabase で空にした上で team を 1 件作って、1 行 (= `team-card`)
 *    状態を axe スキャン対象にする
 *  - axe-core を WCAG 2.1 AA タグで走らせ、serious / critical 違反のみを
 *    失敗扱い
 *  - `awaitReady: { testid: "team-card" }` でデータロード完了を待つ
 */
import { test } from "../fixtures/authenticated-test";

import { createTeam } from "../fixtures/factories";
import { resetDatabase } from "../utils/reset-db";
import { loginAsAdmin } from "../utils/session";
import { expectNoA11ySeriousViolations } from "./_helper";

test.describe("a11y: /teams", () => {
  test.beforeAll(async () => {
    await loginAsAdmin();
    await resetDatabase();
    await createTeam({ name: "a11y-team-fixture" });
  });

  test("a11y: /teams serious/critical 違反なし", async ({ page }) => {
    await page.goto("/teams");
    await expectNoA11ySeriousViolations(page, {
      awaitReady: { testid: "team-card" },
    });
  });
});
