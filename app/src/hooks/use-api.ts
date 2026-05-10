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

    // 認証状態の変更を購読。
    // `subscribe` はマウント時に同期で 1 度コールバックを発火するが、その時点では
    // AuthClient の初期 refresh が完了しておらず `isLoading=true` / accessToken=null
    // のままになっている。ここで無条件に `setIsReady(true)` してしまうと、購読側
    // (e.g. /teams, /api-keys ページ) が token 未取得のまま fetch を走らせて 401 で
    // 落ちる。`isLoading` が解けてから ready 扱いにする。
    const unsubscribe = authClient.subscribe((state) => {
      const newToken = authClient.getAccessToken();
      api.setToken(newToken);
      if (!state.isLoading) {
        setIsReady(true);
      }
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
