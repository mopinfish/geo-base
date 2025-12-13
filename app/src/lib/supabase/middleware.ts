import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

/**
 * Supabaseキーを取得（新形式優先、レガシーにフォールバック）
 */
function getSupabaseKey(): string {
  return (
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ?? 
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );
}

/**
 * ミドルウェア用のSupabaseクライアントを作成し、セッションを更新
 * 
 * 環境変数は以下のいずれかを使用可能：
 * - NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY（推奨・新形式）
 * - NEXT_PUBLIC_SUPABASE_ANON_KEY（レガシー形式）
 * 
 * @param request - Next.js Request
 * @returns Promise<NextResponse>
 */
export async function updateSession(request: NextRequest) {
  let supabaseResponse = NextResponse.next({
    request,
  });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    getSupabaseKey(),
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) =>
            request.cookies.set(name, value)
          );
          supabaseResponse = NextResponse.next({
            request,
          });
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          );
        },
      },
    }
  );

  // 重要: createServerClient と supabase.auth.getUser() の間に
  // ロジックを記述しないでください。単純なミスでも
  // ユーザーがランダムにログアウトされる問題が発生する可能性があります。

  const {
    data: { user },
  } = await supabase.auth.getUser();

  // 認証が必要なルートの定義
  const protectedRoutes = [
    "/",
    "/tilesets",
    "/features",
    "/datasources",
    "/settings",
  ];

  // 認証不要なルート（ログインページなど）
  const publicRoutes = ["/login", "/auth/callback"];

  const isProtectedRoute = protectedRoutes.some(
    (route) =>
      request.nextUrl.pathname === route ||
      request.nextUrl.pathname.startsWith(route + "/")
  );

  const isPublicRoute = publicRoutes.some(
    (route) =>
      request.nextUrl.pathname === route ||
      request.nextUrl.pathname.startsWith(route + "/")
  );

  // 未認証ユーザーが保護されたルートにアクセスした場合、ログインページにリダイレクト
  if (!user && isProtectedRoute && !isPublicRoute) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("redirectTo", request.nextUrl.pathname);
    return NextResponse.redirect(url);
  }

  // 認証済みユーザーがログインページにアクセスした場合、ダッシュボードにリダイレクト
  if (user && request.nextUrl.pathname === "/login") {
    const redirectTo = request.nextUrl.searchParams.get("redirectTo") || "/";
    const url = request.nextUrl.clone();
    url.pathname = redirectTo;
    url.searchParams.delete("redirectTo");
    return NextResponse.redirect(url);
  }

  // 重要: supabaseResponse オブジェクトをそのまま返してください。
  // NextResponse.next() を使用して新しいレスポンスオブジェクトを作成すると、
  // 以下の問題が発生する可能性があります:
  // 1) Cookie を正しくブラウザに渡せなくなる
  // 2) セッションの更新が失われる

  return supabaseResponse;
}
