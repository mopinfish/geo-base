/**
 * Middleware decision logic (route guard) — pure, framework-agnostic.
 *
 * Allow-list 方式（issue #46）:
 * - PUBLIC_PATHS に列挙されたパスは未ログインでもアクセス可
 * - それ以外は refresh cookie を要求し、無ければ /login にリダイレクト
 * - AUTH_ONLY_PATHS にログイン済みでアクセスした場合は / にリダイレクト
 *
 * 切り出した理由: `next/server` の NextRequest/NextResponse は単体テストで
 * モックしにくいので、決定ロジックを純粋関数に分離してテスト容易にする。
 */

export const PUBLIC_PATHS = [
  "/login",
  "/accept-invitation",
  "/password-reset/request",
  "/password-reset/confirm",
] as const;

export const AUTH_ONLY_PATHS = [
  "/login",
  "/password-reset/request",
  "/password-reset/confirm",
] as const;

export type MiddlewareDecision =
  | { kind: "next" }
  | { kind: "redirect-login"; next: string }
  | { kind: "redirect-home" };

const matchesAny = (paths: readonly string[], pathname: string): boolean =>
  paths.some((p) => pathname === p || pathname.startsWith(p + "/"));

export function decideMiddleware(
  pathname: string,
  hasRefresh: boolean,
): MiddlewareDecision {
  const isPublic = matchesAny(PUBLIC_PATHS, pathname);
  const isAuthOnly = matchesAny(AUTH_ONLY_PATHS, pathname);

  if (isAuthOnly && hasRefresh) {
    return { kind: "redirect-home" };
  }

  if (!isPublic && !hasRefresh) {
    return { kind: "redirect-login", next: pathname };
  }

  return { kind: "next" };
}
