"use client";

import { useTranslations } from "next-intl";

import { Sidebar } from "./sidebar";
import { useAuth } from "@/lib/auth/context";
import { User } from "lucide-react";

interface AdminLayoutProps {
  children: React.ReactNode;
}

export function AdminLayout({ children }: AdminLayoutProps) {
  const { user, isLoading } = useAuth();
  // i18n Phase 3 (#107) smoke: 翻訳経路を全画面で必ず通すため Header に
  // 1 文字列だけ next-intl 経由で出す。文字列実体は
  // `app/src/locales/<locale>/common.json:app.title`。
  // PR-B で言語切替 UI / Sidebar の他文字列を catalog 化する。
  const t = useTranslations("common");

  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      <main className="md:pl-64">
        {/* ヘッダー */}
        <header className="sticky top-0 z-30 border-b bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/60">
          <div className="container mx-auto flex h-14 items-center justify-between px-6">
            <div className="text-sm font-medium text-muted-foreground">
              {t("app.title")}
            </div>
            {!isLoading && user && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <User className="h-4 w-4" />
                <span className="hidden sm:inline">{user.email}</span>
              </div>
            )}
          </div>
        </header>

        {/* メインコンテンツ */}
        <div className="container mx-auto p-6 pt-6">{children}</div>
      </main>
    </div>
  );
}
