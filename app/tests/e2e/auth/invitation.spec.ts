import { test, expect } from "@playwright/test";

import { resetDatabase } from "../utils/reset-db";
import { fetchRecentToken } from "../utils/token-fetch";
import { loginAsAdmin } from "../utils/session";
import { createTeam, inviteMember } from "../fixtures/factories";

/**
 * AUTH-10: 招待 token で新規ユーザー登録 + 自動ログイン。
 *
 * 受諾後のリダイレクト先は `/teams/${info.team_id}` (accept-invitation/page.tsx 参照)。
 * 旧プランでは `/` だったが、実装は team 詳細にジャンプする。
 */
test.beforeAll(async () => {
  await loginAsAdmin();
  await resetDatabase();
});

test("AUTH-10 招待 token で新規ユーザー登録 + 自動ログインしてチーム詳細へ", async ({
  page,
}) => {
  // beforeAll で resetDB 後の session を失った可能性に備え念のため再ログイン。
  await loginAsAdmin();

  const team = await createTeam({ name: "Invitation E2E Team" });
  const inviteEmail = `invitee-${Date.now()}@example.com`;
  await inviteMember({ teamId: team.id, email: inviteEmail });

  const token = await fetchRecentToken("team_invitation", inviteEmail);

  // 招待ページへ。InvitationInfo を取得して表示するため少し待つ。
  await page.goto(`/accept-invitation?token=${encodeURIComponent(token)}`);
  await expect(page.getByTestId("invitation-name")).toBeVisible({
    timeout: 10_000,
  });

  await page.getByTestId("invitation-name").fill("E2E Invitee");
  await page.getByTestId("invitation-password").fill("Invitee-pass-1!");
  await page.getByTestId("invitation-submit").click();

  // 受諾後はチーム詳細にリダイレクト。
  await page.waitForURL(new RegExp(`/teams/${team.id}`), {
    timeout: 15_000,
  });
});
