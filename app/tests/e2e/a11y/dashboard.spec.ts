import { test } from "../fixtures/authenticated-test";
import { expectNoA11ySeriousViolations } from "./_helper";

test("a11y: / serious/critical 違反なし", async ({ page }) => {
  await page.goto("/");
  // Issue #123: dashboard はロード中に skeleton / "-" placeholder が出るため、
  // axe スキャンを発火させる前に「データ取得完了」(= 件数 placeholder が
  // 数値に置き換わる) を待つ。これで full E2E で 100% / nightly でも flake
  // 0 になることを期待する。
  await expectNoA11ySeriousViolations(page, {
    awaitReady: {
      testid: "dashboard-tilesets-count",
      expectTextNot: "-",
      timeout: 15_000,
    },
  });
});
