import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";


const PROTECTED_PATHS = [
  "/tilesets", "/features", "/datasources",
  "/teams", "/api-keys", "/settings",
];

const AUTH_ONLY_PATHS = [
  "/login",
  "/password-reset/request",
  "/password-reset/confirm",
];


export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const hasRefresh = !!request.cookies.get("geo_base_refresh");

  const isProtected =
    pathname === "/" || PROTECTED_PATHS.some((p) => pathname.startsWith(p));
  const isAuthPage = AUTH_ONLY_PATHS.includes(pathname);

  if (isProtected && !hasRefresh) {
    const url = new URL("/login", request.url);
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }

  if (isAuthPage && hasRefresh) {
    return NextResponse.redirect(new URL("/", request.url));
  }

  return NextResponse.next();
}


export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
