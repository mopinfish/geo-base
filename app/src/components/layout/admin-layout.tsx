"use client";

import { Sidebar } from "./sidebar";

interface AdminLayoutProps {
  children: React.ReactNode;
}

export function AdminLayout({ children }: AdminLayoutProps) {
  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      <main className="md:pl-64">
        <div className="container mx-auto p-6 pt-20 md:pt-6">{children}</div>
      </main>
    </div>
  );
}
