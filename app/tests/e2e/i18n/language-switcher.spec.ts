/**
 * Phase 3b / Issue #107: 言語切替 UI の E2E。
 *
 * 検証フロー:
 *  1. 初回 (cookie 未設定) でダッシュボード (`/`) を開く。
 *     `test.use({ locale: "en-US" })` で Accept-Language を明示的に固定して
 *     あるため、`proxy.ts` の resolveLocale は `en` を選んで cookie に書く。
 *     → Sidebar に `Dashboard` (en) が表示される。
 *  2. LanguageSwitcher を開き `日本語` を選択。
 *     → router.refresh() で RSC が再評価され `ダッシュボード` (ja) に切替。
 *  3. page.reload() しても `ダッシュボード` (= cookie + DB 永続化が効いている)。
 *  4. `NEXT_LOCALE` cookie が `ja` に上書きされていること。
 *  5. 戻して `English` を選択 → `Dashboard` に戻る。
 *
 * 認証中 user に対しては DB の `users.preferred_locale` も更新されるが、
 * 本 spec では cookie + UI の挙動だけ検証する (DB 永続化は
 * `api/tests/test_auth_locale.py` 側で別途カバー)。
 */
import { expect, test } from "../fixtures/authenticated-test";

const SIDEBAR_NAV = "nav";

test.describe("LanguageSwitcher", () => {
  // Playwright default の Accept-Language は実行環境 (ローカル / CI) の
  // ブラウザ設定に依存して flake し得るため、明示的に en-US に固定する
  // (Copilot PR #129 round 1 指摘)。
  test.use({ locale: "en-US" });

  test("LS-01 言語切替 → reload で維持 → 戻せる", async ({ page, context }) => {
    // 1) 初回。locale=en-US で Accept-Language が en 系に固定されているため
    //    proxy.ts は NEXT_LOCALE cookie を `en` で初期化し、Sidebar が英語表示。
    await page.goto("/");

    const sidebar = page.locator(SIDEBAR_NAV);
    await expect(sidebar.getByText("Dashboard", { exact: true })).toBeVisible();

    // 2) Switcher → 日本語
    await page.getByTestId("language-switcher").click();
    await page.getByTestId("language-switcher-ja").click();

    await expect(
      sidebar.getByText("ダッシュボード", { exact: true }),
    ).toBeVisible();

    // 3) reload 後も `ダッシュボード`
    await page.reload();
    await expect(
      sidebar.getByText("ダッシュボード", { exact: true }),
    ).toBeVisible();

    // 4) NEXT_LOCALE cookie が ja
    const cookies = await context.cookies();
    const nextLocale = cookies.find((c) => c.name === "NEXT_LOCALE");
    expect(nextLocale?.value).toBe("ja");

    // 5) Switcher → English に戻す
    await page.getByTestId("language-switcher").click();
    await page.getByTestId("language-switcher-en").click();

    await expect(sidebar.getByText("Dashboard", { exact: true })).toBeVisible();

    const cookiesAfter = await context.cookies();
    const nextLocaleAfter = cookiesAfter.find((c) => c.name === "NEXT_LOCALE");
    expect(nextLocaleAfter?.value).toBe("en");
  });
});
