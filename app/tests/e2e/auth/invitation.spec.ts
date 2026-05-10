import { test } from "@playwright/test";

// AUTH-10: 招待 token で新規ユーザー登録 + 自動ログイン
//
// このテストは `inviteMember` factory が必要なため、Tasks 6-9 batch
// (Teams core を実装する) で完成させる。それまでスケルトンとして残す。
//
// 完成後の想定フロー:
// 1. loginAsAdmin して team を作成 + member 招待
// 2. fetchRecentToken("team_invitation", inviteEmail) で token 取得
// 3. /accept-invitation?token=... に goto
// 4. name + password を入力して submit
// 5. waitForURL("/") で自動ログイン後のダッシュボード

test.skip("AUTH-10 招待 token で新規ユーザー登録 + 自動ログイン", async () => {
  // Pending: inviteMember factory in Tasks 6-9 batch (Teams core)
});
