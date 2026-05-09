"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { User, KeyRound } from "lucide-react";
import { cn } from "@/lib/utils";

const items = [
  { href: "/settings/profile", label: "プロフィール", icon: User },
  { href: "/settings/password", label: "パスワード", icon: KeyRound },
];

export function SettingsNav() {
  const pathname = usePathname();

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
