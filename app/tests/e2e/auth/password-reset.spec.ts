import { test, expect, request } from "@playwright/test";

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

test.describe("Password reset round-trip (AUTH-08)", () => {
  // CI 初回実行 (run 25650874619) で AUTH-08 が timeout を超え、
  // inline rollback が走らず admin password が壊れた状態で残り、
  // 後続のすべての authenticated テストが 401 で fail するカスケード障害が
  // 発生した。これを防ぐため:
  // 1. test timeout を 60s に拡張 (CI の page goto は 1 回で 1-3s かかる)
  // 2. rollback は inline ではなく `afterAll` で API 直叩きで実行する
  //    (テスト本体が timeout / fail しても確実に走る)
  test.afterAll(async () => {
    const apiBase =
      process.env.PLAYWRIGHT_API_BASE_URL || "http://localhost:8000";
    // utils/reset-db.ts / token-fetch.ts / factories.ts:expireApiKey と同様に、
    // 非認証で admin password を書き換える API を本番に向けて誤爆させない
    // ための localhost / 127.0.0.1 guard (Copilot PR #122 round 3 指摘)。
    const apiHost = new URL(apiBase).hostname;
    if (!["localhost", "127.0.0.1"].includes(apiHost)) {
      throw new Error(
        `Refusing to call /api/auth/password-reset/* against non-local host: ${apiHost}`,
      );
    }
    const ctx = await request.newContext({ baseURL: apiBase });
    try {
      await ctx.post("/api/auth/password-reset/request", {
        data: { email: E2E_ADMIN_EMAIL },
      });
      const token = await fetchRecentToken(
        "password_reset",
        E2E_ADMIN_EMAIL,
      );
      const res = await ctx.post("/api/auth/password-reset/confirm", {
        data: { token, new_password: ORIGINAL_PASSWORD },
      });
      if (!res.ok()) {
        // 失敗してもテストは止めない (元々失敗してた場合、admin password は
        // まだ ORIGINAL のままの可能性も高い)。ログだけ残す。
        // eslint-disable-next-line no-console
        console.error(
          `AUTH-08 rollback warn: confirm ${res.status()} ${await res.text()}`,
        );
      }
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error("AUTH-08 password rollback failed:", err);
    } finally {
      await ctx.dispose();
    }
  });

  test("AUTH-08 reset token で新パスワード設定 → 新パスワードでログイン可", async ({
    page,
  }) => {
    test.setTimeout(60_000);

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
    await page.goto(
      `/password-reset/confirm?token=${encodeURIComponent(token)}`,
    );
    await page
      .getByTestId("password-reset-confirm-password")
      .fill(NEW_PASSWORD);
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

    // rollback は `afterAll` で API 経由実行 (テスト失敗時も確実に走るため)
  });
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
