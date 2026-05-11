import { test, expect } from "../fixtures/authenticated-test";
import { request } from "@playwright/test";

import { resetDatabase } from "../utils/reset-db";
import { createTeam, inviteMember } from "../fixtures/factories";
import { loginAsAdmin, E2E_ADMIN_EMAIL, E2E_ADMIN_PASSWORD } from "../utils/session";
import { fetchRecentToken } from "../utils/token-fetch";

const APP_BASE = process.env.PLAYWRIGHT_BASE_URL || "http://localhost:3000";

/**
 * 招待 → accept で実際に member を増やすヘルパー。
 *
 * accept-invitation は新規ユーザー作成 + 自動ログインの API。叩いた後
 * その API context は新規ユーザーの session を持つが、本テストでは
 * factory の admin session には影響を与えない (別 request context)。
 *
 * 呼び出した側 (admin として再ログインしたい場合は) は本ヘルパー後に
 * `await loginAsAdmin()` を呼んで session を上書きすること。
 */
async function acceptInvitationAsNewUser(
  token: string,
  name: string,
  password: string,
): Promise<void> {
  const ctx = await request.newContext({ baseURL: APP_BASE });
  try {
    const res = await ctx.post("/api/auth/accept-invitation", {
      data: { token, name, password },
    });
    if (!res.ok()) {
      throw new Error(
        `acceptInvitation failed: ${res.status()} ${await res.text()}`,
      );
    }
  } finally {
    await ctx.dispose();
  }
}

test.describe("Teams members - invite", () => {
  test.beforeAll(async () => {
    await loginAsAdmin();
    await resetDatabase();
  });

  test("TM-04 招待を送信すると招待一覧に表示される", async ({ page }) => {
    const team = await createTeam({ name: "TM-04 Team" });

    await page.goto(`/teams/${team.id}`);

    // Members タブから「招待する」ボタンを開く。
    await page.getByTestId("team-invite-button").click();

    const inviteEmail = `tm04-${Date.now()}@example.com`;
    await page.getByTestId("team-invite-email").fill(inviteEmail);
    await page.getByTestId("team-invite-submit").click();

    // 招待タブに切り替えて行が見えることを確認。
    // 招待は state 直接更新でも反映される (invitations list)。
    await page.getByRole("tab", { name: /招待/ }).click();

    const row = page
      .getByTestId("team-invitation-row")
      .filter({ hasText: inviteEmail });
    await expect(row).toBeVisible();
  });
});

test.describe("Teams members - removal", () => {
  test.beforeAll(async () => {
    await loginAsAdmin();
    await resetDatabase();
  });

  test("TM-06 招待 → accept でメンバーに昇格 → 削除でリストから消える", async ({
    page,
  }) => {
    const team = await createTeam({ name: "TM-06 Team" });
    const memberEmail = `tm06-${Date.now()}@example.com`;

    // 招待を作成 (admin session)。
    await inviteMember({ teamId: team.id, email: memberEmail });

    // 招待 token を取得 → 受諾。受諾は新規 user session で動くが、
    // ここでは別 request context を使うので admin session には影響しない。
    const token = await fetchRecentToken("team_invitation", memberEmail);
    await acceptInvitationAsNewUser(token, "TM06 User", "Member-pass-1!");

    // accept で admin の access token は変わらないが、念のため再ログイン。
    await loginAsAdmin();

    await page.goto(`/teams/${team.id}`);

    // owner + 受諾 user の 2 名が member に並ぶ。
    const members = page.getByTestId("team-member-row");
    await expect(members).toHaveCount(2);

    // owner ではない方の行を絞り込み、削除アクションを実行する。
    const targetRow = members.filter({ hasText: memberEmail });
    await expect(targetRow).toBeVisible();
    await targetRow.getByRole("button").last().click(); // dropdown trigger
    await page.getByRole("menuitem", { name: /削除/ }).click();

    // 1 件に減る (owner のみ)。
    await expect(members).toHaveCount(1);
    await expect(targetRow).toHaveCount(0);
  });

  // TM-05 (role 変更) は team 詳細 UI に member の role を変更する操作が
  // 存在しないため Phase 2 では skip。API は updateTeamMember を持つが、
  // UI で公開されたら同 spec を有効化する。
  test.skip("TM-05 member の role 変更 (UI 未実装のため Phase 3 移管)", async () => {
    // intentionally empty
  });
});

test.describe("Teams members - delete team", () => {
  test.beforeAll(async () => {
    await loginAsAdmin();
    await resetDatabase();
  });

  test("TM-07 チーム詳細画面の削除で /teams へ遷移し一覧から消える", async ({
    page,
  }) => {
    const team = await createTeam({ name: "TM-07 Team" });

    await page.goto(`/teams/${team.id}`);

    await page.getByTestId("team-delete-button").click();
    await page.getByTestId("team-delete-confirm").click();

    await page.waitForURL("**/teams", { timeout: 10_000 });
    await expect(page.getByText("TM-07 Team")).toHaveCount(0);
  });
});

// 未使用 export を防ぐ lint silencer (E2E_ADMIN_* は将来の re-login 用に import している)
void E2E_ADMIN_EMAIL;
void E2E_ADMIN_PASSWORD;
