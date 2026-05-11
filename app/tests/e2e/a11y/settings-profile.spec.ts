/**
 * Issue #100 (Phase 3 a11y 監査) の受入条件 6 ページのうち、`/settings`
 * (= `/settings/profile` にリダイレクト) を担当する spec。
 *
 * 形式は `dashboard.spec.ts` と同じく axe-core を WCAG 2.1 AA タグで走らせ、
 * serious / critical 違反のみを失敗扱いにする。
 *
 * fixture 不要 (factory / api-client を使わないため `authenticated-test`
 * fixture の per-test ログインだけで十分。Copilot PR #130 round 1 指摘で
 * 冗長な `loginAsAdmin()` を除去)。
 */
import { expect, test } from "../fixtures/authenticated-test";

import { expectNoA11ySeriousViolations } from "./_helper";

test.describe("a11y: /settings", () => {
  test("a11y: /settings/profile serious/critical 違反なし", async ({
    page,
  }) => {
    await page.goto("/settings/profile");

    // `useAuth()` 経由の user hydrate 完了を待つ。
    // `profile-name` input は常時 render されるが、user が来るまで value が
    // 空。空でなくなったタイミングをローディング完了の signal とする
    // (Copilot PR #130 round 1 指摘 — networkidle だけだとローディング中
    //  スキャンの可能性があった)。
    await expect(page.getByTestId("profile-name")).not.toHaveValue("");

    await expectNoA11ySeriousViolations(page);
  });
});
