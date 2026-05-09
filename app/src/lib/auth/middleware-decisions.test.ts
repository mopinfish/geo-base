import { describe, it, expect } from "vitest";

import {
  PUBLIC_PATHS,
  AUTH_ONLY_PATHS,
  decideMiddleware,
} from "./middleware-decisions";

describe("decideMiddleware", () => {
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
      const result = decideMiddleware(pathname, false);
      expect(result).toEqual({ kind: "redirect-login", next: pathname });
    });

    it.each([
      "/login",
      "/accept-invitation",
      "/password-reset/request",
      "/password-reset/confirm",
    ])("公開ルート %s はそのまま通す", (pathname) => {
      const result = decideMiddleware(pathname, false);
      expect(result).toEqual({ kind: "next" });
    });

    it("将来追加された未知のルート（例: /reports）も自動的に保護対象になる", () => {
      const result = decideMiddleware("/reports", false);
      expect(result).toEqual({ kind: "redirect-login", next: "/reports" });
    });

    it("公開ルートのサブパス（例: /password-reset/confirm/foo）も公開扱い", () => {
      const result = decideMiddleware(
        "/password-reset/confirm/extra",
        false,
      );
      expect(result).toEqual({ kind: "next" });
    });

    it("公開ルートに似た別名（例: /login-foo）は公開扱いしない", () => {
      const result = decideMiddleware("/login-foo", false);
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
        const result = decideMiddleware(pathname, true);
        expect(result).toEqual({ kind: "redirect-home" });
      },
    );

    it("/accept-invitation は AUTH_ONLY ではないのでそのまま通す（ログイン中の招待受諾を許容）", () => {
      const result = decideMiddleware("/accept-invitation", true);
      expect(result).toEqual({ kind: "next" });
    });

    it.each([
      "/",
      "/tilesets",
      "/teams/abc",
      "/settings/profile",
      "/api-keys",
    ])("保護ルート %s はそのまま通す", (pathname) => {
      const result = decideMiddleware(pathname, true);
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
