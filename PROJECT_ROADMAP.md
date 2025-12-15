# geo-base プロジェクトロードマップ

## 1. プロジェクト概要

### 1.1 プロジェクト名
**geo-base** - モノレポ構成の地理空間タイルサーバーシステム

### 1.2 目的
- 地理空間データ（ラスタ/ベクタタイル）を配信するタイルサーバーの構築
- LLM/AIクライアントからアクセス可能なMCPサーバーの提供
- タイルセット管理のための管理画面の実装

### 1.3 主要機能
1. **タイルサーバー**: ラスタ/ベクタタイルの配信API
2. **MCPサーバー**: Claude等のAIクライアント向けツール提供
3. **管理画面**: タイルセットのアップロード・管理・プレビュー

### 1.4 現在のステータス

| シーズン | ステータス | 期間 | 成果 |
|---------|-----------|------|------|
| ファーストシーズン | ✅ 完了 | 2024年 | 基本機能実装 |
| セカンドシーズン | ✅ 完了 | 2025年12月 | MCP拡充・UI改善 |

---

## 2. 技術スタック

### 2.1 バックエンド

| コンポーネント | 技術 | ホスティング | バージョン |
|--------------|------|-------------|-----------|
| タイルサーバー | Python FastAPI | Vercel Serverless Functions | 0.4.0 |
| MCPサーバー | Python FastMCP | Fly.io (Docker) / ローカル | 0.2.5 |
| データベース | PostgreSQL + PostGIS | Supabase | - |
| ストレージ | Blob Storage | Vercel Blob | - |

### 2.2 フロントエンド

| コンポーネント | 技術 | ホスティング | バージョン |
|--------------|------|-------------|-----------|
| 管理画面 | Next.js 16 + TypeScript | Vercel | 0.4.0 |
| 地図ライブラリ | MapLibre GL JS | - | - |
| 認証 | Supabase Auth | Supabase | - |
| UIライブラリ | shadcn/ui + Tailwind CSS v4 | - | - |

### 2.3 開発ツール

| 用途 | ツール |
|-----|-------|
| Pythonパッケージ管理 | uv |
| Node.jsパッケージ管理 | npm |
| コンテナ | Docker / Docker Compose |
| ローカルDB | Docker (PostGIS) |
| シェル | fish |

### 2.4 サポートフォーマット

**ラスタタイル:**
- GeoTIFF / Cloud Optimized GeoTIFF (COG)
- PNG / JPG

**ベクタタイル:**
- GeoJSON
- Mapbox Vector Tile (MVT / .pbf)
- PMTiles

---

## 3. システムアーキテクチャ

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              クライアント層                                    │
├─────────────────────┬─────────────────────┬─────────────────────────────────┤
│    地図ビューア       │     管理画面         │      LLM/AIクライアント          │
│  (MapLibre GL JS)   │   (Next.js)        │    (Claude Desktop等)           │
└─────────┬───────────┴─────────┬───────────┴──────────────┬──────────────────┘
          │                     │                          │
          │ タイルリクエスト       │ 管理API                   │ MCP Protocol
          ▼                     ▼                          ▼
┌─────────────────────────────────────────────┐  ┌────────────────────────────┐
│              Vercel Platform                 │  │       Fly.io               │
├─────────────────────────────────────────────┤  ├────────────────────────────┤
│  ┌─────────────────────────────────────┐    │  │  ┌──────────────────────┐  │
│  │     Tile Server API (FastAPI)       │    │  │  │   MCP Server         │  │
│  │     /api/tiles/{z}/{x}/{y}          │    │  │  │   (FastMCP)          │  │
│  │     /api/tilesets/...               │    │  │  │                      │  │
│  └─────────────────────────────────────┘    │  │  │  24 Tools:           │  │
│  ┌─────────────────────────────────────┐    │  │  │  - タイルセット管理    │  │
│  │     Admin Dashboard (Next.js)       │    │  │  │  - フィーチャー検索    │  │
│  │     /dashboard/...                  │    │  │  │  - 空間分析          │  │
│  │     /auth/...                       │    │  │  │  - 統計              │  │
│  └─────────────────────────────────────┘    │  │  └──────────────────────┘  │
└──────────────────────┬──────────────────────┘  └──────────────┬─────────────┘
                       │                                        │
                       │ DB接続                                  │ HTTP
                       ▼                                        ▼
          ┌────────────────────────────┐              Tile Server API
          │         Supabase           │                     
          ├────────────────────────────┤                     
          │  PostgreSQL + PostGIS      │                     
          │  - タイルセットメタデータ     │                     
          │  - ベクタフィーチャー        │                     
          │  - ユーザー情報            │                     
          ├────────────────────────────┤                     
          │      Supabase Auth         │                     
          │  - 認証・認可              │                     
          └────────────────────────────┘                     
```

---

## 4. 開発フェーズ進捗

### ファーストシーズン（完了）

#### フェーズ1: 基本的なタイル配信API ✅

| Step | 内容 | ステータス |
|------|------|-----------|
| 1.1 | プロジェクト初期設定 | ✅ 完了 |
| 1.2 | FastAPIタイルサーバー構築 | ✅ 完了 |
| 1.3 | 動的タイル生成（PostGIS ST_AsMVT） | ✅ 完了 |
| 1.4 | Vercelデプロイ | ✅ 完了 |

#### フェーズ2: MCPサーバー機能 ✅

| Step | 内容 | ステータス |
|------|------|-----------|
| 2.1 | FastMCPサーバー基盤 | ✅ 完了 |
| 2.2 | 基本ツール実装（16ツール） | ✅ 完了 |
| 2.3 | Fly.ioデプロイ | ✅ 完了 |

#### フェーズ3: 管理画面 ✅

| Step | 内容 | ステータス |
|------|------|-----------|
| 3.1 | Next.js基盤構築 | ✅ 完了 |
| 3.2 | 認証機能（Supabase Auth） | ✅ 完了 |
| 3.3 | データ管理機能 | ✅ 完了 |
| 3.4 | マッププレビュー | ✅ 完了 |

### セカンドシーズン（完了）

#### Phase 1: 基盤強化 ✅

| Step | 内容 | ステータス | 成果物 |
|------|------|-----------|--------|
| 2.5-A | ロギング基盤 | ✅ 完了 | `logger.py` |
| 2.5-B | エラーハンドリング・リトライ | ✅ 完了 | `errors.py`, `retry.py` |

#### Phase 2: 機能拡充 ✅

| Step | 内容 | ステータス | 成果物 |
|------|------|-----------|--------|
| 2.5-C | 統計ツール | ✅ 完了 | 4ツール追加 |
| 2.5-D | **空間分析ツール（最重要ゴール）** | ✅ 完了 | 4ツール追加 |

#### Phase 3: 品質向上 ✅

| Step | 内容 | ステータス | 成果物 |
|------|------|-----------|--------|
| 2.5-E | 入力バリデーション | ✅ 完了 | `validators.py` |
| 2.5-F | テスト拡充 | ✅ 完了 | カバレッジ85% |
| 2.5-G | バリデーション統合 | ✅ 完了 | 全ツール対応 |
| 2.5-H | テストバグ修正 | ✅ 完了 | - |

#### Phase 4: UI/UX改善 ✅

| Step | 内容 | ステータス | 成果物 |
|------|------|-----------|--------|
| 2.5-I | マッププレビュー全画面 | ✅ 完了 | 全画面モード |
| 2.5-J | レイヤー別スタイリング | ✅ 完了 | 10色パレット |
| 2.5-K | ポップアップ改善 | ✅ 完了 | 長文対応、URLリンク化 |
| 2.5-L | UI視認性改善 | ✅ 完了 | ボタン位置調整 |
| 2.5-M | TypeScriptビルドエラー修正 | ✅ 完了 | 型アサーション |

---

## 5. MCPツール一覧（24個）

### 5.1 タイルセット関連（3ツール）
- `tool_list_tilesets` - タイルセット一覧取得
- `tool_get_tileset` - タイルセット詳細取得
- `tool_get_tileset_tilejson` - TileJSON取得

### 5.2 フィーチャー関連（2ツール）
- `tool_search_features` - フィーチャー検索
- `tool_get_feature` - フィーチャー詳細取得

### 5.3 タイル関連（1ツール）
- `tool_get_tile_url` - タイルURL生成

### 5.4 ユーティリティ（2ツール）
- `tool_health_check` - ヘルスチェック
- `tool_get_server_info` - サーバー情報取得

### 5.5 ジオコーディング（2ツール）
- `tool_geocode` - 住所→座標変換
- `tool_reverse_geocode` - 座標→住所変換

### 5.6 CRUD操作（6ツール）
- `tool_create_tileset` - タイルセット作成
- `tool_update_tileset` - タイルセット更新
- `tool_delete_tileset` - タイルセット削除
- `tool_create_feature` - フィーチャー作成
- `tool_update_feature` - フィーチャー更新
- `tool_delete_feature` - フィーチャー削除

### 5.7 統計ツール（4ツール）🆕
- `tool_get_tileset_stats` - タイルセット統計
- `tool_get_feature_distribution` - ジオメトリ分布
- `tool_get_layer_stats` - レイヤー別統計
- `tool_get_area_stats` - エリア統計

### 5.8 空間分析ツール（4ツール）🆕
- `tool_analyze_area` - 包括的空間分析
- `tool_calculate_distance` - 距離計算
- `tool_find_nearest_features` - 近傍検索
- `tool_get_buffer_zone_features` - バッファゾーン分析

---

## 6. 今後の課題と改善点

### 6.1 既知の課題

| 課題 | 優先度 | 詳細 |
|------|--------|------|
| boundsの異常値 | 中 | 一部タイルセットで範囲が異常に広い |
| QGISとのTileJSON互換性 | 低 | `vector_layers[].id`とMVTレイヤー名の不一致（対応保留） |
| キャッシュ機能 | 低 | パフォーマンス改善のため未実装 |

### 6.2 将来の改善提案

**短期:**
- bounds計算の改善
- リトライ機能の全ツール統合

**中期:**
- タイルキャッシュ実装
- バルクインポート/エクスポート

**長期:**
- チーム/組織管理
- 使用量モニタリング
- APIキー管理

---

## 7. ローカル開発環境セットアップ

### 7.1 前提条件
- Python 3.11+
- Node.js 20+
- Docker & Docker Compose
- uv（Pythonパッケージマネージャー）
- fish シェル（推奨）

### 7.2 セットアップ手順

```fish
# リポジトリクローン
git clone https://github.com/mopinfish/geo-base.git
cd geo-base

# ローカルPostGIS起動
cd docker
docker compose up -d
cd ..

# APIサーバー
cd api
uv sync
uv run uvicorn lib.main:app --reload --port 8000
cd ..

# MCPサーバー
cd mcp
uv sync
uv run python server.py
cd ..

# 管理画面
cd app
npm install
npm run dev
cd ..
```

### 7.3 環境変数

**api/.env:**
```env
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=xxx
SUPABASE_SERVICE_ROLE_KEY=xxx
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres
```

**app/.env.local:**
```env
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=xxx
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**mcp/.env:**
```env
TILE_SERVER_URL=http://localhost:8000
API_TOKEN=xxxxx
LOG_LEVEL=INFO
```

---

## 8. デプロイ

### 8.1 Vercel（API + 管理画面）

```fish
vercel deploy --prod
```

### 8.2 Fly.io（MCPサーバー）

```fish
cd mcp
fly deploy
```

---

## 9. 関連ドキュメント

| ドキュメント | 説明 |
|-------------|------|
| `HANDOVER_S2_FINAL.md` | セカンドシーズン完了報告書 |
| `MCP_BEST_PRACTICES.md` | MCPサーバー開発のベストプラクティス |
| `MCP_PRESENTATION.md` | プレゼン用シナリオ |
| `TEST_PLAN.md` | テスト計画 |
| `QGIS_TILEJSON_ISSUE.md` | QGISとの互換性問題分析 |

---

## 更新履歴

| 日付 | 内容 |
|------|------|
| 2024-XX-XX | 初版作成 |
| 2025-12-14 | セカンドシーズン開始 |
| 2025-12-15 | **セカンドシーズン完了**、進捗更新 |
