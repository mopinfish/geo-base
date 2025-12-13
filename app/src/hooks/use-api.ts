"use client";

import { useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";

/**
 * 認証付きAPIクライアントを提供するフック
 * 
 * Supabaseのセッションからアクセストークンを取得し、
 * APIクライアントに設定する
 */
export function useApi() {
  const setupToken = useCallback(async () => {
    const supabase = createClient();
    const { data: { session } } = await supabase.auth.getSession();
    
    if (session?.access_token) {
      api.setToken(session.access_token);
    } else {
      api.setToken(null);
    }
  }, []);

  useEffect(() => {
    // 初期設定
    setupToken();

    // 認証状態の変更を監視
    const supabase = createClient();
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        if (session?.access_token) {
          api.setToken(session.access_token);
        } else {
          api.setToken(null);
        }
      }
    );

    return () => subscription.unsubscribe();
  }, [setupToken]);

  return api;
}

/**
 * 認証トークンを一度だけ設定するユーティリティ
 * Server Actionsや非コンポーネントで使用
 */
export async function setupApiToken(): Promise<void> {
  const supabase = createClient();
  const { data: { session } } = await supabase.auth.getSession();
  
  if (session?.access_token) {
    api.setToken(session.access_token);
  }
}
