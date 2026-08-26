"use client";

import { Globe } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { Locale } from "@/i18n/config";
import { LOCALES } from "@/i18n/config";
import { useLocaleSwitcher } from "@/hooks/use-locale-switcher";

/**
 * Header に置く地球儀アイコン dropdown。クリックで言語を切替。
 *
 * 翻訳ロード経路 / cookie 永続化 / DB 永続化 / RSC 再評価は
 * `useLocaleSwitcher` に集約 (Phase 3 / Issue #107)。
 *
 * a11y: 単一選択の設定なので `DropdownMenuRadioGroup` + `DropdownMenuRadioItem`
 * (= `role="menuitemradio"` + `aria-checked`) を使う。Screen reader が
 * 「選択中」状態を確実に読み上げられる
 * (Copilot PR #129 round 2 指摘)。
 *
 * 多重クリック抑止:
 * - 現在 locale と同じ項目は `disabled` (= no-op に変えるより明示的)
 * - `isPending` 中は両項目を `disabled` にして、dropdown が開いた状態での
 *   高速連打を防ぐ (Copilot PR #129 round 2 指摘)
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
        <DropdownMenuRadioGroup
          value={current}
          onValueChange={(value) => {
            // RadioGroup は同一 value 選択でも onValueChange を呼ばないが、
            // 念のため明示的に no-op (UX 上の保険)。
            if (value === current) return;
            switchTo(value as Locale);
          }}
        >
          {LOCALES.map((locale) => (
            <DropdownMenuRadioItem
              key={locale}
              value={locale}
              disabled={isPending || locale === current}
              data-testid={`language-switcher-${locale}`}
            >
              {t(`label_${locale}`)}
            </DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
