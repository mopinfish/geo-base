/**
 * Playwright globalSetup (Issue #110, Phase 1).
 *
 * 1. API と Next.js の起動を待つ
 * 2. `python -m lib.auth.cli create-admin --password ...` で admin を冪等作成
 * 3. POST /api/auth/login でトークンを取得
 * 4. storageState を `playwright/.auth/admin.json` に保存
 */
import { execSync } from "node:child_process";
import { mkdirSync } from "node:fs";
import path from "node:path";
import { request, type FullConfig } from "@playwright/test";

import { waitForServer } from "./utils/wait-for-server";

export const E2E_ADMIN_EMAIL = "e2e-admin@test.local";
export const E2E_ADMIN_PASSWORD = "E2E-pass-1!";
export const E2E_ADMIN_NAME = "E2E Admin";

const API_BASE = process.env.PLAYWRIGHT_API_BASE_URL || "http://localhost:8000";
const APP_BASE = process.env.PLAYWRIGHT_BASE_URL || "http://localhost:3000";
const AUTH_DIR = path.resolve(__dirname, "../../playwright/.auth");

async function ensureAdminUser(): Promise<void> {
  // CLI 経由で admin を冪等に作成する。既に存在するなら "already exists" 出力で
  // 終了コード 1 になるため、それは握りつぶす。失敗の本当のシグナルは
  // 直後のログイン試行で検出する。
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
    // 既存ユーザー時は exit 1 になる。ログインで本当に動くかを確認するのでここでは無視。
  }
}

async function loginAndSaveState(): Promise<void> {
  mkdirSync(AUTH_DIR, { recursive: true });

  const ctx = await request.newContext({ baseURL: APP_BASE });
  // Cookie を保持して /api/auth/login 経由でセッションを成立させる。
  // Next.js の rewrites を通して /api/auth/login が API に proxy される構成に依存。
  // ローカルの Next.js dev では `next.config.ts` で /api 配下を API_URL に rewrite している。
  const res = await ctx.post(`${API_BASE}/api/auth/login`, {
    data: { email: E2E_ADMIN_EMAIL, password: E2E_ADMIN_PASSWORD },
  });
  if (!res.ok()) {
    throw new Error(`Failed to login as ${E2E_ADMIN_EMAIL}: ${res.status()} ${await res.text()}`);
  }
  // refresh cookie がレスポンスに乗る。それを保存。
  await ctx.storageState({ path: path.join(AUTH_DIR, "admin.json") });
  await ctx.dispose();
}

export default async function globalSetup(_config: FullConfig): Promise<void> {
  await waitForServer(`${API_BASE}/api/health`);
  await waitForServer(APP_BASE);
  await ensureAdminUser();
  await loginAndSaveState();
}
