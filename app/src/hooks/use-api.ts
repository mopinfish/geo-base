"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { authClient } from "@/lib/auth/client";

/**
 * 認証付きAPIクライアントを提供するフック
 *
 * AuthClient のセッションからアクセストークンを取得し、
 * APIクライアントに設定する
 *
 * @returns { api, isReady } - APIクライアントと準備完了状態
 */
export function useApi() {
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    // 初期トークン設定
    const token = authClient.getAccessToken();
    api.setToken(token);

    // 認証状態の変更を購読
    const unsubscribe = authClient.subscribe(() => {
      const newToken = authClient.getAccessToken();
      api.setToken(newToken);
      setIsReady(true);
    });

    return unsubscribe;
  }, []);

  return { api, isReady };
}

/**
 * 認証トークンを一度だけ設定するユーティリティ
 * Server Actionsや非コンポーネントで使用
 */
export async function setupApiToken(): Promise<void> {
  const token = authClient.getAccessToken();
  if (token) {
    api.setToken(token);
  }
}
