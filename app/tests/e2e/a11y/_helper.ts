/**
 * A11y assertion helper (Phase 3 試験導入)。
 *
 * @axe-core/playwright で page 全体をスキャンし、`serious` または `critical`
 * 違反のみを失敗扱いにする。minor / moderate は warning として log 出力する。
 * 初期導入時に既存ページが全部赤くなって CI が止まる事態を避けるため、
 * 閾値は徐々に厳しくする方針。
 *
 * Flake 対策 (Issue #123): ローディング中の skeleton / disabled button が
 * 一時的に a11y 違反を出すケースが nightly で 1 件捕捉された (dashboard)。
 * 呼び出し側は `awaitReady` で「データロード完了の signal となる testid」を
 * 渡せるようにし、axe スキャン前にその要素が visible かつ「ローディング
 * placeholder」でないことを確認できる。
 */
import AxeBuilder from "@axe-core/playwright";
import { expect, type Locator, type Page } from "@playwright/test";

export interface ExpectNoA11ySeriousViolationsOptions {
  /**
   * 指定した testid を持つ要素の表示を `timeout` ミリ秒以内に待ってから
   * axe をスキャンする。動的データ取得後の安定状態を担保するために使う。
   *
   * `expectTextNot` を指定すると、当該要素のテキストがそれと一致しない
   * 状態 (= ロード完了後の値) になるまで待つ。
   */
  awaitReady?: {
    testid: string;
    expectTextNot?: string;
    timeout?: number;
  };
}

async function waitForReadyState(
  page: Page,
  opts: ExpectNoA11ySeriousViolationsOptions["awaitReady"],
): Promise<void> {
  if (!opts) return;
  const locator: Locator = page.getByTestId(opts.testid);
  const timeout = opts.timeout ?? 10_000;
  await expect(locator).toBeVisible({ timeout });
  if (opts.expectTextNot !== undefined) {
    // ローディング中の placeholder ("-" 等) が外れるまで待つ。
    await expect(locator).not.toHaveText(opts.expectTextNot, { timeout });
  }
}

export async function expectNoA11ySeriousViolations(
  page: Page,
  options: ExpectNoA11ySeriousViolationsOptions = {},
): Promise<void> {
  await waitForReadyState(page, options.awaitReady);

  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();

  const severeViolations = results.violations.filter(
    (v) => v.impact === "serious" || v.impact === "critical",
  );

  if (severeViolations.length > 0) {
    console.log(
      JSON.stringify(
        severeViolations.map((v) => ({
          id: v.id,
          impact: v.impact,
          help: v.help,
          nodes: v.nodes.length,
        })),
        null,
        2,
      ),
    );
  }

  expect(
    severeViolations,
    `Found ${severeViolations.length} serious/critical A11y violations`,
  ).toHaveLength(0);
}
