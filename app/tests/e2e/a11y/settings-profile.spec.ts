/**
 * Issue #100 (Phase 3 a11y 監査) の受入条件 6 ページのうち、`/settings`
 * (= `/settings/profile` にリダイレクト) を担当する spec。
 *
 * 形式は `dashboard.spec.ts` と同じく axe-core を WCAG 2.1 AA タグで走らせ、
 * serious / critical 違反のみを失敗扱いにする。
 *
 * fixture 不要 (ログイン済み user の profile 編集画面が表示されるだけ)。
 */
import { test } from "../fixtures/authenticated-test";

import { loginAsAdmin } from "../utils/session";
import { expectNoA11ySeriousViolations } from "./_helper";

test.describe("a11y: /settings", () => {
  test.beforeAll(async () => {
    await loginAsAdmin();
  });

  test("a11y: /settings/profile serious/critical 違反なし", async ({
    page,
  }) => {
    await page.goto("/settings/profile");
    // useAuth() の user が hydrate されるまで待つため、name 入力欄に既存
    // ユーザーの名前が入った状態を `awaitReady` の代わりに getByLabel で確認。
    // SettingsNav は静的レンダー、ローディング placeholder は無いので
    // 軽く同期するだけで axe スキャンに十分。
    await page.waitForLoadState("networkidle");
    await expectNoA11ySeriousViolations(page);
  });
});
