# geo-base サードシーズン ロードマップ

## 📋 概要

**プロジェクト**: geo-base  
**シーズン**: サードシーズン（Season 3）  
**開始日**: 2025-12-15  
**ステータス**: 計画中

---

## 🎯 サードシーズンの目標

| 目標 | 説明 |
|------|------|
| 🚀 Fly.io移行 | API部分をVercelからFly.ioに移行し、GDAL等のネイティブ依存を解消 |
| 🖼️ ラスター機能 | Cloud Optimized GeoTIFF対応、動的ラスタタイル生成 |
| 📊 データ品質 | bounds/center計算の改善、データ検証機能 |
| ⚡ パフォーマンス | キャッシュ、バッチ処理、クエリ最適化 |
| 📦 データ管理 | バルクインポート/エクスポート、履歴管理 |
| 🏢 エンタープライズ | チーム管理、APIキー、使用量モニタリング |

---

## 🏗️ アーキテクチャ変更

### 現在のアーキテクチャ（セカンドシーズン完了時点）

```
┌─────────────────────────────────────────────────────────────────┐
│                         クライアント層                            │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   地図ビューア    │     管理画面     │      LLM/AIクライアント      │
│ (MapLibre GL JS) │   (Next.js)     │    (Claude Desktop等)       │
└────────┬────────┴────────┬────────┴─────────────┬───────────────┘
         │                 │                      │
         ▼                 ▼                      ▼
┌────────────────────────────────┐    ┌────────────────────────────┐
│       Vercel Platform          │    │         Fly.io             │
├────────────────────────────────┤    ├────────────────────────────┤
│  Tile Server API (FastAPI)     │    │  MCP Server (FastMCP)      │
│  Admin Dashboard (Next.js)     │    │  24 Tools                  │
└────────────────┬───────────────┘    └─────────────┬──────────────┘
                 │                                  │
                 └──────────────┬───────────────────┘
                                ▼
                   ┌────────────────────────────┐
                   │         Supabase           │
                   │  PostgreSQL + PostGIS      │
                   │  Supabase Auth             │
                   └────────────────────────────┘
```

### 新アーキテクチャ（サードシーズン完了後）

```
┌─────────────────────────────────────────────────────────────────┐
│                         クライアント層                            │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   地図ビューア    │     管理画面     │      LLM/AIクライアント      │
│ (MapLibre GL JS) │   (Next.js)     │    (Claude Desktop等)       │
└────────┬────────┴────────┬────────┴─────────────┬───────────────┘
         │                 │                      │
         ▼                 ▼                      ▼
┌────────────────────┐  ┌────────────────────────────────────────┐
│  Vercel Platform   │  │              Fly.io                    │
├────────────────────┤  ├────────────────────────────────────────┤
│  Admin Dashboard   │  │  ┌──────────────────────────────────┐  │
│  (Next.js)         │  │  │  Tile Server API (FastAPI)       │  │
│                    │  │  │  - Vector Tiles (MVT)            │  │
│                    │  │  │  - Raster Tiles (COG/GeoTIFF)    │  │
│                    │  │  │  - GDAL/rasterio対応             │  │
│                    │  │  └──────────────────────────────────┘  │
│                    │  │  ┌──────────────────────────────────┐  │
│                    │  │  │  MCP Server (FastMCP)            │  │
│                    │  │  │  24+ Tools                       │  │
│                    │  │  └──────────────────────────────────┘  │
│                    │  │  ┌──────────────────────────────────┐  │
│                    │  │  │  Redis (Upstash/Fly Redis)       │  │
│                    │  │  │  キャッシュ層                      │  │
│                    │  │  └──────────────────────────────────┘  │
└────────────────────┘  └────────────────────────────────────────┘
                                        │
                                        ▼
                          ┌────────────────────────────┐
                          │         Supabase           │
                          │  PostgreSQL + PostGIS      │
                          │  Supabase Auth             │
                          │  Supabase Storage          │
                          └────────────────────────────┘
```

---

## 📅 開発フェーズ

### Phase 1: Fly.io移行 & ラスター機能拡張（3-4週間）

API部分をVercelからFly.ioに移行し、GDAL依存のラスター機能を実装します。

#### Step 3.1-A: Fly.io移行準備

| タスク | 詳細 | 見積もり |
|--------|------|----------|
| Dockerfile作成 | Python 3.11 + GDAL + rasterio環境構築 | 1日 |
| fly.toml設定 | APIサーバー用の設定ファイル | 0.5日 |
| 環境変数移行 | Vercel → Fly.io環境変数設定 | 0.5日 |
| ヘルスチェック | /health エンドポイント確認 | 0.5日 |

**成果物**:
- `api/Dockerfile`
- `api/fly.toml`
- Fly.ioへのデプロイ成功

#### Step 3.1-B: API移行・動作確認

| タスク | 詳細 | 見積もり |
|--------|------|----------|
| 既存エンドポイント移行 | 全APIエンドポイントの動作確認 | 1日 |
| DB接続確認 | Supabase接続の安定性確認 | 0.5日 |
| パフォーマンステスト | レスポンス時間の計測・比較 | 0.5日 |
| SSL/TLS設定 | カスタムドメイン設定（オプション） | 0.5日 |

**成果物**:
- Fly.ioで稼働するAPI (`geo-base-api.fly.dev`)
- 移行レポート

#### Step 3.1-C: COG（Cloud Optimized GeoTIFF）対応

| タスク | 詳細 | 見積もり |
|--------|------|----------|
| rio-tiler導入 | pyproject.tomlへの追加 | 0.5日 |
| COGアップロード | Supabase Storageへの保存 | 1日 |
| タイル生成API | `/api/tiles/{id}/{z}/{x}/{y}.png` | 2日 |
| TileJSON生成 | ラスター用TileJSON対応 | 1日 |

**成果物**:
- COGファイルのアップロード機能
- 動的ラスタータイル生成API

#### Step 3.1-D: ラスター分析機能

| タスク | 詳細 | 見積もり |
|--------|------|----------|
| バンド演算 | NDVI、NDWI等の指数計算 | 2日 |
| 統計情報取得 | 範囲内のピクセル統計 | 1日 |
| カラーマップ | 複数のカラーマップ対応 | 1日 |
| MCPツール追加 | ラスター分析用ツール | 1日 |

**成果物**:
- `tool_analyze_raster` - ラスター統計分析
- `tool_calculate_index` - 植生指数等の計算
- ラスター演算API

#### Step 3.1-E: 管理画面対応

| タスク | 詳細 | 見積もり |
|--------|------|----------|
| ラスタープレビュー | MapLibreでのラスター表示 | 1日 |
| アップロードUI | COGファイルのドラッグ&ドロップ | 1日 |
| バンド選択UI | 表示バンドの選択機能 | 0.5日 |
| カラーマップ選択 | プリセットカラーマップ | 0.5日 |

**成果物**:
- ラスター対応の管理画面

---

### Phase 2: データ品質 & パフォーマンス最適化（2-3週間）

#### Step 3.2-A: bounds/center計算の改善

| タスク | 詳細 | 見積もり |
|--------|------|----------|
| bounds計算修正 | GeoJSONインポート時の正確な計算 | 1日 |
| center計算改善 | 重心計算の精度向上 | 0.5日 |
| 既存データ修正 | マイグレーションスクリプト | 0.5日 |
| バリデーション強化 | インポート前の検証 | 1日 |

**成果物**:
- 正確なbounds/center計算ロジック
- データ修正マイグレーション

#### Step 3.2-B: リトライ機能の完全統合

| タスク | 詳細 | 見積もり |
|--------|------|----------|
| tilesets.py統合 | retry.pyの関数を適用 | 0.5日 |
| features.py統合 | retry.pyの関数を適用 | 0.5日 |
| API層リトライ | FastAPIレベルでのリトライ | 1日 |
| テスト追加 | リトライシナリオのテスト | 0.5日 |

**成果物**:
- 全ツールへのリトライ機能統合

#### Step 3.2-C: キャッシュ実装

| タスク | 詳細 | 見積もり |
|--------|------|----------|
| Redis/Upstash設定 | Fly.ioでのRedis設定 | 0.5日 |
| タイルキャッシュ | MVT/ラスタータイルのキャッシュ | 1.5日 |
| TileJSONキャッシュ | メタデータのキャッシュ | 0.5日 |
| キャッシュ無効化 | データ更新時の自動クリア | 1日 |

**成果物**:
- Redisベースのキャッシュ層
- キャッシュヒット率モニタリング

#### Step 3.2-D: バッチ処理対応

| タスク | 詳細 | 見積もり |
|--------|------|----------|
| 一括作成API | POST `/api/features/bulk` | 1日 |
| 一括更新API | PATCH `/api/features/bulk` | 1日 |
| 一括削除API | DELETE `/api/features/bulk` | 0.5日 |
| MCPツール追加 | バッチ操作用ツール | 1日 |

**成果物**:
- `tool_bulk_create_features`
- `tool_bulk_update_features`
- `tool_bulk_delete_features`

#### Step 3.2-E: クエリ最適化

| タスク | 詳細 | 見積もり |
|--------|------|----------|
| インデックス最適化 | PostGISインデックスの見直し | 0.5日 |
| クエリ分析 | EXPLAIN ANALYZEによる分析 | 0.5日 |
| 空間インデックス | GiSTインデックスの追加・調整 | 0.5日 |
| ベンチマーク | パフォーマンス計測・レポート | 0.5日 |

**成果物**:
- 最適化されたDBスキーマ
- パフォーマンスベンチマークレポート

---

### Phase 3: データ管理強化（2-3週間）

#### Step 3.3-A: バルクインポート

| タスク | 詳細 | 見積もり |
|--------|------|----------|
| Shapefile対応 | .shp/.shx/.dbfファイル読み込み | 2日 |
| GeoPackage対応 | .gpkgファイル読み込み | 1日 |
| CSV対応 | 座標カラム付きCSV読み込み | 1日 |
| インポートUI | 進捗表示、エラーハンドリング | 1日 |

**成果物**:
- 複数フォーマット対応のインポート機能

#### Step 3.3-B: エクスポート機能

| タスク | 詳細 | 見積もり |
|--------|------|----------|
| GeoJSONエクスポート | フィーチャーのGeoJSON出力 | 0.5日 |
| CSVエクスポート | 属性データのCSV出力 | 0.5日 |
| Shapefileエクスポート | .shp形式での出力 | 1日 |
| エクスポートUI | フォーマット選択、ダウンロード | 1日 |

**成果物**:
- 複数フォーマット対応のエクスポート機能
- `tool_export_features` MCPツール

#### Step 3.3-C: タイルセット管理強化

| タスク | 詳細 | 見積もり |
|--------|------|----------|
| クローン機能 | タイルセットの複製 | 1日 |
| マージ機能 | 複数タイルセットの統合 | 1日 |
| 差分比較 | 2つのタイルセットの差分表示 | 1日 |

**成果物**:
- タイルセット操作の拡張機能

#### Step 3.3-D: 履歴・バージョン管理

| タスク | 詳細 | 見積もり |
|--------|------|----------|
| 変更履歴テーブル | feature_historyテーブル作成 | 1日 |
| 変更トラッキング | INSERT/UPDATE/DELETEの記録 | 1日 |
| 履歴表示UI | 変更履歴の一覧・詳細表示 | 1日 |
| ロールバック | 過去バージョンへの復元 | 1日 |

**成果物**:
- フィーチャー変更履歴機能

---

### Phase 4: エンタープライズ機能（3-4週間）

#### Step 3.4-A: チーム/組織管理

| タスク | 詳細 | 見積もり |
|--------|------|----------|
| organizationsテーブル | 組織データモデル設計 | 1日 |
| team_membersテーブル | メンバーシップ管理 | 1日 |
| 招待機能 | メール招待、承認フロー | 2日 |
| 組織切替UI | ワークスペース切替機能 | 1日 |

**成果物**:
- マルチテナント対応の組織管理

#### Step 3.4-B: 権限管理

| タスク | 詳細 | 見積もり |
|--------|------|----------|
| ロール定義 | Owner/Admin/Editor/Viewer | 1日 |
| タイルセット権限 | 個別アクセス権設定 | 1日 |
| RLS設定 | Supabase Row Level Security | 1日 |
| 権限UI | 権限設定画面 | 1日 |

**成果物**:
- ロールベースのアクセス制御

#### Step 3.4-C: APIキー管理

| タスク | 詳細 | 見積もり |
|--------|------|----------|
| api_keysテーブル | APIキーデータモデル | 0.5日 |
| キー生成・失効 | 発行・無効化機能 | 1日 |
| レート制限 | キー別のレート制限 | 1日 |
| APIキーUI | 管理画面でのキー管理 | 1日 |

**成果物**:
- 外部システム連携用APIキー機能

#### Step 3.4-D: 使用量モニタリング

| タスク | 詳細 | 見積もり |
|--------|------|----------|
| usage_logsテーブル | リクエストログ設計 | 1日 |
| リクエスト記録 | APIリクエストのロギング | 1日 |
| 集計・可視化 | 日別/月別の使用量グラフ | 2日 |
| アラート設定 | 閾値超過時の通知 | 1日 |

**成果物**:
- 使用量ダッシュボード
- 使用量アラート機能

---

## 📊 マイルストーン

| マイルストーン | 目標日 | 成果物 |
|--------------|--------|--------|
| M1: Fly.io移行完了 | Week 1 | APIがFly.ioで稼働 |
| M2: ラスター基本機能 | Week 2-3 | COG対応、動的タイル生成 |
| M3: ラスター分析機能 | Week 4 | NDVI計算、MCPツール |
| M4: データ品質改善 | Week 5-6 | bounds修正、リトライ統合 |
| M5: キャッシュ・バッチ | Week 7 | Redis導入、一括操作 |
| M6: インポート/エクスポート | Week 8-9 | 複数フォーマット対応 |
| M7: 履歴管理 | Week 10 | 変更履歴、ロールバック |
| M8: チーム管理 | Week 11-12 | 組織、権限管理 |
| M9: APIキー・モニタリング | Week 13-14 | APIキー、使用量追跡 |

---

## 🔧 技術仕様

### 新規依存パッケージ（API）

```toml
# api/pyproject.toml への追加
[project.dependencies]
# ラスター処理
rasterio = "^1.3.0"
rio-tiler = "^6.0.0"
rio-cogeo = "^5.0.0"

# キャッシュ
redis = "^5.0.0"

# ファイル形式
fiona = "^1.9.0"  # Shapefile/GeoPackage
pyproj = "^3.6.0"
```

### 新規Dockerfile（API）

```dockerfile
# api/Dockerfile
FROM ghcr.io/osgeo/gdal:ubuntu-small-3.8.0

WORKDIR /app

# Python環境
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# uv インストール
RUN pip install uv

# 依存関係
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

# アプリケーション
COPY . .

EXPOSE 8080

CMD ["uv", "run", "uvicorn", "lib.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### 新規データベーステーブル

```sql
-- 組織管理
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- チームメンバー
CREATE TABLE team_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL DEFAULT 'viewer',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (organization_id, user_id)
);

-- APIキー
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(64) NOT NULL,
    prefix VARCHAR(8) NOT NULL,
    scopes TEXT[] DEFAULT '{}',
    rate_limit INTEGER DEFAULT 1000,
    expires_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    revoked_at TIMESTAMPTZ
);

-- 使用量ログ
CREATE TABLE usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    api_key_id UUID REFERENCES api_keys(id),
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    status_code INTEGER,
    response_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- フィーチャー変更履歴
CREATE TABLE feature_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    feature_id UUID NOT NULL,
    tileset_id UUID REFERENCES tilesets(id) ON DELETE CASCADE,
    operation VARCHAR(20) NOT NULL, -- 'create', 'update', 'delete'
    old_data JSONB,
    new_data JSONB,
    user_id UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- インデックス
CREATE INDEX usage_logs_org_created_idx ON usage_logs (organization_id, created_at);
CREATE INDEX usage_logs_api_key_idx ON usage_logs (api_key_id, created_at);
CREATE INDEX feature_history_feature_idx ON feature_history (feature_id, created_at);
```

---

## 📁 ディレクトリ構成（サードシーズン完了後）

```
geo-base/
├── api/                         # FastAPI タイルサーバー (Fly.io)
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── Dockerfile              # 🆕 Fly.io用
│   ├── fly.toml                # 🆕 Fly.io設定
│   │
│   ├── lib/
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── storage.py
│   │   ├── tiles.py
│   │   ├── raster.py           # 🆕 ラスター処理
│   │   ├── cache.py            # 🆕 キャッシュ層
│   │   ├── auth.py
│   │   ├── api_keys.py         # 🆕 APIキー認証
│   │   └── usage.py            # 🆕 使用量ロギング
│   │
│   └── tests/
│
├── app/                         # Next.js 管理画面 (Vercel)
│   ├── src/
│   │   ├── app/
│   │   │   ├── dashboard/
│   │   │   │   ├── tilesets/
│   │   │   │   ├── features/
│   │   │   │   ├── import/     # 🆕 インポート
│   │   │   │   ├── export/     # 🆕 エクスポート
│   │   │   │   ├── history/    # 🆕 履歴
│   │   │   │   ├── team/       # 🆕 チーム管理
│   │   │   │   ├── api-keys/   # 🆕 APIキー管理
│   │   │   │   └── usage/      # 🆕 使用量
│   │   │   └── ...
│   │   └── ...
│   └── ...
│
├── mcp/                         # MCP Server (Fly.io)
│   ├── tools/
│   │   ├── tilesets.py
│   │   ├── features.py
│   │   ├── geocoding.py
│   │   ├── crud.py
│   │   ├── stats.py
│   │   ├── analysis.py
│   │   ├── raster.py           # 🆕 ラスター分析
│   │   ├── bulk.py             # 🆕 バッチ操作
│   │   └── export.py           # 🆕 エクスポート
│   └── ...
│
└── ...
```

---

## 🧪 テスト計画

### Phase 1 テスト

| カテゴリ | テスト内容 |
|---------|----------|
| 移行テスト | 既存APIエンドポイントの完全動作確認 |
| ラスターテスト | COGアップロード、タイル生成、バンド演算 |
| 統合テスト | MCP → API → DB の一気通貫テスト |

### Phase 2 テスト

| カテゴリ | テスト内容 |
|---------|----------|
| 品質テスト | bounds/center計算の精度検証 |
| キャッシュテスト | ヒット率、無効化タイミング |
| バッチテスト | 大量データの一括処理性能 |

### Phase 3-4 テスト

| カテゴリ | テスト内容 |
|---------|----------|
| インポートテスト | 各フォーマットの読み込み精度 |
| 権限テスト | RLSポリシーの検証 |
| 負荷テスト | 複数組織同時アクセス |

---

## 📈 成功指標

| 指標 | 目標値 |
|------|--------|
| APIレスポンス時間 | < 100ms (キャッシュヒット時) |
| タイルキャッシュヒット率 | > 80% |
| テストカバレッジ | > 85% 維持 |
| MCPツール数 | 30+ |
| 対応フォーマット | ベクター4種 + ラスター3種 |

---

## 🔄 リスクと対策

| リスク | 影響 | 対策 |
|--------|------|------|
| Fly.io移行でのパフォーマンス低下 | 中 | ベンチマーク比較、必要に応じてスケールアップ |
| GDAL依存によるビルド時間増加 | 低 | マルチステージビルド、キャッシュ活用 |
| キャッシュ整合性問題 | 中 | TTL設定、明示的無効化API |
| 大規模インポートのタイムアウト | 中 | バックグラウンドジョブ化 |

---

## 📚 参考資料

- [Fly.io Documentation](https://fly.io/docs/)
- [rio-tiler Documentation](https://cogeotiff.github.io/rio-tiler/)
- [GDAL Docker Images](https://github.com/OSGeo/gdal/tree/master/docker)
- [Supabase Row Level Security](https://supabase.com/docs/guides/auth/row-level-security)
- [Redis Caching Patterns](https://redis.io/docs/manual/patterns/)

---

## 更新履歴

| 日付 | 内容 | 担当 |
|------|------|------|
| 2025-12-15 | サードシーズンロードマップ作成 | Claude |
