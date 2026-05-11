/**
 * Phase 3b / Issue #107: 言語切替 UI の E2E。
 *
 * 検証フロー:
 *  1. 初回 (cookie 未設定) で /dashboard を開く。Playwright default の
 *     Accept-Language が `en-US,en;q=0.9` のため、`proxy.ts` の
 *     resolveLocale は `en` を選んで cookie に書く想定。
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
  test("LS-01 言語切替 → reload で維持 → 戻せる", async ({ page, context }) => {
    // 1) 初回。Playwright default の Accept-Language は en 系のため
    //    Sidebar が英語表示で立ち上がる想定。
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
