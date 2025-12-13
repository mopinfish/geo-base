import { createClient } from "@/lib/supabase/server";
import { NextResponse } from "next/server";

/**
 * OAuth認証コールバックハンドラー
 * 
 * Supabase Auth の OAuth フロー完了後にリダイレクトされるエンドポイント
 * 認証コードをセッションに交換し、ユーザーを適切なページにリダイレクトする
 */
export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  const next = searchParams.get("next") ?? "/";

  if (code) {
    const supabase = await createClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    
    if (!error) {
      // セッション交換成功 - リダイレクト先へ
      const forwardedHost = request.headers.get("x-forwarded-host");
      const isLocalEnv = process.env.NODE_ENV === "development";
      
      if (isLocalEnv) {
        // ローカル環境では origin を使用
        return NextResponse.redirect(`${origin}${next}`);
      } else if (forwardedHost) {
        // Vercel等のプロキシ環境では x-forwarded-host を使用
        return NextResponse.redirect(`https://${forwardedHost}${next}`);
      } else {
        return NextResponse.redirect(`${origin}${next}`);
      }
    }
  }

  // エラー時はログインページにリダイレクト（エラーメッセージ付き）
  return NextResponse.redirect(`${origin}/login?error=auth_callback_error`);
}
