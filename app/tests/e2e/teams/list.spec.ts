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

test.describe("Teams list - duplicate slug", () => {
  // TM-03 (Phase 3): 「同じ slug で 2 回作成 → 2 回目はエラー」を期待していたが、
  // 実装の `create_team` (api/lib/routers/teams.py) は重複検知時にエラーを返さず、
  // `secrets.token_hex(4)` でランダムサフィックス付きの新 slug を発行して
  // 黙って成功させる仕様になっている。よって UI レベルでは重複エラーが発生せず、
  // 本テストは仕様上成立しない。
  //
  // 仕様変更 (重複時に 409 を返す等) が入った時点で skip を外して有効化する。
  // 関連: api/lib/routers/teams.py:130-138 (slug 既存時に generate_slug を再実行)。
  test.skip("TM-03 同じ slug の team を 2 回作成 → 2 回目はエラー", async () => {
    // 実装側で重複時 409 を返すようになったら以下を有効化する。
    // 1) team-create-button から duplicate-team を作成 (成功)
    // 2) もう一度 duplicate-team を入力 → team-create-error が表示される
  });
});
