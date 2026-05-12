/**
 * i18n missing-key 検知テスト (Phase 3 / Issue #107)。
 *
 * 全 namespace で `en` と `ja` の key set が完全一致することを assert する。
 * 翻訳忘れ / 余分なキー / typo を CI で検出する目的。
 *
 * 新しい namespace を追加した際は `app/src/i18n/config.ts:NAMESPACES`
 * 配列に追加すれば本テストが自動でカバーする。
 */

import { describe, expect, it } from "vitest";

import { LOCALES, NAMESPACES } from "@/i18n/config";

function flatKeys(obj: unknown, prefix = ""): string[] {
  if (!obj || typeof obj !== "object") return [];
  return Object.entries(obj as Record<string, unknown>).flatMap(([k, v]) => {
    const key = prefix ? `${prefix}.${k}` : k;
    if (v && typeof v === "object" && !Array.isArray(v)) {
      return flatKeys(v, key);
    }
    return [key];
  });
}

describe("locale keysets", () => {
  for (const ns of NAMESPACES) {
    it(`${ns}: en と ja の keys が一致`, async () => {
      const en = (await import(`@/locales/en/${ns}.json`)).default;
      const ja = (await import(`@/locales/ja/${ns}.json`)).default;
      const enKeys = flatKeys(en).sort();
      const jaKeys = flatKeys(ja).sort();
      expect(jaKeys, `missing or extra keys in ja/${ns}.json`).toEqual(enKeys);
    });
  }

  it("LOCALES に en と ja が含まれる (smoke)", () => {
    expect(LOCALES).toContain("en");
    expect(LOCALES).toContain("ja");
  });
});
