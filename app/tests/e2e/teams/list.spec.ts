import { test, expect } from "../fixtures/authenticated-test";

import { resetDatabase } from "../utils/reset-db";
import { createTeam } from "../fixtures/factories";
import { loginAsAdmin } from "../utils/session";

test.describe("Teams list - smoke", () => {
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
});

test.describe("Teams list - create dialog", () => {
  test.beforeAll(async () => {
    await loginAsAdmin();
    await resetDatabase();
  });

  test("TM-02 ダイアログから名前のみでチームを作成できる (slug は自動生成)", async ({
    page,
  }) => {
    await page.goto("/teams");

    // 初期は 0 件。
    await expect(page.getByTestId("team-card")).toHaveCount(0);

    await page.getByTestId("team-create-button").click();

    // slug 未指定でも作成できる (TeamCreate の model_validator で自動生成)。
    await page.getByTestId("team-create-name").fill("My New Team");
    await page.getByTestId("team-create-submit").click();

    // 一覧に追加される。
    await expect(page.getByTestId("team-card")).toHaveCount(1);
    await expect(page.getByText("My New Team")).toBeVisible();
    // slug は generate_slug() で "my-new-team" に変換されることを期待。
    await expect(page.getByText("@my-new-team")).toBeVisible();
  });
});
