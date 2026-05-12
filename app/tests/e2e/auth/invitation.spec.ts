import { test, expect } from "@playwright/test";

import { resetDatabase } from "../utils/reset-db";
import { fetchRecentToken } from "../utils/token-fetch";
import { loginAsAdmin, E2E_ADMIN_EMAIL } from "../utils/session";
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

/**
 * AUTH-11: 既存ユーザー宛の招待 → /login へ誘導。
 *
 * 実装 (accept-invitation/page.tsx) は `info.has_existing_account` の場合に
 * 自動リダイレクトではなく `<a href="/login?next=...">ログイン</a>` のリンクを
 * 表示する仕様。したがってここでは「リンクが表示されており、その href が
 * /login?next=/accept-invitation?... 形式である」ことを assert する。
 */
test("AUTH-11 既存ユーザー宛の招待 → /login?next=/accept-invitation に誘導", async ({
  page,
}) => {
  await loginAsAdmin();

  const team = await createTeam({ name: "AUTH-11 Team" });
  await inviteMember({ teamId: team.id, email: E2E_ADMIN_EMAIL });
  const token = await fetchRecentToken("team_invitation", E2E_ADMIN_EMAIL);

  await page.goto(`/accept-invitation?token=${encodeURIComponent(token)}`);

  const loginLink = page.getByTestId("invitation-login-link");
  await expect(loginLink).toBeVisible({ timeout: 10_000 });

  const href = await loginLink.getAttribute("href");
  expect(href).not.toBeNull();
  // /login?next=<encoded accept-invitation URL> の形であることを確認。
  expect(href!).toMatch(/^\/login\?next=/);
  const nextParam = new URL(href!, "http://localhost").searchParams.get("next");
  expect(nextParam).toContain("/accept-invitation");
});

test("AUTH-12 無効な invitation token → エラー表示", async ({ page }) => {
  await page.goto("/accept-invitation?token=invalid-invite-xyz-12345");
  await expect(page.getByTestId("invitation-error")).toBeVisible({
    timeout: 10_000,
  });
});
