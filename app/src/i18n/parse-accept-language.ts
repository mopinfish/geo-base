/**
 * `Accept-Language` header から `LOCALES` に含まれる locale を抽出する
 * 共通ヘルパ (Phase 3 / Issue #107)。
 *
 * `proxy.ts` (middleware) と `request.ts` (Server Components 用 next-intl
 * config) の両方から呼ばれる。両者の解決ロジックが drift しないよう
 * 集約する目的 (Copilot PR #127 round 2 指摘)。
 *
 * 仕様:
 * - カンマ区切り (例 `ja, en;q=0.8, zh-CN;q=0.5`) の先頭から評価
 * - 各 token は `;q=...` を捨てて `xx-YY` を `xx` に正規化 (region tag は
 *   現状の `LOCALES` に含まれないので primary subtag のみで判定)
 * - 最初に `LOCALES` に合致した locale を返す。なければ `null`
 *
 * 将来 region 付き locale (例 `en-US`) を扱う必要が出たら本ヘルパを拡張
 * すれば proxy.ts / request.ts 両方に反映される。
 */

import { LOCALES, type Locale } from "./config";

export function parseAcceptLanguage(header: string): Locale | null {
  if (!header) return null;
  for (const part of header.split(",")) {
    const tag = part
      .split(";")[0]
      ?.trim()
      .split("-")[0]
      ?.toLowerCase();
    if (tag && (LOCALES as readonly string[]).includes(tag)) {
      return tag as Locale;
    }
  }
  return null;
}
