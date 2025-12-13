import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "geo-base Admin",
  description: "geo-base タイルサーバー管理画面",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ja">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
