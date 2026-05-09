# geo-base API

FastAPI タイルサーバー - ベクター/ラスター地理データ配信API

## 概要

geo-base APIは、PostGISデータベースからベクタータイル（MVT）を動的に生成し、PMTilesやCloud Optimized GeoTIFF（COG）形式のラスターデータも配信できる地理空間タイルサーバーです。

## 機能

- **ベクタータイル**: PostGIS ST_AsMVTによる動的MVT生成
- **PMTiles**: クラウドネイティブなベクタータイル形式のサポート
- **ラスタータイル**: rio-tilerによるCOGタイル生成（Fly.io環境）
- **認証**: プラガブル認証（`AUTH_PROVIDER=local|supabase` で切替）+ API キー（詳細は [`docs/AUTH_SETUP.md`](../docs/AUTH_SETUP.md)）
- **チーム / ロール**: チームベースのタイルセット共有（Phase 3 / Step 3.3-A）
- **CRUD API**: タイルセット・フィーチャー管理

## プロジェクト構造

```
api/
├── lib/
│   ├── main.py              # アプリケーションエントリポイント
│   ├── models/              # Pydanticモデル
│   │   ├── tileset.py       # TilesetCreate, TilesetUpdate
│   │   ├── feature.py       # FeatureCreate, FeatureUpdate, Bulk系
│   │   ├── datasource.py    # DatasourceCreate, DatasourceUpdate
│   │   └── api_key.py       # APIKeyCreate, APIKeyResponse 等
│   ├── routers/             # FastAPI APIRouter
│   │   ├── health.py        # /api/health
│   │   ├── auth.py          # /api/auth/* (login, refresh, me, password-reset, invitations 等)
│   │   ├── api_keys.py      # /api/api-keys (Phase 3 / Step 3.3-A)
│   │   ├── teams.py         # /api/teams (Phase 3 / Step 3.3-A)
│   │   ├── tilesets.py      # /api/tilesets CRUD
│   │   ├── features.py      # /api/features CRUD
│   │   ├── batch_features.py # /api/features/bulk, /api/features/export
│   │   ├── datasources.py   # /api/datasources CRUD
│   │   ├── colormaps.py     # /api/colormaps
│   │   ├── stats.py         # /api/stats
│   │   └── tiles/           # タイル配信
│   │       ├── mbtiles.py   # MBTiles
│   │       ├── dynamic.py   # Dynamic vector tiles
│   │       ├── pmtiles.py   # PMTiles
│   │       └── raster.py    # COG raster tiles
│   ├── auth/                # プラガブル認証パッケージ (Phase 3 / Step 3.3-A)
│   │   ├── __init__.py      # get_auth_provider, require_auth, AuthContext 等
│   │   ├── provider.py      # AuthProvider ABC
│   │   ├── providers/       # 実装: local.py, supabase.py
│   │   ├── models.py        # User, AuthResult, TokenPair
│   │   ├── errors.py        # AuthError 階層
│   │   ├── jwt_utils.py     # JWT 発行・検証
│   │   ├── password.py      # bcrypt ハッシュ
│   │   ├── tokens.py        # refresh_token CRUD
│   │   ├── rate_limit.py    # login_attempts レート制限
│   │   ├── api_key_auth.py  # API キー検証
│   │   ├── context.py       # AuthContext（JWT + API キー統合）
│   │   ├── email_backends/  # null / console / smtp
│   │   └── cli.py           # `python -m lib.auth.cli` CLI
│   ├── config.py            # 設定
│   ├── database.py          # DB接続
│   ├── cors_middleware.py   # CORS ミドルウェア（CORS_ORIGINS 反映）
│   ├── cache.py             # キャッシュ
│   ├── tile_cache.py        # タイル特化キャッシュ
│   ├── batch.py             # バッチ処理
│   ├── tiles.py             # タイル生成ユーティリティ
│   ├── pmtiles.py           # PMTiles処理
│   ├── raster_tiles.py      # ラスタータイル処理
│   └── storage.py           # ストレージ (S3/Supabase)
├── Dockerfile               # Fly.io用Dockerイメージ
├── pyproject.toml           # Python依存関係 (uv)
└── uv.lock                  # ロックファイル
```

## デプロイ

### Fly.io（推奨）

```bash
cd api
fly deploy
```

詳細は [FLY_DEPLOY.md](./FLY_DEPLOY.md) を参照してください。

### Vercel

```bash
vercel deploy
```

## 環境変数

主要変数の抜粋。詳細は [`docs/AUTH_SETUP.md`](../docs/AUTH_SETUP.md) を参照。

| 変数名 | 説明 | 必須 |
|--------|------|------|
| `DATABASE_URL` | PostgreSQL接続文字列 | ✅ |
| `AUTH_PROVIDER` | `local` または `supabase`（既定: `supabase`） | ✅ |
| `JWT_SECRET` | local モード必須。`SUPABASE_JWT_SECRET` にフォールバック可 | ⚠ local 必須 |
| `EMAIL_BACKEND` | `null` / `console` / `smtp`（既定: `console`） | ❌ |
| `INVITATION_BASE_URL` | 招待・リセットリンクの base URL | ❌ |
| `CORS_ORIGINS` | 許可する origin 一覧（CSV/JSON 配列） | ❌ |
| `COOKIE_SAMESITE` / `COOKIE_SECURE` | refresh Cookie のポリシー | ❌ |
| `LOCAL_AUTH_ALLOW_SIGNUP` | local モードで signup を許可するか | ❌ |
| `SUPABASE_URL` | `AUTH_PROVIDER=supabase` 必須 | 条件付き |
| `SUPABASE_SERVICE_ROLE_KEY` | `AUTH_PROVIDER=supabase` 必須 | 条件付き |
| `SUPABASE_JWT_SECRET` | `AUTH_PROVIDER=supabase` 必須 | 条件付き |
| `ENVIRONMENT` | 環境名（production/development） | ❌ |

## 開発

```bash
# 依存関係インストール
uv sync

# 開発サーバー起動
uv run uvicorn lib.main:app --reload --port 8000

# APIドキュメント
open http://localhost:8000/docs
```

## API エンドポイント

### Health
- `GET /api/health` - ヘルスチェック
- `GET /api/health/db` - DB接続チェック

### Auth (`/api/auth/*`)
- `POST /api/auth/login` - email + password ログイン（refresh Cookie 設定）
- `POST /api/auth/refresh` - access_token 再発行
- `POST /api/auth/logout` - refresh token 失効
- `GET /api/auth/me` - 現在のユーザー情報
- `PATCH /api/auth/me` - プロフィール更新
- `POST /api/auth/me/password` - パスワード変更
- `POST /api/auth/password-reset/request` - リセットメール送信
- `POST /api/auth/password-reset/confirm` - リセット実行
- `GET /api/auth/invitations/{token}` - 招待情報取得
- `POST /api/auth/accept-invitation` - 招待受諾 + 自動ログイン

### API Keys (`/api/api-keys/*`)
- `POST /api/api-keys` - APIキー発行（個人 / チーム）
- `GET /api/api-keys` - 自分の APIキー一覧
- `DELETE /api/api-keys/{id}` - 失効

### Teams (`/api/teams/*`)
- `POST /api/teams` - チーム作成
- `GET /api/teams` - 所属チーム一覧
- `POST /api/teams/{id}/invitations` - メンバー招待

### Tilesets
- `GET /api/tilesets` - タイルセット一覧
- `GET /api/tilesets/{id}` - タイルセット詳細
- `GET /api/tilesets/{id}/tilejson.json` - TileJSON
- `POST /api/tilesets` - タイルセット作成
- `PATCH /api/tilesets/{id}` - タイルセット更新
- `DELETE /api/tilesets/{id}` - タイルセット削除

### Features
- `GET /api/features` - フィーチャー一覧
- `POST /api/features` - フィーチャー作成
- `POST /api/features/bulk` - 一括インポート

### Tiles
- `GET /api/tiles/features/{z}/{x}/{y}.pbf` - ベクタータイル取得
- `GET /api/tiles/pmtiles/{id}/{z}/{x}/{y}.pbf` - PMTilesタイル
- `GET /api/tiles/raster/{id}/{z}/{x}/{y}.png` - ラスタータイル取得

### Datasources
- `GET /api/datasources` - データソース一覧
- `POST /api/datasources` - データソース作成
- `POST /api/datasources/cog/upload` - COGアップロード

### Stats & Colormaps
- `GET /api/stats` - 統計情報
- `GET /api/colormaps` - カラーマップ一覧

## ライセンス

MIT
