/**
 * 認証付き API クライアント。
 *
 * globalSetup で保存した storageState の cookie をそのまま `request` context に
 * 流し込んで使う。各テストファイルから:
 *
 *   const api = await createApiClient();
 *   const tileset = await api.createTileset({ name: "..." });
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

export async function createApiClient(): Promise<APIRequestContext> {
  return request.newContext({
    baseURL: API_BASE,
    storageState: STORAGE_STATE,
    extraHTTPHeaders: { "Content-Type": "application/json" },
  });
}
