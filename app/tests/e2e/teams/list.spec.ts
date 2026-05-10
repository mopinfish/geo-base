import { test, expect } from "../fixtures/authenticated-test";

import { resetDatabase } from "../utils/reset-db";
import { createTeam } from "../fixtures/factories";
import { loginAsAdmin } from "../utils/session";

test.beforeAll(async () => {
  await loginAsAdmin();
  await resetDatabase();
  await createTeam({ name: "Team Alpha" });
  await createTeam({ name: "Team Beta" });
});

test("TM-01 @smoke チーム一覧に作成済みのチームが表示される", async ({ page }) => {
  await page.goto("/teams");

  const cards = page.getByTestId("team-card");
  await expect(cards).toHaveCount(2);
  await expect(page.getByText("Team Alpha")).toBeVisible();
  await expect(page.getByText("Team Beta")).toBeVisible();
});
