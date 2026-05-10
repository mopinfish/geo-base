# E2E テスト（Playwright）

Issue #110 / [E2E 戦略 spec](../../../docs/superpowers/specs/2026-05-10-e2e-testing-design.md) / [Phase 1 plan](../../../docs/superpowers/plans/2026-05-10-e2e-phase1.md)

## ローカル実行手順

### 1. 専用 DB を用意する

#### Fresh volume の場合（推奨）

`docker/postgis-init/98_create_e2e_db.sh` が postgis 初回起動時に `geo_base_e2e` を自動作成するので、追加コマンドは不要:

```fish
docker compose -f docker/docker-compose.yml up -d
```

#### 既存 volume の場合（postgis を以前から動かしていた場合）

init script は新規 volume にしか流れないので、手動で作成する:

```fish
docker compose -f docker/docker-compose.yml exec postgis \
  psql -U postgres -c "CREATE DATABASE geo_base_e2e;"
docker compose -f docker/docker-compose.yml exec postgis bash -c \
  'pg_dump -U postgres --schema-only --no-owner --no-acl geo_base \
     | psql -U postgres -d geo_base_e2e'
```

#### Phase 2 で worker 並列を有効にする場合（既存 volume）

`E2E_WORKER_COUNT > 1` で動かしたい場合は、worker 別 DB を手動で作成する:

```fish
for i in 0 1 2 3
  docker compose -f docker/docker-compose.yml exec postgis \
    psql -U postgres -c "CREATE DATABASE geo_base_e2e_w$i;"
  docker compose -f docker/docker-compose.yml exec postgis bash -c \
    "pg_dump -U postgres --schema-only --no-owner --no-acl geo_base | psql -U postgres -d geo_base_e2e_w$i"
end
```

> 注: Phase 2 段階では Playwright 設定は `workers: 1` を維持しており、上記の worker DB は将来の並列化に備えた足場。実行時は `geo_base_e2e` (worker なし) のみ使用される。

> 注: ローカル環境で postgis のホストポートが 5432 でない場合は、以降の `DATABASE_URL` の port 部分を実際のポートに合わせること。

### 2. API を `E2E_MODE=1` で起動する

```fish
cd api
set -x DATABASE_URL postgresql://postgres:postgres@localhost:5432/geo_base_e2e
set -x JWT_SECRET test-secret-do-not-use-in-prod
set -x E2E_MODE 1
uv run uvicorn lib.main:app --port 8000
```

### 3. Next.js を production で起動する

別ターミナルで:

```fish
cd app
# NEXT_PUBLIC_API_URL は空のまま。ブラウザは /api/* を叩き、Next.js rewrites が
# API_BACKEND_URL を reverse proxy 先として使う（HttpOnly cookie の同一オリジン化）。
set -x API_BACKEND_URL http://localhost:8000
npm run build
npm run start -- --port 3000
```

### 4. smoke を流す

別ターミナルで:

```fish
cd app
npm run test:e2e:smoke
```

すべて緑になれば PASS。失敗は `npx playwright show-report` で詳細を確認する。

## ファイル構成

```
app/tests/e2e/
├── auth/                       # AUTH-* (unauthenticated project)
├── dashboard/                  # DASH-*
├── tilesets/                   # TS-*
├── features/                   # FT-*
├── datasources/                # DS-*
├── teams/                      # TM-*
├── api-keys/                   # AK-*
├── fixtures/
│   ├── api-client.ts           # session.ts の access_token を Bearer に乗せる request context
│   ├── authenticated-test.ts   # 認証必須テスト用の fixture (per-test loginAsAdmin + addCookies)
│   ├── factories.ts            # API 経由のシードファクトリ
│   └── sample.geojson
├── utils/
│   ├── reset-db.ts             # POST /api/test/reset 呼び出し（認証不要）
│   ├── session.ts              # loginAsAdmin / getAccessToken / getCookies
│   └── wait-for-server.ts
└── globalSetup.ts              # admin user の冪等作成のみ（ログインは各テストで都度実施）
```

## 新しいテストを書く

1. 該当する feature フォルダ（例: `tilesets/`）に `*.spec.ts` を作成。
2. テスト先頭で `await resetDatabase()` を呼ぶ。
3. 必要なら `factories.ts` の関数で前提データを作成。
4. 認証ありなら `playwright.config.ts` の `authenticated` project に自動マッチする（`auth/` 配下にだけ置かない）。
5. 各テストには `@smoke` タグを付ければ smoke run に含まれる。

## セレクタ規約

優先順位（i18n 対応のため）:

1. `getByRole(...)`
2. `getByLabel(...)`
3. `getByTestId('feature-element-role')` — 命名は `<feature>-<element>-<role>`
4. CSS セレクタは最終手段

テキスト一致 (`getByText`) は将来の英訳で破綻するので、極力使わない。

## トラブルシューティング

- **"Login failed: ..."**: `utils/session.ts` の `loginAsAdmin()` が API に届かない or 認証情報が不一致。Step 2 の API 起動と `globalSetup.ts` で作成された admin の email/password が一致しているか確認。
- **"Refusing to call /api/test/reset against non-local host"**: `PLAYWRIGHT_API_BASE_URL` が localhost / 127.0.0.1 でない。production を誤爆しないための安全装置。
- **"DATABASE_URL must point to a geo_base_e2e* database"**: API が `geo_base_e2e` 以外の DB に向いている。Step 2 の `DATABASE_URL` を確認。
- **"Not Found" (404) on /api/test/reset**: API が `E2E_MODE=1` 付きで起動されていない。Step 2 の env を確認。
- **"@playwright/test cannot find module ./tests/e2e/globalSetup.ts"**: `tests/e2e/globalSetup.ts` が無いか TypeScript エラー。`npx tsc --noEmit` で確認。
- **"No active session. Call loginAsAdmin() ..."**: factory 等が認証必須なのに loginAsAdmin が呼ばれていない。`fixtures/authenticated-test.ts` から `test, expect` を import するか、beforeAll で明示的に `loginAsAdmin()` を呼ぶ。
