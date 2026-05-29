# E2E テスト拡充デザイン（Playwright + CI 組込み）

- **Date**: 2026-05-10
- **Status**: Approved (brainstorming completed)
- **Owner**: @OtsukaNoboru
- **Related Issues**: TBD（本ドキュメント承認後に Epic + 子 Issue を起票）

## 1. 背景

`geo-base` の Admin UI（`app/`）には現在、Vitest による単体テスト 1 ファイル（`app/src/lib/auth/proxy-decisions.test.ts`）しか存在しない。E2E テストはゼロ。`.github/workflows/` には `cleanup-expired.yml` のみで、テスト実行用の CI ワークフローも未整備。

今後の機能改修・i18n 対応・デザインシステム移行などを安全に進めるためには、主要ユーザーフローを自動検証する E2E テスト基盤が不可欠である。

## 2. ゴール

1. Admin UI の主要ユーザーフローを Playwright で E2E カバーする。
2. 認証・DB リセット・テストデータ生成を再利用可能なフィクスチャで提供し、新規テスト追加が容易な構造を作る。
3. CI を 3 段階で整備する: PR ごとの smoke、main マージ時 / nightly の full E2E。
4. リファクタリング・i18n 対応など今後の改修速度を上げる。

## 3. 現状把握

- **ルート総数**: 23（公開 4 + 認証必須 19）
- **機能領域**: 7 領域（Auth / Dashboard / Tilesets / Features / Datasources / Teams / API Keys / Settings）
- **既存テスト**: Vitest の `proxy-decisions.test.ts` 1 ファイルのみ
- **Playwright**: 未導入（`@playwright/test` なし、`playwright.config.*` なし）
- **CI**: `cleanup-expired.yml` のみ（テスト用 CI ワークフロー未整備）
- **認証**: アクセストークンはメモリ保持、リフレッシュトークンは HttpOnly Cookie。401 で自動リフレッシュ。
- **テストユーザー作成**: `python -m lib.auth.cli create-admin` で冪等に作成可能。

## 4. テスト範囲（Test Inventory）

E2E でカバーする全テストケース。カテゴリは smoke（PR で必ず実行）/ core（main・nightly で実行）/ edge（境界・エラー系）/ regression（過去バグ再発防止）。

### 4.1 Auth（公開ルート 4）

| ID | シナリオ | カテゴリ |
|---|---|---|
| AUTH-01 | 正しい認証情報でログイン → `/` にリダイレクト | smoke |
| AUTH-02 | 誤った認証情報 → エラーメッセージ表示、`/login` に留まる | core |
| AUTH-03 | `/login?next=/tilesets` ログイン後 → `/tilesets` にリダイレクト | core |
| AUTH-04 | ログアウト → `/login` 遷移、セッションクリア | smoke |
| AUTH-05 | 未認証で `/tilesets` 直接アクセス → `/login?next=/tilesets` | core |
| AUTH-06 | アクセストークン期限切れ → 自動リフレッシュで透明に継続 | edge |
| AUTH-07 | パスワードリセット申請 → 成功メッセージ | core |
| AUTH-08 | リセット token で新パスワード設定 → 新パスワードでログイン可 | core |
| AUTH-09 | 無効/期限切れ token でリセット試行 → エラー | edge |
| AUTH-10 | 招待 token で新規ユーザー登録 + 自動ログイン | core |
| AUTH-11 | 既存ユーザーの招待受諾フロー（`/login?next=...` 経由） | edge |
| AUTH-12 | 無効な招待 token → エラー | edge |

### 4.2 Dashboard

| ID | シナリオ | カテゴリ |
|---|---|---|
| DASH-01 | tilesets/features/datasources の件数が表示される | smoke |
| DASH-02 | 更新ボタンで再取得される | core |

### 4.3 Tilesets

| ID | シナリオ | カテゴリ |
|---|---|---|
| TS-01 | 一覧表示 | smoke |
| TS-02 | 名前検索でフィルタ | core |
| TS-03 | type フィルタ（vector/raster/pmtiles） | core |
| TS-04 | public/private フィルタ | core |
| TS-05 | 一括選択 + 一括削除（確認ダイアログ） | core |
| TS-06 | 新規作成フォームのバリデーション（name 必須） | core |
| TS-07 | 新規作成 → 詳細ページへ遷移 | smoke |
| TS-08 | 詳細ページにメタデータ + マッププレビュー表示 | core |
| TS-09 | 編集 → 保存 → 反映確認 | core |
| TS-10 | is_public トグル切替 | core |
| TS-11 | 単一削除（確認ダイアログ） | core |
| TS-12 | PMTiles 直接アップロード（Issue #101 Phase 3+4） | core |
| TS-13 | 自分の非公開 tileset が一覧に表示される（PR #103 リグレッション防止） | regression |

### 4.4 Features

| ID | シナリオ | カテゴリ |
|---|---|---|
| FT-01 | 一覧表示 | smoke |
| FT-02 | tileset でフィルタ | core |
| FT-03 | プロパティ検索 | core |
| FT-04 | limit セレクタ（10/50/100） | core |
| FT-05 | 一括選択 + 一括削除（dry_run なし） | core |
| FT-06 | 一括更新（layer / properties） | core |
| FT-07 | GeoJSON エクスポート（ダウンロードトリガ） | core |
| FT-08 | CSV エクスポート | core |
| FT-09 | Point geometry で新規作成 | core |
| FT-10 | Polygon geometry で新規作成 | core |
| FT-11 | プロパティ編集 | core |
| FT-12 | 詳細ページで地図に表示 | core |
| FT-13 | GeoJSON ファイル import（drag-drop） | smoke |
| FT-14 | 不正な GeoJSON → エラー | edge |

### 4.5 Datasources（Issue #101 関連）

| ID | シナリオ | カテゴリ |
|---|---|---|
| DS-01 | 一覧 + type フィルタ | smoke |
| DS-02 | include-private トグル | core |
| DS-03 | 一括削除 | core |
| DS-04 | public PMTiles URL で登録 | core |
| DS-05 | `s3://...` private URL で登録（Issue #101 Phase 1） | core |
| DS-06 | COG type で登録 | core |
| DS-07 | Test connection 成功 | core |
| DS-08 | Test connection 失敗 | edge |

### 4.6 Teams

| ID | シナリオ | カテゴリ |
|---|---|---|
| TM-01 | 自分のチーム一覧 | smoke |
| TM-02 | チーム作成（slug 自動生成） | core |
| TM-03 | チーム作成（slug 重複エラー） | edge |
| TM-04 | メンバー招待送信 | core |
| TM-05 | メンバー role 変更 | core |
| TM-06 | メンバー削除 | core |
| TM-07 | チーム削除 | core |
| TM-08 | 空状態の表示 | edge |

### 4.7 API Keys

| ID | シナリオ | カテゴリ |
|---|---|---|
| AK-01 | 一覧（マスク済み key 表示） | smoke |
| AK-02 | フルスコープで作成 | core |
| AK-03 | 限定スコープで作成 | core |
| AK-04 | 作成直後の key コピー（一度きりの可視化） | core |
| AK-05 | revoke（理由付き） | core |
| AK-06 | revoke 済み key の削除 | core |
| AK-07 | 期限切れ key のステータス表示 | edge |

### 4.8 Settings

| ID | シナリオ | カテゴリ |
|---|---|---|
| ST-01 | プロフィール名・email 更新 | core |
| ST-02 | パスワード変更（旧 + 新） | core |
| ST-03 | 旧パスワード誤り → エラー | edge |

### 4.9 集計

| カテゴリ | 件数 |
|---|---|
| smoke | 10 |
| core | 45 |
| edge | 15 |
| regression | 数件（蓄積していく） |
| **合計** | **約 75** |

## 5. アーキテクチャ

### 5.1 全体スタック

```
[Local / GitHub Actions runner]
  ├─ services: postgis (port 5432), redis (port 6379)
  │     ↑ GHA では native services ブロック、ローカルでは docker compose
  ├─ FastAPI (uvicorn, port 8000) — uv で起動、E2E_MODE=1
  ├─ Next.js (next start, port 3000) — production build 済み
  └─ Playwright runner (Chromium のみ)
        ├─ globalSetup: ユーザー作成 + login → storageState 保存
        ├─ tests/e2e/auth/*.spec.ts (storageState なし project)
        └─ tests/e2e/{tilesets,features,...}/*.spec.ts (storageState 有 project)
```

### 5.2 認証戦略（globalSetup + storageState）

- `app/tests/e2e/globalSetup.ts` で:
  1. `python -m lib.auth.cli create-admin --email e2e-admin@test.local --password 'E2E-pass-1!'`（冪等）
  2. POST `/api/auth/login` でアクセストークン取得
  3. `playwright/.auth/admin.json` に storageState 保存
- 役割別ユーザー（member / viewer）も同じ仕組みで作成可能な形に。
- `playwright.config.ts` の **2 project**:
  - `unauthenticated`: `tests/e2e/auth/**` 用、storageState なし
  - `authenticated`: `tests/e2e/!(auth)/**` 用、`storageState: 'playwright/.auth/admin.json'`

### 5.3 DB シーディング戦略

- 専用 DB: `geo_base_e2e`（pytest 用 `geo_base_test`、開発用 `geo_base` と完全分離）
- 各テストファイルの `beforeAll` で:
  1. SQL でユーザー以外の主要テーブル（tilesets, features, datasources, teams, team_members, team_invitations, api_keys, refresh_tokens 等）を truncate
  2. ファイル固有の前提データを **API 経由のファクトリ関数**でシード
- ファクトリ関数（`app/tests/e2e/fixtures/factories.ts`）:
  - `createTileset({ name, type, isPublic })` → POST `/api/tilesets/`
  - `createDatasource({ url, type })` → POST `/api/datasources/`
  - `createTeam({ name })` → POST `/api/teams/`
  - 戻り値はサーバが返した ID 付きエンティティ
- DB リセットは **API 側のテスト専用エンドポイント** `POST /api/test/reset`（環境変数 `E2E_MODE=1` のときだけルーター登録、本番では import すらされない）として実装。Playwright 側に SQL を散らさず、API レイヤーで境界を持たせる。
- Phase 1 はワーカー並列なし（`workers: 1`）。Phase 2 でワーカー別 DB（`geo_base_e2e_w1`, `geo_base_e2e_w2` 等）に拡張し `workers: 4` 化。

### 5.4 MapLibre GL の扱い

- ピクセル assertion はしない。
- 検証する: マップコンテナの DOM 存在、tile API（`/api/tiles/...` または `/api/tilesets/{id}/tilejson`）への network request 発生、console error なし。
- ビジュアル回帰は対象外（Phase 3 で再考）。

### 5.5 ブラウザマトリクス

- **Chromium のみ**。
- Firefox / WebKit は需要が出たら追加（Admin UI は Safari/Firefox 主要ターゲットでないため当面不要）。

### 5.6 テスト ID 規約

- 既存コードに `data-testid` がない箇所は Phase 1 で smoke 対象の要素にだけ追加。網羅的な追加はしない。
- 命名: `data-testid="<feature>-<element>-<role>"`（例: `tileset-list-row`、`login-submit`）。
- セレクタ優先順位: `getByRole` → `getByLabel` → `getByTestId` → CSS。テキスト依存セレクタを避けることで i18n 対応にも備える。

## 6. CI 設計

### 6.1 ワークフロー 3 種

- `.github/workflows/e2e-smoke.yml`
  - トリガ: `pull_request`、`paths: ['app/**', 'api/**', 'docker/postgis-init/**', '.github/workflows/e2e-*.yml']`
  - 範囲: smoke 10 件のみ
  - 必須化: required check
  - 想定時間: 4〜5 分

- `.github/workflows/e2e-full.yml`
  - トリガ: `push: branches: [main]`、`workflow_dispatch`
  - 範囲: 全 75 件、4 worker 並列
  - 必須化: required check（マージ後検証）
  - 想定時間: 8〜10 分

- `.github/workflows/e2e-nightly.yml`
  - トリガ: cron `0 18 * * *`（03:00 JST）、`workflow_dispatch`
  - 範囲: 全 75 件 + 失敗時通知
  - 想定時間: 10〜15 分（A11y チェック含む場合）

### 6.2 共通セットアップの抽出

3 ワークフロー間で重複する処理を `.github/actions/e2e-setup/action.yml`（composite action）に切り出す:
- Postgres / Redis service 設定
- uv setup + cache（api venv）
- node setup + cache（app node_modules）
- Playwright browsers cache（`actions/cache` で `~/.cache/ms-playwright`）
- Next.js build cache（`.next/cache`）
- DB マイグレーション適用 + テストユーザー作成

### 6.3 コスト試算（最適化後）

| ステップ | 時間 |
|---|---|
| services 起動（postgis + redis） | 20〜30s |
| uv sync（キャッシュ済み） | 15〜20s |
| npm ci（キャッシュ済み） | 5〜10s |
| Playwright browsers（キャッシュ済み） | 5〜10s |
| Next.js build（キャッシュ済み） | 10〜20s |
| API / Next.js 起動 | 10〜20s |
| **セットアップ合計** | **約 1.5〜2 分** |
| smoke 10 件実行 | 1〜2 分 |
| full 75 件実行（4 worker） | 3〜5 分 |

## 7. ファイルレイアウト

```
app/
  tests/
    e2e/
      auth/
        login.spec.ts
        password-reset.spec.ts
        invitation.spec.ts
      tilesets/
        list.spec.ts
        create.spec.ts
        edit.spec.ts
        delete.spec.ts
        upload-pmtiles.spec.ts
      features/
        list.spec.ts
        create.spec.ts
        export.spec.ts
        import.spec.ts
        bulk.spec.ts
      datasources/
        list.spec.ts
        create.spec.ts
        test-connection.spec.ts
      teams/
        ...
      api-keys/
        ...
      settings/
        ...
      fixtures/
        factories.ts        # API 経由のテストデータファクトリ
        api-client.ts       # 認証付き fetch ラッパー
      utils/
        reset-db.ts         # POST /api/test/reset 呼び出し
        wait-for-server.ts
      page-objects/         # 必要に応じて（initial は使わない）
      globalSetup.ts
  playwright.config.ts
api/
  lib/
    routers/
      test_helpers.py       # E2E_MODE=1 でのみ include される
.github/
  workflows/
    e2e-smoke.yml
    e2e-full.yml
    e2e-nightly.yml
  actions/
    e2e-setup/
      action.yml
```

## 8. フェーズ計画

### Phase 1: Foundation + Smoke

**スコープ**:
- Playwright 導入（`@playwright/test`）+ `playwright.config.ts`
- `globalSetup.ts` で認証 storageState 生成
- `POST /api/test/reset` エンドポイント（`E2E_MODE=1` ガード）
- `factories.ts` のシード関数（tilesets / datasources / teams / api-keys ぶんの最低限）
- smoke 10 件実装（AUTH-01/04、DASH-01、TS-01/07、FT-01/13、DS-01、TM-01、AK-01）
- `e2e-smoke.yml` ワークフロー
- 共通 composite action `e2e-setup`
- ローカル実行手順を `app/tests/e2e/README.md` に記載
- CONTRIBUTING への追記（テスト追加方法）

**完了の定義**:
- PR で smoke 10 件が CI 上 5 分以内にグリーン
- ローカルで `cd app && npm run test:e2e:smoke` が動く
- 新規テスト追加 PR が外部コントリビューターでも書ける

**見積もり**: 大型、1〜2 週間。

### Phase 2: Core coverage + Full CI

**スコープ**:
- core カテゴリ約 45 件を実装
- ワーカー並列対応: ワーカー別 DB（`geo_base_e2e_w1〜w4`）の自動セットアップ・リセット
- `playwright.config.ts` の `workers: 4`、`fullyParallel: true`
- `e2e-full.yml`（main マージ時）+ `e2e-nightly.yml`（cron）追加
- flaky 検出と隔離ルール（`test.fixme` + issue 自動起票）
- regression テストの追加運用ルール（PR #103 のような過去バグ起因のものを蓄積）

**完了の定義**:
- main マージ時に full E2E が 10 分以内に完了
- core カテゴリ網羅率 100%
- nightly が定期実行され失敗が可視化される

**見積もり**: 2〜4 週間。複数 PR に分割推奨。

### Phase 3: Edge + Regression + A11y

**スコープ**:
- edge カテゴリ約 15 件を実装
- `@axe-core/playwright` 試験導入（主要画面の A11y 自動チェック）
- ビジュアル回帰の必要性を再評価（必要なら `@playwright/test` の `toHaveScreenshot()` を限定導入）
- regression テストの蓄積（5 件以上を目標）

**完了の定義**:
- edge / regression が安定稼働
- nightly の flake 率 < 2%（直近 30 ラン中で 1 つ以下）
- A11y チェックが少なくとも login / tilesets-list / features-list で動作

**見積もり**: 1〜2 週間。

## 9. 非ゴール

- ビジュアル回帰テスト（Phase 3 で再検討）
- WebKit / Firefox サポート
- パフォーマンステスト・負荷テスト
- E2E カバレッジ計測ツールの導入
- API の独立 E2E（FastAPI 側は pytest で別途カバー）
- staging / production 環境への smoke（別途検討、本 Epic の範囲外）

## 10. リスクと緩和策

| リスク | 緩和策 |
|---|---|
| MapLibre GL の非決定性で flaky | ピクセル assertion 不採用。tile API への network request 発生のみ assert。`waitForResponse` で同期化。 |
| `POST /api/test/reset` が本番に漏れる | `E2E_MODE` 環境変数でルーター登録を分岐。本番デプロイの `fly.toml` に `E2E_MODE` 不在を CI でチェック。実装側で `assert os.getenv("E2E_MODE") == "1"` を二重ガード。 |
| CI コンテナ起動でフィードバック遅延 | キャッシュ徹底、Next.js は `next start`、4 worker 並列、smoke と full 分離。 |
| `geo_base_e2e` データが開発 DB と混じる | DB 名で完全分離、`reset-db.ts` 内で `DATABASE_URL` の DB 名チェックを必須化（`geo_base_e2e` で始まらないなら abort）。 |
| flaky テスト | CI のみ `retries: 2`、flaky と判定された test は `test.fixme` で隔離 + issue 自動起票。 |
| Phase 2 でのワーカー並列レース | ワーカー別 DB を `workerInfo.workerIndex` で割り当て。globalSetup でワーカー数ぶんの DB を作成・マイグレーション。 |
| テキストセレクタ依存で i18n PR で全テスト破綻 | `getByRole` / `getByLabel` / `getByTestId` 優先のセレクタ規約を強制。テキスト一致は最小限に。 |

## 11. 成功指標

- **Phase 1 完了**: PR で smoke 10 件が 5 分以内にグリーン。新規テスト追加が CONTRIBUTING に従って書ける。
- **Phase 2 完了**: main マージ時の full E2E が 10 分以内。core カテゴリ網羅率 100%。
- **Phase 3 完了**: nightly full の flake 率 < 2%（30 ラン中 1 件以下）。regression テスト 5 件以上。

## 12. 起票する Issue 構造

- **Epic**: `[Epic] E2E テスト拡充: Playwright で主要フローを自動検証 + CI 組込み`
  - 本ドキュメントへリンク、Phase 1〜3 のチェックリスト
- **Sub-issue 1**: Phase 1 — Foundation + smoke (10 cases) + PR CI
- **Sub-issue 2**: Phase 2 — Core coverage (~45 cases) + main/nightly full CI + parallel workers
- **Sub-issue 3**: Phase 3 — Edge + regression + A11y (~20 cases)

カスタムフィールドの設定:

| Issue | Status | Priority | Size |
|---|---|---|---|
| Epic | Backlog | P1 | XL |
| Phase 1 | Ready | P1 | M |
| Phase 2 | Backlog | P2 | L |
| Phase 3 | Backlog | P2 | M |

## 13. 参考

- Playwright 公式: https://playwright.dev/
- Playwright globalSetup と storageState: https://playwright.dev/docs/auth
- GitHub Actions services: https://docs.github.com/en/actions/using-containerized-services
- 関連スキル: `superpowers:brainstorming`、`superpowers:writing-plans`
