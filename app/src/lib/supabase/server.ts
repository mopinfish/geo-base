import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

/**
 * Cookieの型定義
 */
interface CookieToSet {
  name: string;
  value: string;
  options?: {
    domain?: string;
    path?: string;
    maxAge?: number;
    httpOnly?: boolean;
    secure?: boolean;
    sameSite?: "strict" | "lax" | "none";
  };
}

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
 * サーバーコンポーネント・サーバーアクション用のSupabaseクライアントを作成
 * 
 * 環境変数は以下のいずれかを使用可能：
 * - NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY（推奨・新形式）
 * - NEXT_PUBLIC_SUPABASE_ANON_KEY（レガシー形式）
 * 
 * @returns Promise<Supabase Server Client>
 */
export async function createClient() {
  const cookieStore = await cookies();

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    getSupabaseKey(),
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet: CookieToSet[]) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options)
            );
          } catch {
            // Server Componentからの呼び出しでは`setAll`が失敗する可能性がある
            // ミドルウェアでセッションをリフレッシュしているので無視して良い
          }
        },
      },
    }
  );
}

/**
 * 現在のユーザーを取得
 * 
 * @returns Promise<User | null>
 */
export async function getUser() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  return user;
}

/**
 * 現在のセッションを取得
 * 
 * @returns Promise<Session | null>
 */
export async function getSession() {
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();
  return session;
}
