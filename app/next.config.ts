import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    if (process.env.NODE_ENV === "development") {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      return [
        { source: "/api/:path*", destination: `${apiUrl}/api/:path*` },
      ];
    }
    return [];
  },
};

export default nextConfig;
