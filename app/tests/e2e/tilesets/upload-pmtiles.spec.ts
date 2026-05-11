import { test } from "../fixtures/authenticated-test";

/**
 * TS-12: PMTiles 直接アップロード。
 *
 * CI で Tigris S3 互換 (moto S3 等) のセットアップが必要なため Phase 3 に先送り。
 * ローカル実行時のスケルトンとして残す。
 *
 * 実装の方針:
 * 1. `/tilesets/new` で type=pmtiles を選択
 * 2. `tests/e2e/fixtures/sample.pmtiles` を `tileset-form-pmtiles-file` に
 *    `setInputFiles`
 * 3. submit → `/tilesets/<id>` への遷移を待つ
 * 4. heading に tileset 名が表示されることを確認
 */
test.skip("TS-12 PMTiles 直接アップロード", async () => {
  // Pending: Phase 3 で moto S3 セットアップ後に実装
});
