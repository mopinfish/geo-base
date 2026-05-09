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
  }
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
