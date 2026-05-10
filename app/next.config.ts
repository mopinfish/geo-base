import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    // /api/* を FastAPI バックエンドへ reverse-proxy する。
    // 同一オリジン化により HttpOnly refresh cookie がブラウザに保存・送信される
    // （vercel.app と fly.dev は別 eTLD+1 のため直接 fetch では cookie が共有不可）。
    //
    // - 本番 (Vercel): API_BACKEND_URL を server-side env として設定
    // - dev: NEXT_PUBLIC_API_URL を流用、未設定なら localhost:8000
    const apiUrl =
      process.env.API_BACKEND_URL ||
      process.env.NEXT_PUBLIC_API_URL ||
      "http://localhost:8000";
    return [
      { source: "/api/:path*", destination: `${apiUrl}/api/:path*` },
    ];
  },
};

export default nextConfig;
