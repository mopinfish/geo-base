/**
 * Regression: Issue #101 / PR #104.
 *
 * 「PMTiles datasource の url に s3://bucket/key 形式が入って欲しい」要件。
 * 修正前は http(s) のみが許容されていて s3:// が validation で reject されていた。
 * fix: Pydantic model で s3:// を許容するように。
 */
import { test, expect } from "../fixtures/authenticated-test";
import { resetDatabase } from "../utils/reset-db";
import { createDatasource } from "../fixtures/factories";
import { loginAsAdmin } from "../utils/session";

test.beforeAll(async () => {
  await loginAsAdmin();
  await resetDatabase();
});

test("DS-09 @regression s3:// URL の datasource が API 経由で作成・表示できる (#101)", async ({
  page,
}) => {
  await createDatasource({
    name: "s3-scheme-regression",
    url: "s3://geo-base-tiles/regression/sample.pmtiles",
    type: "pmtiles",
  });
  await page.goto("/datasources");
  await expect(
    page.getByText("s3://geo-base-tiles/regression/sample.pmtiles"),
  ).toBeVisible({ timeout: 10_000 });
});
