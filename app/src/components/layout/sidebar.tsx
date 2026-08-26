"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Map,
  Layers,
  Database,
  Settings,
  Home,
  LogOut,
  Menu,
  X,
  Loader2,
  Users,
  KeyRound,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { authClient } from "@/lib/auth/client";

/**
 * `key` は `common.nav.<key>` (Phase 3b / Issue #107)。文字列は catalog 側で
 * 一元管理し、本配列ではアイコンと href だけを定義する。
 */
interface NavItem {
  key: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
}

const navItems: NavItem[] = [
  { key: "dashboard", href: "/", icon: Home },
  { key: "tilesets", href: "/tilesets", icon: Layers },
  { key: "features", href: "/features", icon: Map },
  { key: "datasources", href: "/datasources", icon: Database },
  { key: "teams", href: "/teams", icon: Users },
  { key: "apiKeys", href: "/api-keys", icon: KeyRound },
];

const bottomNavItems: NavItem[] = [
  { key: "settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [isOpen, setIsOpen] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const t = useTranslations("common");

  const handleLogout = async () => {
    setIsLoggingOut(true);

    try {
      await authClient.logout();
      router.push("/login");
      router.refresh();
    } catch (error) {
      console.error("Logout error:", error);
      setIsLoggingOut(false);
    }
  };

  return (
    <>
      {/* モバイルメニューボタン */}
      <Button
        variant="ghost"
        size="icon"
        className="fixed left-4 top-4 z-50 md:hidden"
        onClick={() => setIsOpen(!isOpen)}
        aria-label={isOpen ? t("nav_mobile.close") : t("nav_mobile.open")}
      >
        {isOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </Button>

      {/* モバイルオーバーレイ */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* サイドバー */}
      <aside
        className={cn(
          "fixed left-0 top-0 z-40 h-screen w-64 border-r bg-card transition-transform md:translate-x-0",
          isOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex h-full flex-col">
          {/* ロゴ・ブランド */}
          <div className="flex h-16 items-center gap-2 border-b px-6">
            <Map className="h-6 w-6 text-primary" />
            <span className="text-lg font-bold">{t("app.brand")}</span>
          </div>

          {/* メインナビゲーション */}
          <nav className="flex-1 space-y-1 p-4">
            {navItems.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setIsOpen(false)}
                  className={cn(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                  )}
                >
                  <item.icon className="h-4 w-4" />
                  {t(`nav.${item.key}`)}
                </Link>
              );
            })}
          </nav>

          <Separator />

          {/* 下部ナビゲーション */}
          <div className="p-4">
            {bottomNavItems.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setIsOpen(false)}
                  className={cn(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                  )}
                >
                  <item.icon className="h-4 w-4" />
                  {t(`nav.${item.key}`)}
                </Link>
              );
            })}
            <button
              className="mt-2 flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground disabled:opacity-50"
              onClick={handleLogout}
              disabled={isLoggingOut}
              data-testid="sidebar-logout"
            >
              {isLoggingOut ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <LogOut className="h-4 w-4" />
              )}
              {isLoggingOut ? t("user.loggingOut") : t("user.logout")}
            </button>
          </div>

          {/* バージョン情報 */}
          <div className="border-t p-4">
            <p className="text-xs text-muted-foreground">{t("app.version")}</p>
          </div>
        </div>
      </aside>
    </>
  );
}
