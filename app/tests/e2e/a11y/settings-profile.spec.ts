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
 *
 * ローディング状態:
 * - `/settings/profile` は `useAuth()` の user が null の間 spinner のみ
 *   描画する (form 自体は render されない)。
 * - user が来てから form が描画され、`profile-name` testid を持つ input が
 *   出現する。よって `profile-name` の visible 状態を待てば
 *   「ユーザー確定後のフォーム表示」を待ったことになる。
 * - 旧実装の `not.toHaveValue("")` は user.name が空文字のユーザーで
 *   timeout する可能性があったため、`awaitReady: { testid }` の visibility
 *   方式に変更 (Copilot PR #130 round 2 指摘)。
 */
import { test } from "../fixtures/authenticated-test";

import { expectNoA11ySeriousViolations } from "./_helper";

test.describe("a11y: /settings", () => {
  test("a11y: /settings/profile serious/critical 違反なし", async ({
    page,
  }) => {
    await page.goto("/settings/profile");
    await expectNoA11ySeriousViolations(page, {
      awaitReady: { testid: "profile-name" },
    });
  });
});
