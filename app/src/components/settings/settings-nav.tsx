"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { User, KeyRound } from "lucide-react";
import { cn } from "@/lib/utils";

export function SettingsNav() {
  const t = useTranslations("settings.nav");
  const pathname = usePathname();

  const items = [
    { href: "/settings/profile", label: t("profile"), icon: User },
    { href: "/settings/password", label: t("password"), icon: KeyRound },
  ];

  return (
    <nav className="flex gap-1 border-b">
      {items.map((item) => {
        const active = pathname === item.href;
        const Icon = item.icon;
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "flex items-center gap-2 border-b-2 px-4 py-2 text-sm font-medium transition-colors",
              active
                ? "border-primary text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground"
            )}
          >
            <Icon className="h-4 w-4" />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
