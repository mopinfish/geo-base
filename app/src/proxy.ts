import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { decideProxy } from "@/lib/auth/proxy-decisions";

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const hasRefresh = !!request.cookies.get("geo_base_refresh");
  const decision = decideProxy(pathname, hasRefresh);

  switch (decision.kind) {
    case "redirect-login": {
      const url = new URL("/login", request.url);
      url.searchParams.set("next", decision.next);
      return NextResponse.redirect(url);
    }
    case "redirect-home":
      return NextResponse.redirect(new URL("/", request.url));
    case "next":
      return NextResponse.next();
    default: {
      // 網羅性チェック（実行時の保険）— 想定外の値が来ても undefined は返さない
      const _exhaustive: never = decision;
      void _exhaustive;
      return NextResponse.next();
    }
  }
}

// matcher パターン（仕様は proxy-decisions.ts の `PROXY_MATCHER` を参照）。
//
// Next.js (Turbopack) は `config.matcher` を **コンパイル時に静的解析** するため、
// 別ファイルの定数を import しても受け付けず、リテラル文字列を直接渡す必要がある。
// そのため `proxy-decisions.ts` の `PROXY_MATCHER` と本ファイルのリテラル
// は **同一文字列** に保つ必要があり、テスト
// （`proxy-decisions.test.ts` の "matcher と proxy.ts のリテラル同期"）
// で同期を担保している。
export const config = {
  matcher: ["/((?!api(?:/|$)|_next/|.*\\.\\w+$).*)"],
};
