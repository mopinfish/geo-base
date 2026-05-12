import { test, expect } from "../fixtures/authenticated-test";

import { resetDatabase } from "../utils/reset-db";
import { loginAsAdmin } from "../utils/session";

/**
 * TM-08: teams が 0 件のときに空状態 (empty state) が表示されることを確認する。
 *
 * `app/src/app/teams/page.tsx` の `teams.length === 0` 分岐に
 * `data-testid="team-empty-state"` を付与している。`team-card` は表示されない。
 */
test.describe("Teams empty state", () => {
  test.beforeAll(async () => {
    await loginAsAdmin();
    await resetDatabase();
  });

  test("TM-08 team が無いとき空状態が表示される", async ({ page }) => {
    await page.goto("/teams");

    await expect(page.getByTestId("team-empty-state")).toBeVisible({
      timeout: 10_000,
    });
    await expect(page.getByTestId("team-card")).toHaveCount(0);
  });
});
