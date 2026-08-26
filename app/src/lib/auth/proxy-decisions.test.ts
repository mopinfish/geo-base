import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  PUBLIC_PATHS,
  AUTH_ONLY_PATHS,
  PROXY_MATCHER,
  decideProxy,
} from "./proxy-decisions";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

describe("decideProxy", () => {
  describe("未ログイン (hasRefresh=false)", () => {
    it.each([
      "/",
      "/tilesets",
      "/tilesets/abc-123",
      "/tilesets/new",
      "/features",
      "/features/abc/edit",
      "/datasources",
      "/datasources/new",
      "/teams",
      "/teams/abc-123",
      "/api-keys",
      "/settings",
      "/settings/profile",
      "/settings/password",
    ])("保護ルート %s は /login にリダイレクトする", (pathname) => {
      const result = decideProxy(pathname, false);
      expect(result).toEqual({ kind: "redirect-login", next: pathname });
    });

    it.each([
      "/login",
      "/accept-invitation",
      "/password-reset/request",
      "/password-reset/confirm",
    ])("公開ルート %s はそのまま通す", (pathname) => {
      const result = decideProxy(pathname, false);
      expect(result).toEqual({ kind: "next" });
    });

    it("将来追加された未知のルート（例: /reports）も自動的に保護対象になる", () => {
      const result = decideProxy("/reports", false);
      expect(result).toEqual({ kind: "redirect-login", next: "/reports" });
    });

    it("公開ルートのサブパス（例: /password-reset/confirm/foo）も公開扱い", () => {
      const result = decideProxy(
        "/password-reset/confirm/extra",
        false,
      );
      expect(result).toEqual({ kind: "next" });
    });

    it("公開ルートに似た別名（例: /login-foo）は公開扱いしない", () => {
      const result = decideProxy("/login-foo", false);
      expect(result).toEqual({ kind: "redirect-login", next: "/login-foo" });
    });
  });

  describe("ログイン済み (hasRefresh=true)", () => {
    it.each([
      "/login",
      "/password-reset/request",
      "/password-reset/confirm",
    ])(
      "AUTH_ONLY パス %s に到達したら / にリダイレクトする",
      (pathname) => {
        const result = decideProxy(pathname, true);
        expect(result).toEqual({ kind: "redirect-home" });
      },
    );

    it("/accept-invitation は AUTH_ONLY ではないのでそのまま通す（ログイン中の招待受諾を許容）", () => {
      const result = decideProxy("/accept-invitation", true);
      expect(result).toEqual({ kind: "next" });
    });

    it.each([
      "/",
      "/tilesets",
      "/teams/abc",
      "/settings/profile",
      "/api-keys",
    ])("保護ルート %s はそのまま通す", (pathname) => {
      const result = decideProxy(pathname, true);
      expect(result).toEqual({ kind: "next" });
    });
  });

  describe("定数定義の一貫性", () => {
    it("AUTH_ONLY_PATHS は PUBLIC_PATHS のサブセットである（保護→公開の隙間が無い）", () => {
      for (const p of AUTH_ONLY_PATHS) {
        expect(PUBLIC_PATHS).toContain(p);
      }
    });
  });
});

describe("PROXY_MATCHER", () => {
  // Next.js は matcher 文字列を内部で正規表現にコンパイルする。
  // ここでは同じ正規表現として直接評価し、対象/除外を検証する。
  const re = new RegExp(`^${PROXY_MATCHER}$`);

  it.each([
    "/",
    "/login",
    "/tilesets",
    "/tilesets/abc-123",
    "/api-keys", // /api で始まるが API ではない UI ルート — 除外されてはいけない
    "/api-keys/new",
    "/teams/abc-123",
    "/settings/profile",
    "/accept-invitation",
  ])("UI ルート %s は proxy 対象（matcher にマッチ）", (pathname) => {
    expect(re.test(pathname)).toBe(true);
  });

  it.each([
    "/api",
    "/api/",
    "/api/auth/login",
    "/api/auth/refresh",
    "/api/health",
    "/api/tilesets",
    "/_next/static/foo",
    "/_next/image",
    "/_next/data/build/index.json",
    "/_next/webpack-hmr",
    "/favicon.ico",
    "/robots.txt",
    "/manifest.json",
    "/file.svg",
    "/logo.png",
  ])("除外パス %s は proxy を skip（matcher にマッチしない）", (pathname) => {
    expect(re.test(pathname)).toBe(false);
  });

  // Next.js (Turbopack) は config.matcher にリテラル文字列を要求するため、
  // proxy.ts では PROXY_MATCHER を import 経由で使えない。
  // 同一ファイル内のリテラルが PROXY_MATCHER と一致することを保証する。
  it("proxy.ts のリテラルが PROXY_MATCHER と同期している", () => {
    const proxySrc = readFileSync(
      path.resolve(__dirname, "../../proxy.ts"),
      "utf8",
    );
    // matcher: ["..."] からリテラルを抜き出し
    const m = proxySrc.match(/matcher:\s*\[\s*"((?:[^"\\]|\\.)*)"\s*\]/);
    expect(m, "proxy.ts に matcher: [\"...\"] 形式のリテラルが見つからない").not.toBeNull();
    // JSON.parse で JS 文字列リテラルのエスケープを解決
    const literal = JSON.parse(`"${m![1]}"`);
    expect(literal).toBe(PROXY_MATCHER);
  });
});
