"use client";

import { useRouter } from "next/navigation";
import { useTransition } from "react";

import {
  LOCALE_COOKIE_MAX_AGE,
  LOCALE_COOKIE_NAME,
} from "@/i18n/locale-cookie";
import type { Locale } from "@/i18n/config";
import { authClient } from "@/lib/auth/client";

/**
 * 言語切替フロー (Phase 3 / Issue #107):
 *
 *  1. `document.cookie` に `NEXT_LOCALE=<locale>` を即時書き込み (同期)
 *     (`request.ts` の `getRequestConfig` は次の SSR でこの cookie を読む)
 *  2. `PATCH /api/auth/me/locale` を **fire-and-forget** で送る。
 *     `await` しないため UI 反映 (router.refresh) は API レイテンシの影響を
 *     受けない。失敗時 (ログアウト中の 401 や bare network エラー) は cookie
 *     だけで切替は機能するため silent warn にとどめる
 *     (Copilot PR #129 round 1 指摘: API 遅延が UI を blocking しない設計に)。
 *  3. `startTransition(() => router.refresh())` で Server Components を再評価。
 *     **コールバックは同期** であることが React の要件。async にすると
 *     `await` 以降が transition 外で実行され `isPending` が pending を表さない
 *     (Copilot PR #129 round 1 指摘)。
 */
export function useLocaleSwitcher() {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  const switchTo = (locale: Locale) => {
    // 1) cookie は同期で書く
    if (typeof document !== "undefined") {
      document.cookie =
        `${LOCALE_COOKIE_NAME}=${locale}; max-age=${LOCALE_COOKIE_MAX_AGE}; ` +
        `path=/; samesite=lax`;
    }

    // 2) DB 永続化は fire-and-forget。失敗は silent warn。
    void authClient.setPreferredLocale(locale).catch((err) => {
      console.warn(
        "[useLocaleSwitcher] setPreferredLocale failed (cookie still saved):",
        err,
      );
    });

    // 3) startTransition は同期コールバックで呼ぶ (`isPending` 追跡のため)。
    startTransition(() => {
      router.refresh();
    });
  };

  return { switchTo, isPending };
}
