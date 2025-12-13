import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

/**
 * サーバーコンポーネント・サーバーアクション用のSupabaseクライアントを作成
 * 
 * @returns Promise<Supabase Server Client>
 */
export async function createClient() {
  const cookieStore = await cookies();

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet) {
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
