import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { decideMiddleware } from "@/lib/auth/middleware-decisions";

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const hasRefresh = !!request.cookies.get("geo_base_refresh");
  const decision = decideMiddleware(pathname, hasRefresh);

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

// matcher から /api/ を除外する。
// authClient (`app/src/lib/auth/client.ts`) は NEXT_PUBLIC_API_URL 未設定時に
// 相対パス `/api/auth/...` を叩く（dev では next.config.ts の rewrites で
// FastAPI に転送される）。middleware が /api/* にマッチすると、未ログイン状態の
// /api/auth/login すら /login にリダイレクトされてログインフローが壊れるため。
export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
