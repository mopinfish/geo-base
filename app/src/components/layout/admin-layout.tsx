"use client";

import { Sidebar } from "./sidebar";
import { useAuth } from "@/contexts/auth-context";
import { User } from "lucide-react";

interface AdminLayoutProps {
  children: React.ReactNode;
}

export function AdminLayout({ children }: AdminLayoutProps) {
  const { user, isLoading } = useAuth();

  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      <main className="md:pl-64">
        {/* ヘッダー */}
        <header className="sticky top-0 z-30 border-b bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/60">
          <div className="container mx-auto flex h-14 items-center justify-end px-6">
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
