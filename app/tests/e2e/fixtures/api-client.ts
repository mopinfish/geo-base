/**
 * 認証付き API クライアント。
 *
 * 認証フロー:
 * - `loginAsAdmin()` (utils/session.ts) が test の beforeAll/beforeEach で
 *   呼ばれ、その時に取得した access token を `getAccessToken()` で返す。
 * - 本モジュールはそれを `Authorization: Bearer <token>` ヘッダにセットして
 *   APIRequestContext を返す。
 *
 * 設計上の note:
 * - cookie + /api/auth/refresh を使うと **refresh token rotation** が起きて
 *   2 度目の利用で API 側に「reuse detected」と判定され全 token が revoke
 *   される。これを避けるため Bearer token を直接使う方式にしている。
 * - factory 関数は本 client を経由して Next.js (APP_BASE) に対して相対 URL を
 *   叩き、Next.js rewrites 経由で API に届く。同一オリジンを保つことで
 *   page tests と factory の両方で cookie / token の扱いが一致する。
 *
 * 利用例 (各 factory 関数の冒頭):
 *   const api = await createApiClient();
 *   const tileset = await api.post("/api/tilesets", { data: {...} });
 */
import { request, type APIRequestContext } from "@playwright/test";

import { getAccessToken } from "../utils/session";

const APP_BASE = process.env.PLAYWRIGHT_BASE_URL || "http://localhost:3000";

export async function createApiClient(): Promise<APIRequestContext> {
  const accessToken = getAccessToken();
  return request.newContext({
    baseURL: APP_BASE,
    extraHTTPHeaders: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
  });
}
