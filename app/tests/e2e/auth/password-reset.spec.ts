import { test, expect } from "@playwright/test";

import { resetDatabase } from "../utils/reset-db";
import { E2E_ADMIN_EMAIL } from "../utils/session";
import { fetchRecentToken } from "../utils/token-fetch";

const ORIGINAL_PASSWORD = "E2E-pass-1!";
const NEW_PASSWORD = "Reset-pass-2!";

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

test("AUTH-08 reset token で新パスワード設定 → 新パスワードでログイン可", async ({
  page,
}) => {
  // 申請して token 発行
  await page.goto("/password-reset/request");
  await page.getByTestId("password-reset-email").fill(E2E_ADMIN_EMAIL);
  await page.getByTestId("password-reset-submit").click();
  await expect(page.getByTestId("password-reset-success")).toBeVisible({
    timeout: 10_000,
  });

  // console backend が記録した token を取り出す
  const token = await fetchRecentToken("password_reset", E2E_ADMIN_EMAIL);

  // 確認ページで新パスワード設定
  await page.goto(`/password-reset/confirm?token=${encodeURIComponent(token)}`);
  await page.getByTestId("password-reset-confirm-password").fill(NEW_PASSWORD);
  await page.getByTestId("password-reset-confirm-submit").click();
  await expect(
    page.getByTestId("password-reset-confirm-success"),
  ).toBeVisible({ timeout: 10_000 });

  // 新パスワードでログイン
  await page.goto("/login");
  await page.getByTestId("login-email").fill(E2E_ADMIN_EMAIL);
  await page.getByTestId("login-password").fill(NEW_PASSWORD);
  await page.getByTestId("login-submit").click();
  await page.waitForURL("/", { timeout: 15_000 });

  // rollback: 元のパスワードに戻す (admin user は他テストと共有のため必須)
  await page.goto("/password-reset/request");
  await page.getByTestId("password-reset-email").fill(E2E_ADMIN_EMAIL);
  await page.getByTestId("password-reset-submit").click();
  await expect(page.getByTestId("password-reset-success")).toBeVisible({
    timeout: 10_000,
  });
  const rollback = await fetchRecentToken("password_reset", E2E_ADMIN_EMAIL);
  await page.goto(
    `/password-reset/confirm?token=${encodeURIComponent(rollback)}`,
  );
  await page
    .getByTestId("password-reset-confirm-password")
    .fill(ORIGINAL_PASSWORD);
  await page.getByTestId("password-reset-confirm-submit").click();
  await expect(
    page.getByTestId("password-reset-confirm-success"),
  ).toBeVisible({ timeout: 10_000 });
});

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
