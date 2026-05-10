/**
 * 認証付き API クライアント。
 *
 * 認証フロー:
 * 1. globalSetup が保存した storageState (refresh cookie) を使って
 *    POST /api/auth/refresh を叩き、新しい access token を取得する。
 * 2. その token を `Authorization: Bearer <token>` ヘッダにセットした
 *    APIRequestContext を返す。
 *
 * `require_auth_context` がかかっている API endpoint は cookie のみでは
 * 認証されず Bearer token が必須なので、このひと手間が要る。
 *
 * 各 factory 関数の冒頭で:
 *   const api = await createApiClient();
 *   const tileset = await api.post("/api/tilesets", ...);
 */
import path from "node:path";
import { request, type APIRequestContext } from "@playwright/test";

const API_BASE = process.env.PLAYWRIGHT_API_BASE_URL || "http://localhost:8000";
// __dirname は `app/tests/e2e/fixtures/` なので、3 つ上に上がると `app/`。
// そこから `playwright/.auth/admin.json` を探す。
const STORAGE_STATE = path.resolve(
  __dirname,
  "../../../playwright/.auth/admin.json",
);

interface RefreshResponse {
  access_token: string;
  refresh_token?: string;
  user?: unknown;
}

async function fetchAccessToken(): Promise<string> {
  const refreshCtx = await request.newContext({
    baseURL: API_BASE,
    storageState: STORAGE_STATE,
  });
  try {
    const res = await refreshCtx.post("/api/auth/refresh");
    if (!res.ok()) {
      throw new Error(
        `Failed to refresh access token: ${res.status()} ${await res.text()}`,
      );
    }
    const body = (await res.json()) as RefreshResponse;
    if (!body.access_token) {
      throw new Error("Refresh response missing access_token");
    }
    return body.access_token;
  } finally {
    await refreshCtx.dispose();
  }
}

export async function createApiClient(): Promise<APIRequestContext> {
  const accessToken = await fetchAccessToken();
  return request.newContext({
    baseURL: API_BASE,
    extraHTTPHeaders: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
  });
}
