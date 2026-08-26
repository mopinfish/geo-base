import { describe, expect, it } from "vitest";

import { parseAcceptLanguage } from "./parse-accept-language";

describe("parseAcceptLanguage", () => {
  it("先頭がサポート locale ならそれを返す", () => {
    expect(parseAcceptLanguage("ja")).toBe("ja");
    expect(parseAcceptLanguage("en")).toBe("en");
  });

  it("q= 付き priority を捨てて先頭の primary subtag を見る", () => {
    expect(parseAcceptLanguage("ja, en;q=0.8")).toBe("ja");
    expect(parseAcceptLanguage("en;q=1.0, ja;q=0.5")).toBe("en");
  });

  it("region tag (xx-YY) は primary subtag のみ抽出して判定", () => {
    expect(parseAcceptLanguage("ja-JP")).toBe("ja");
    expect(parseAcceptLanguage("en-US, ja;q=0.5")).toBe("en");
  });

  it("先頭が unsupported なら次の候補を見る", () => {
    expect(parseAcceptLanguage("zh-CN, ja;q=0.5")).toBe("ja");
    expect(parseAcceptLanguage("fr, de, en;q=0.3")).toBe("en");
  });

  it("どれも合致しなければ null", () => {
    expect(parseAcceptLanguage("fr, de")).toBeNull();
    expect(parseAcceptLanguage("zh-CN, ko")).toBeNull();
  });

  it("空文字 / 空白入力は null", () => {
    expect(parseAcceptLanguage("")).toBeNull();
    expect(parseAcceptLanguage(" ")).toBeNull();
  });

  it("大文字混在を正規化", () => {
    expect(parseAcceptLanguage("JA")).toBe("ja");
    expect(parseAcceptLanguage("EN-us")).toBe("en");
  });
});
