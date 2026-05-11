/**
 * A11y assertion helper (Phase 3 試験導入)。
 *
 * @axe-core/playwright で page 全体をスキャンし、`serious` または `critical`
 * 違反のみを失敗扱いにする。minor / moderate は warning として log 出力する。
 * 初期導入時に既存ページが全部赤くなって CI が止まる事態を避けるため、
 * 閾値は徐々に厳しくする方針。
 */
import AxeBuilder from "@axe-core/playwright";
import { expect, type Page } from "@playwright/test";

export async function expectNoA11ySeriousViolations(page: Page): Promise<void> {
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
