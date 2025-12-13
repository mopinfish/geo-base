import { type NextRequest } from "next/server";
import { updateSession } from "@/lib/supabase/middleware";

/**
 * Next.js Middleware
 * 全てのリクエストでSupabaseセッションを更新し、認証状態をチェック
 */
export async function middleware(request: NextRequest) {
  return await updateSession(request);
}

/**
 * ミドルウェアを適用するパスの設定
 * 静的ファイルやAPIルートを除外
 */
export const config = {
  matcher: [
    /*
     * 以下を除く全てのパスにマッチ:
     * - _next/static (静的ファイル)
     * - _next/image (画像最適化ファイル)
     * - favicon.ico (ファビコン)
     * - 画像ファイル (.svg, .png, .jpg, .jpeg, .gif, .webp)
     */
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
