/**
 * Playwright globalSetup (Issue #110, Phase 1).
 *
 * 1. API と Next.js の起動を待つ
 * 2. `python -m lib.auth.cli create-admin --password ...` で admin を冪等作成
 *
 * NOTE: 以前はここでログインして storageState を保存していたが、
 * refresh token rotation により同じ refresh token を 2 度使うと
 * 「reuse detected」で全 token が revoke される。このため:
 *
 *   - globalSetup ではログインしない（user 作成のみ）
 *   - 各テストファイルの beforeAll / beforeEach で `loginAsAdmin()` を
 *     呼んで、その時に発行された refresh token を `context.addCookies` で
 *     注入する形にしている (utils/session.ts を参照)。
 */
import { execSync } from "node:child_process";
import path from "node:path";
import type { FullConfig } from "@playwright/test";

import { waitForServer } from "./utils/wait-for-server";
import { E2E_ADMIN_EMAIL, E2E_ADMIN_PASSWORD } from "./utils/session";

// 既存テストとの互換性のため再 export する。
export {
  E2E_ADMIN_EMAIL,
  E2E_ADMIN_PASSWORD,
} from "./utils/session";
export const E2E_ADMIN_NAME = "E2E Admin";

const API_BASE = process.env.PLAYWRIGHT_API_BASE_URL || "http://localhost:8000";
const APP_BASE = process.env.PLAYWRIGHT_BASE_URL || "http://localhost:3000";

async function ensureAdminUser(): Promise<void> {
  // CLI 経由で admin を冪等に作成する。既に存在するなら "already exists" 出力で
  // 終了コード 1 になるため、それは握りつぶす。失敗の本当のシグナルは
  // 各テストの login 試行で検出する。
  const cmd = [
    "uv run python -m lib.auth.cli create-admin",
    `--email ${E2E_ADMIN_EMAIL}`,
    `--password '${E2E_ADMIN_PASSWORD}'`,
    `--name '${E2E_ADMIN_NAME}'`,
  ].join(" ");

  try {
    execSync(cmd, {
      cwd: path.resolve(__dirname, "../../../api"),
      stdio: "inherit",
      env: { ...process.env, PYTHONUNBUFFERED: "1" },
    });
  } catch {
    // 既存ユーザー時は exit 1 になる。各テストの login 試行で本当に動くかを
    // 検出するのでここでは無視。
  }
}

export default async function globalSetup(_config: FullConfig): Promise<void> {
  await waitForServer(`${API_BASE}/api/health`);
  await waitForServer(APP_BASE);
  await ensureAdminUser();
}
