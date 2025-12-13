import { createBrowserClient } from "@supabase/ssr";

/**
 * ブラウザ（クライアントコンポーネント）用のSupabaseクライアントを作成
 * 
 * 環境変数は以下のいずれかを使用可能：
 * - NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY（推奨・新形式）
 * - NEXT_PUBLIC_SUPABASE_ANON_KEY（レガシー形式）
 * 
 * @returns Supabase Browser Client
 */
export function createClient() {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
  
  // 新形式（publishable key）を優先、なければレガシー（anon key）を使用
  const supabaseKey = 
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ?? 
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

  return createBrowserClient(supabaseUrl, supabaseKey);
}
