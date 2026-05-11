"use client";

import { Globe } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { Locale } from "@/i18n/config";
import { useLocaleSwitcher } from "@/hooks/use-locale-switcher";

/**
 * Header に置く地球儀アイコン dropdown。クリックで言語を切替。
 * 翻訳ロード経路 / cookie 永続化 / DB 永続化 / RSC 再評価は
 * `useLocaleSwitcher` に集約 (Phase 3 / Issue #107)。
 *
 * 現在の locale はアイコン横に `EN` / `JA` で表示し、`aria-current` で
 * dropdown の選択中項目を SR にも伝える。
 */
export function LanguageSwitcher() {
  const t = useTranslations("common.language");
  const current = useLocale() as Locale;
  const { switchTo, isPending } = useLocaleSwitcher();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          aria-label={t("switch")}
          disabled={isPending}
          data-testid="language-switcher"
        >
          <Globe className="h-4 w-4" />
          <span className="ml-2 text-xs uppercase">{current}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {/*
         * 現在 locale と一致する項目は disabled。
         * 同一 locale 選択で cookie 上書き + API 呼出 + RSC refresh が無駄に
         * 走るのを防ぐ (Copilot PR #129 round 1 指摘)。
         */}
        <DropdownMenuItem
          onClick={() => switchTo("en")}
          data-testid="language-switcher-en"
          aria-current={current === "en"}
          disabled={current === "en"}
        >
          {t("label_en")}
        </DropdownMenuItem>
        <DropdownMenuItem
          onClick={() => switchTo("ja")}
          data-testid="language-switcher-ja"
          aria-current={current === "ja"}
          disabled={current === "ja"}
        >
          {t("label_ja")}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
