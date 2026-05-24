# geo-base Season 3 引き継ぎドキュメント

**更新日**: 2026-05-24  
**プロジェクト**: geo-base - 地理空間タイルサーバーシステム  
**リポジトリ**: https://github.com/mopinfish/geo-base  
**現在のブランチ**: `develop`

---

## 1. 現在のシステム状況

### 1.1 デプロイ状況

| コンポーネント | ステータス | URL | バージョン |
|---------------|-----------|-----|-----------|
| API Server (Fly.io) | ✅ 稼働中 | https://geo-base-api.fly.dev | 0.4.4 |
| MCP Server (Fly.io) | ✅ 稼働中 | https://geo-base-mcp.fly.dev | 0.2.5 |
| Admin UI (Vercel) | ✅ 稼働中 | https://geo-base-admin.vercel.app | 0.5.0 |

> **Note**: Vercel版API（geo-base-puce.vercel.app）は廃止済み。すべてのコンポーネントがFly.io APIを参照。

### 1.2 Season 3 進捗サマリー

| フェーズ | ステップ | 内容 | ステータス |
|---------|---------|------|-----------|
| Phase 1 | Step 3.1-A | Fly.io移行準備（Dockerfile, fly.toml） | ✅ 完了 |
| Phase 1 | Step 3.1-B | API移行・動作確認 | ✅ 完了 |
| Phase 1 | Step 3.1-C | COGサポート | ✅ 完了 |
| Phase 1 | Step 3.1-D | ラスター分析 | ✅ 完了 |
| Phase 1 | Step 3.1-E | Admin UI更新 | ✅ 完了 |
| - | main.pyリファクタリング | 4,124行 → 150行にモジュール分割 | ✅ 完了 |
| **Phase 2** | **Step 3.2-A** | **バリデーション強化** | ✅ 完了 |
| **Phase 2** | **Step 3.2-B** | **リトライ機能統合** | ✅ 完了 |
| **Phase 2** | **Step 3.2-C** | **Redisキャッシュ導入** | ✅ 完了 |
| **Phase 2** | **Step 3.2-D** | **バッチ処理最適化 + 管理画面UI** | ✅ 完了 |
| **Phase 3** | **Step 3.3-A** | **チーム / ロール + プラガブル認証** | ✅ 完了（Backend + Admin UI） |
| **Epic #90** | **Phase 1** | **Admin UI デザインシステム移行: デザイントークン整備（#91〜#94）** | ✅ 完了（PR #154） |
| **Epic #90** | **Phase 2** | **Admin UI デザインシステム移行: コンポーネント再スタイル（#95〜#99）** | ✅ 完了（PR #155〜#159） |
| **Epic #90** | **Phase 3** | **Admin UI デザインシステム移行: a11y 監査 WCAG 2.1 AA（#100）** | ✅ 完了（PR #160、違反ゼロ） |

---

## 2. Phase 2 完了サマリー

### 2.1 テスト結果

```
153 passed in 0.68s
```

### 2.2 完了したステップ一覧

| ステップ | 内容 | テスト数 | 主要ファイル |
|---------|------|---------|-------------|
| Step 3.2-A | バリデーション強化 | 132 | `validators.py`, `fix_bounds.py` |
| Step 3.2-B | リトライ機能統合 | 80 | `retry.py`, `database.py` |
| Step 3.2-C | Redisキャッシュ導入 | 46 | `cache.py`, `tile_cache.py` |
| Step 3.2-D | バッチ処理最適化 | 27 | `batch.py`, `batch_features.py` |

---

## 3. 今回完了した作業: Step 3.2-D バッチ処理最適化 + 管理画面UI

### 3.1 概要

フィーチャーのバッチエクスポート、一括更新、一括削除機能をAPI・UIの両方で実装しました。

### 3.2 API実装

#### Step 3.2-D.1: バッチ処理モジュール

**新規ファイル**: `api/lib/batch.py` (~800行)

```
主要機能:
- BatchResult データクラス（success_count, failed_count, errors, duration等）
- BatchStatus enum（PENDING, IN_PROGRESS, COMPLETED, FAILED, CANCELLED）

エクスポート:
- export_features_geojson(): GeoJSONエクスポート（tileset_id または feature_ids指定）
- export_features_geojson_streaming(): ストリーミングエクスポート（大量データ対応）
- export_features_csv(): CSVエクスポート（WKT geometry、プロパティ列自動検出）

バッチ更新:
- batch_update_features(): ID指定での一括更新
- batch_update_by_filter(): フィルタ条件での一括更新

バッチ削除:
- batch_delete_features(): ID指定での一括削除
- batch_delete_by_filter(): フィルタ条件での一括削除（dry_run対応）
```

#### Step 3.2-D.2: エンドポイントルーター

**新規ファイル**: `api/lib/routers/batch_features.py` (~570行)

| メソッド | パス | 説明 |
|---------|------|------|
| POST | `/api/features/export` | フィーチャーエクスポート（GeoJSON/CSV） |
| GET | `/api/features/export/{tileset_id}` | シンプルエクスポート |
| GET | `/api/features/export/{tileset_id}/stream` | ストリーミングエクスポート |
| POST | `/api/features/bulk/update` | バッチ更新 |
| POST | `/api/features/bulk/delete` | バッチ削除 |
| DELETE | `/api/features/bulk` | シンプルバッチ削除 |

**主要モデル**:
- `ExportRequest`: tileset_id または feature_ids、format（geojson/csv）、フィルタオプション
- `BatchUpdateRequest`: feature_ids または filter、updates、merge_properties
- `BatchDeleteRequest`: feature_ids または filter、dry_run、limit

### 3.3 管理画面UI実装

#### フィーチャー一覧ページ (`app/src/app/features/page.tsx`)

**3つのエクスポート方法**:

| 場所 | 操作 | 対象 |
|------|------|------|
| ヘッダー | タイルセット選択 → 「エクスポート」ボタン | 選択タイルセットの全フィーチャー |
| 選択バー | フィーチャー選択 → 「選択をエクスポート」ボタン | 選択したフィーチャーのみ |
| タイルセット詳細 | ExportFeaturesButtonコンポーネント使用 | そのタイルセットの全フィーチャー |

**バッチ操作UI**:
- エクスポートダイアログ: GeoJSON/CSV形式選択
- バッチ更新ダイアログ: レイヤー名変更、プロパティ追加/マージ（JSON形式）
- バッチ削除ダイアログ: 削除プレビュー（dry_run）、確認ダイアログ

#### APIクライアント (`app/src/lib/api.ts`)

追加されたメソッド:
```typescript
exportFeatures(data: ExportRequest): Promise<ExportResult>
exportFeaturesCsv(data: ExportRequest): Promise<Blob>
batchUpdateFeatures(data: BatchUpdateRequest): Promise<BatchOperationResponse>
batchDeleteFeatures(data: BatchDeleteRequest): Promise<BatchOperationResponse>
```

#### 再利用可能コンポーネント

**新規ファイル**: `app/src/components/features/export-features-button.tsx`
- タイルセット詳細ページなどで使用可能
- GeoJSON/CSV形式選択ダイアログ内蔵

### 3.4 追加・更新ファイル一覧

```
api/
├── lib/
│   ├── batch.py                    # 新規 (800行) - バッチ処理モジュール
│   ├── main.py                     # 更新 (v0.4.4) - batch_featuresルーター追加
│   └── routers/
│       └── batch_features.py       # 新規 (570行) - バッチエンドポイント
└── tests/
    └── test_batch.py               # 新規 (520行) - 27テスト

app/src/
├── lib/
│   └── api.ts                      # 更新 - バッチ操作API追加
├── app/features/
│   └── page.tsx                    # 更新 (~1000行) - エクスポート/バッチ更新/バッチ削除UI
└── components/features/
    ├── export-features-button.tsx  # 新規 - エクスポートボタンコンポーネント
    └── index.ts                    # 更新 - エクスポート追加
```

---

## 4. API使用例

### エクスポート

```bash
# タイルセット全体をGeoJSONエクスポート
curl -X POST http://localhost:8000/api/features/export \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tileset_id": "uuid",
    "format": "geojson"
  }'

# 選択フィーチャーをCSVエクスポート
curl -X POST http://localhost:8000/api/features/export \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "feature_ids": ["uuid-1", "uuid-2", "uuid-3"],
    "format": "csv"
  }' \
  -o selected_features.csv
```

### バッチ更新

```bash
# ID指定で一括更新
curl -X POST http://localhost:8000/api/features/bulk/update \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "feature_ids": ["uuid-1", "uuid-2"],
    "updates": {"properties": {"status": "reviewed"}},
    "merge_properties": true
  }'
```

### バッチ削除

```bash
# ドライラン（プレビュー）
curl -X POST http://localhost:8000/api/features/bulk/delete \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "feature_ids": ["uuid-1", "uuid-2"],
    "dry_run": true
  }'

# 実際に削除
curl -X POST http://localhost:8000/api/features/bulk/delete \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "feature_ids": ["uuid-1", "uuid-2"]
  }'
```

---

## 5. 次のステップ: Phase 3 Step 3.3-A チームモデル設計

### 5.1 概要

エンタープライズ機能の基盤となるチーム/組織管理機能を設計・実装します。

### 5.2 タスク一覧

| タスク | 詳細 | 見積もり |
|--------|------|----------|
| データモデル設計 | teams, team_members, invitationsテーブル | 1日 |
| マイグレーション | Supabaseスキーマ作成 | 0.5日 |
| APIエンドポイント | チームCRUD、メンバー管理 | 1.5日 |
| 権限モデル | role-based access control設計 | 1日 |
| テスト | チーム機能テスト | 0.5日 |

### 5.3 予定されるテーブル構造

```sql
-- チーム
CREATE TABLE teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    owner_id UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- チームメンバー
CREATE TABLE team_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL DEFAULT 'member', -- owner, admin, member, viewer
    joined_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(team_id, user_id)
);

-- 招待
CREATE TABLE team_invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'member',
    invited_by UUID REFERENCES auth.users(id),
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    accepted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

---

## 6. 今後のロードマップ

### Phase 3: データ管理強化

| ステップ | 内容 | Issue | ステータス |
|---------|------|-------|-----------|
| Step 3.3-A | チーム / ロール + プラガブル認証 | — | ✅ 完了（Backend + Admin UI） |
| Step 3.3-B | APIキー管理 | — | ✅ 完了（Step 3.3-A に統合） |
| Step 3.3-C | Shapefile/GeoPackage インポート | #162 | 📋 起票済み |
| Step 3.3-D | タイルセット管理強化（クローン・マージ・差分） | #163 | 📋 起票済み |

### Phase 4: エンタープライズ機能

| ステップ | 内容 | Issue | ステータス |
|---------|------|-------|-----------|
| Step 3.4-B | RBAC — タイルセット単位アクセス制御 | #164 | 📋 起票済み |
| Step 3.4-D | 使用量モニタリング | #165 | 📋 起票済み |

### 横断課題

| 内容 | Issue | ステータス |
|------|-------|-----------|
| E2E テスト自動マイグレーション対応 | #166 | 📋 起票済み |

### Epic #90: Admin UI デジタル庁デザインシステム準拠（完了）

| フェーズ | 内容 | PR | ステータス |
|---------|------|-----|-----------|
| Phase 1: デザイントークン | カラーパレット・タイポグラフィ・シャドウ・フォーカスリングトークン整備（#91〜#94） | #154 | ✅ 完了 |
| Phase 2: コンポーネント再スタイル | Button/Input/Form/Select/Dialog/Table 他 shadcn/ui 全コンポーネント（#95〜#99） | #155〜#159 | ✅ 完了 |
| Phase 3: a11y 監査 | axe-core/playwright WCAG 2.1 AA スキャン 6 ページ、serious/critical 違反ゼロ（#100） | #160 | ✅ 完了 |

主な変更点:
- `globals.css`: `--destructive` トークン WCAG 1.4.3 修正（`84.2%` → `62.8%`）
- `button.tsx`: `isLoading` prop + `aria-busy`、Radix Slot クラッシュ修正
- `input.tsx` / `label.tsx` / `textarea.tsx`: `error`/`required` prop、`form.tsx` 新規追加
- `table.tsx`: `scope="col"` (WCAG 1.3.1)
- 全インタラクティブコンポーネント: フォーカスリング `ring-*` → `outline-*` 統一（WCAG 1.4.11）

> Step 3.3-A の詳細は以下を参照:
> - セットアップ: `docs/manuals/AUTH_SETUP.md`
> - 移行手順: `docs/manuals/AUTH_MIGRATION.md`
> - 手動 E2E チェック: `docs/refs/AUTH_E2E_CHECKLIST.md`
> - 認可仕様レビュー（2026-05-09 監査）: `docs/reports/ACCESS_CONTROL_REVIEW.md`
> - 設計書: `docs/specs/2026-05-08-pluggable-auth-design.md`

#### Step 3.3-A 完了サマリ（2026-05-08）

**Backend (Phase 0-5):**
- `api/lib/auth/` パッケージ化（provider ABC + LocalAuthProvider + SupabaseAuthProvider + factory）
- AuthContext / api_key_auth / check_tileset_access_v2 でアプリ層認可
- `/api/auth/*` 10 エンドポイント（login/refresh/logout/me/password-reset/invitation 等）
- TwoTierCORSMiddleware（`/api/auth/*` strict / その他 `*` 許容）
- CLI: `python -m lib.auth.cli {create-admin,revoke-token,cleanup-expired}`
- 起動時 fail-fast 設定検証

**Admin UI (Phase 6):**
- Supabase クライアント完全撤去（`@supabase/ssr`, `@supabase/supabase-js` 依存削除）
- `app/src/lib/auth/` の AuthClient + AuthProvider 抽象化
- 認証ページ 6 ページ新規（login, accept-invitation, password-reset/{request,confirm}, settings/{profile,password}）
- middleware は refresh cookie 存在で route guard
- `apiFetch` で 401 → refresh → retry 自動化

**ドキュメント (Phase 7):**
- `docs/manuals/AUTH_SETUP.md`（local モード セットアップ）
- `docs/manuals/AUTH_MIGRATION.md`（supabase → local 移行手順）

**テスト:**
- 479 passed, 2 skipped（auth 関連 130+ 直接テスト）
- auth モジュールカバレッジ: 70-100%（password/tokens/provider/context/errors/models = 100%）

**コミット規模:**
- Backend: 32 コミット（design docs `024a956` 〜 `13437fc`）
- Admin UI: 10 コミット（`c48a2f2` 〜 `fb40c83`）
- ドキュメント: 3 コミット（`e5f7799`, `b5152dd`, `49a47cb`）
- ブランチ: `feat/s3_3-3_team_and_role`

### Phase 4: エンタープライズ機能（3-4週間）

- Step 3.4-A: 権限管理（RBAC）
- Step 3.4-B: 使用量モニタリング
- Step 3.4-C: 監査ログ
- Step 3.4-D: SSOサポート

---

## 7. 技術メモ

### 7.1 テスト実行方法

```fish
cd api

# 全テスト実行
PYTHONPATH=. uv run pytest tests/ -v

# 特定テストファイル
PYTHONPATH=. uv run pytest tests/test_batch.py -v

# カバレッジ付き
PYTHONPATH=. uv run pytest tests/ --cov=lib --cov-report=term-missing
```

### 7.2 ローカル開発環境

```fish
# Docker環境起動
cd docker
docker compose up -d

# API起動
cd ../api
set -x DATABASE_URL "postgresql://postgres:postgres@localhost:5432/geo_base"
set -x REDIS_ENABLED true
set -x REDIS_HOST localhost
uv run uvicorn lib.main:app --reload --port 8000

# Admin UI起動
cd ../app
npm run dev
```

### 7.3 主要な設定ファイル

| ファイル | 説明 |
|---------|------|
| `api/lib/config.py` | API設定（DB接続、Redis、キャッシュ等） |
| `api/fly.toml` | Fly.ioデプロイ設定 |
| `app/.env.local` | Admin UI環境変数 |
| `docker/docker-compose.yml` | ローカル開発用Docker設定 |

---

## 8. デプロイ手順

### 8.1 Step 3.2-D の適用

```fish
cd /path/to/geo-base

# zipを解凍して上書き
unzip -o ~/Downloads/geo-base-step3.2-D-v3.zip -d .

# テスト実行確認
cd api
PYTHONPATH=. uv run pytest tests/ -v

# Admin UIビルド確認
cd ../app
npm run build

# コミット & プッシュ
cd ..
git add .
git commit -m "feat: Step 3.2-D - バッチ処理最適化 + 管理画面UI

API:
- api/lib/batch.py: BatchResult, エクスポート, バッチ更新/削除
- api/lib/routers/batch_features.py: REST APIエンドポイント
- api/lib/main.py: batch_featuresルーター追加 (v0.4.4)

Admin UI:
- app/src/lib/api.ts: バッチ操作API追加
- app/src/app/features/page.tsx: エクスポート/バッチ更新/バッチ削除UI
- app/src/components/features/export-features-button.tsx: エクスポートボタン

テスト: 27テスト追加（API総数153テスト）
Phase 2 完了"

git push origin develop

# Fly.ioデプロイ
cd api
fly deploy
```

---

## 9. 参考リソース

### プロジェクトドキュメント

| ファイル | 説明 |
|---------|------|
| `docs/plans/ROADMAP_S3.md` | Season 3 完全ロードマップ |
| `/mnt/project/HANDOVER_S3_STEP3.2-D.md` | Step 3.2-D 詳細引き継ぎ |
| `/mnt/project/HANDOVER_MAIN_REFACTORING.md` | main.pyリファクタリング完了ドキュメント |
| `/mnt/project/geo-base.txt` | 最新ソースコードスナップショット |
| `/mnt/project/MCP_BEST_PRACTICES.md` | MCPサーバー実装ベストプラクティス |

### 外部ドキュメント

- [Fly.io Documentation](https://fly.io/docs/)
- [Redis Documentation](https://redis.io/docs/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)

---

## 10. 次回作業の開始手順

```fish
# 1. リポジトリを最新に更新
cd /path/to/geo-base
git checkout develop
git pull origin develop

# 2. Phase 2完了の変更が適用されているか確認
ls -la api/lib/batch.py
ls -la api/lib/cache.py
ls -la api/lib/retry.py

# 3. テスト実行確認
cd api
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:15432/geo_base_test uv run pytest tests/ -q
# 期待: 653 passed, 2 skipped

# 4. 動作確認
curl https://geo-base-api.fly.dev/api/health

# 5. 次の Issue を選択して作業開始
# - Issue #162: Shapefile/GeoPackage インポート（推奨: ユーザー価値が高い）
# - Issue #163: タイルセット管理強化
# - Issue #166: E2E テスト自動マイグレーション（開発摩擦を早期解消）
```

---

## 11. 成果物まとめ

### Phase 2 完了時点のファイル構成（API側）

```
api/
├── lib/
│   ├── main.py              # エントリーポイント (v0.4.4)
│   ├── config.py            # 設定管理
│   ├── database.py          # DB接続（リトライ対応）
│   ├── auth.py              # 認証
│   ├── validators.py        # バリデーション (Step 3.2-A)
│   ├── retry.py             # リトライ機能 (Step 3.2-B)
│   ├── cache.py             # キャッシュ基盤 (Step 3.2-C)
│   ├── tile_cache.py        # タイルキャッシュ (Step 3.2-C)
│   ├── batch.py             # バッチ処理 (Step 3.2-D)
│   ├── models/
│   │   ├── __init__.py
│   │   ├── tileset.py
│   │   ├── feature.py
│   │   └── datasource.py
│   └── routers/
│       ├── __init__.py
│       ├── health.py
│       ├── tilesets.py
│       ├── features.py
│       ├── datasources.py
│       ├── tiles.py
│       └── batch_features.py # バッチエンドポイント (Step 3.2-D)
└── tests/
    ├── conftest.py
    ├── test_validators.py
    ├── test_tileset_models.py
    ├── test_fix_bounds.py
    ├── test_retry.py
    ├── test_tile_cache.py
    └── test_batch.py
```

### Phase 2 テスト統計

| テストファイル | テスト数 |
|---------------|---------|
| test_validators.py | 61 |
| test_tileset_models.py | 37 |
| test_fix_bounds.py | 34 |
| test_retry.py | 7 |
| test_tile_cache.py | 27 |
| test_batch.py | 27 |
| **合計** | **153** (+ 1 skipped) |

---

**作成者**: Claude (Anthropic)  
**Phase 2 完了日**: 2025-12-17  
**Epic #90 完了日**: 2026-05-24  
**次回作業候補**: Issue #162（Shapefile/GeoPackage インポート）・#163（タイルセット管理強化）・#166（E2E テスト自動マイグレーション）— 優先度は Issue コメントで判断
