import { test, expect } from "@playwright/test";

import { resetDatabase } from "../utils/reset-db";
import { E2E_ADMIN_EMAIL } from "../utils/session";

test.beforeAll(async () => {
  await resetDatabase();
});

test("AUTH-07 パスワードリセット申請 → 成功メッセージ", async ({ page }) => {
  await page.goto("/password-reset/request");
  await page.getByTestId("password-reset-email").fill(E2E_ADMIN_EMAIL);
  await page.getByTestId("password-reset-submit").click();

  // 成功メッセージ表示（実装の text に依存しないよう testid で）
  await expect(page.getByTestId("password-reset-success")).toBeVisible({
    timeout: 10_000,
  });
});

// AUTH-08 (token で新パスワード設定) は Phase 3 に移管:
// password_reset_tokens は token_hash のみ保持し平文取得不可のため、
// console email backend キャプチャ等の追加機構が必要。

test("AUTH-09 無効な reset token → エラー表示", async ({ page }) => {
  await page.goto("/password-reset/confirm?token=invalid-token-xyz-12345");

  // 実装はフォーム送信時にトークンを検証してエラーを出す仕様 (page.tsx 参照)。
  // ページロードのみではエラー要素が無いため、ダミーのパスワードで submit して
  // API 側の検証失敗を観測する。
  await page
    .getByTestId("password-reset-confirm-password")
    .fill("Dummy-pass-12345!");
  await page.getByTestId("password-reset-confirm-submit").click();

  await expect(page.getByTestId("password-reset-error")).toBeVisible({
    timeout: 10_000,
  });
});
