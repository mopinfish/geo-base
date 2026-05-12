import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

// next-intl の getRequestConfig を `src/i18n/request.ts` から読み込ませる
// (Phase 3 / Issue #107)。
const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

const nextConfig: NextConfig = {
  async rewrites() {
    // /api/* を FastAPI バックエンドへ reverse-proxy する。
    // 同一オリジン化により HttpOnly refresh cookie がブラウザに保存・送信される
    // （vercel.app と fly.dev は別 eTLD+1 のため直接 fetch では cookie が共有不可）。
    //
    // 解決の優先順位は API_BACKEND_URL > NEXT_PUBLIC_API_URL > localhost:8000:
    // - 本番 (Vercel production): API_BACKEND_URL を必須にして fail-fast
    // - dev / Vercel preview: 未設定なら localhost:8000 にフォールバック。
    //   NEXT_PUBLIC_API_URL は client.ts 側の fetch base にも使うため、dev で
    //   別 URL を当てたい場合の上書きとしても残してある。

    // Vercel **production** build で API_BACKEND_URL 未設定だと localhost に
    // rewrite されて静かに壊れる。preview build は localhost フォールバック
    // で build 自体は通すため、`VERCEL_ENV` で gate する。
    if (
      process.env.VERCEL_ENV === "production" &&
      !process.env.API_BACKEND_URL
    ) {
      throw new Error(
        "API_BACKEND_URL must be set for Vercel production builds. " +
          "Configure it in the project's Environment Variables " +
          "(e.g. https://geo-base-api.fly.dev).",
      );
    }

    // 末尾スラッシュは正規化（`https://example.com/` + `/api/...` で `//` に
    // ならないように）。
    const apiUrl = (
      process.env.API_BACKEND_URL ||
      process.env.NEXT_PUBLIC_API_URL ||
      "http://localhost:8000"
    ).replace(/\/+$/, "");
    return [
      { source: "/api/:path*", destination: `${apiUrl}/api/:path*` },
    ];
  },
};

export default withNextIntl(nextConfig);
