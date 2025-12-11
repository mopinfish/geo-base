# geo-base デプロイガイド

## Vercel へのデプロイ

### 前提条件

1. [Vercel アカウント](https://vercel.com/signup)
2. [Supabase アカウント](https://supabase.com/)（本番データベース用）
3. GitHub リポジトリへのプッシュ権限

---

## Step 1: Supabase プロジェクトの作成

### 1.1 新規プロジェクト作成

1. [Supabase Dashboard](https://supabase.com/dashboard) にログイン
2. "New Project" をクリック
3. プロジェクト名（例: `geo-base`）とパスワードを設定
4. リージョンを選択（例: Tokyo - `ap-northeast-1`）
5. "Create new project" をクリック

### 1.2 PostGIS 拡張の有効化

SQL Editor で以下を実行:

```sql
-- PostGIS拡張を有効化
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
```

### 1.3 テーブル作成

`docker/postgis-init/01_init.sql` の内容を SQL Editor で実行してテーブルを作成します。

### 1.4 接続情報の取得

1. Project Settings → Database に移動
2. "Connection string" セクションで "URI" を選択
3. 接続文字列をコピー（パスワードを実際の値に置き換え）

```
postgresql://postgres.[PROJECT_REF]:[YOUR_PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
```

> **注意**: Transaction モードの Pooler（ポート6543）を使用することを推奨します。

---

## Step 2: Vercel プロジェクトの設定

### 2.1 GitHub リポジトリの接続

1. [Vercel Dashboard](https://vercel.com/dashboard) にログイン
2. "Add New..." → "Project" をクリック
3. GitHub リポジトリ `geo-base` を選択
4. "Import" をクリック

### 2.2 プロジェクト設定

| 設定項目 | 値 |
|---------|-----|
| Framework Preset | Other |
| Root Directory | `.` (デフォルト) |
| Build Command | (空のまま) |
| Output Directory | (空のまま) |
| Install Command | (空のまま) |

### 2.3 環境変数の設定

"Environment Variables" セクションで以下を設定:

| 変数名 | 値 | 説明 |
|--------|-----|------|
| `DATABASE_URL` | `postgresql://postgres.[...]` | Supabase の接続文字列 |
| `ENVIRONMENT` | `production` | 環境識別子 |

オプション（必要に応じて）:
| 変数名 | 値 | 説明 |
|--------|-----|------|
| `SUPABASE_URL` | `https://[PROJECT_REF].supabase.co` | Supabase プロジェクト URL |
| `SUPABASE_ANON_KEY` | `eyJhbGci...` | Supabase anon キー |

### 2.4 デプロイ

"Deploy" をクリックしてデプロイを開始します。

---

## Step 3: 動作確認

デプロイ完了後、以下のエンドポイントで動作確認:

| エンドポイント | 説明 |
|---------------|------|
| `https://[your-app].vercel.app/` | プレビューページ |
| `https://[your-app].vercel.app/api/health` | ヘルスチェック |
| `https://[your-app].vercel.app/api/health/db` | DB接続チェック |
| `https://[your-app].vercel.app/api/tilesets` | タイルセット一覧 |

---

## トラブルシューティング

### データベース接続エラー

**症状**: `/api/health/db` が `"database": "disconnected"` を返す

**対処法**:
1. `DATABASE_URL` が正しく設定されているか確認
2. Supabase の接続文字列でパスワードが正しいか確認
3. Pooler モード（ポート6543）を使用しているか確認
4. Supabase Dashboard でプロジェクトがアクティブか確認

### PostGIS エラー

**症状**: `/api/health/db` が `"postgis": "unavailable"` を返す

**対処法**:
1. Supabase SQL Editor で `SELECT PostGIS_Version();` を実行
2. エラーが出る場合は `CREATE EXTENSION postgis;` を再実行

### タイムアウトエラー

**症状**: API リクエストがタイムアウトする

**対処法**:
1. Vercel Pro プランでは `maxDuration` を60秒に増加可能
2. クエリの最適化（インデックス追加等）
3. 空間インデックスの確認: `CREATE INDEX IF NOT EXISTS idx_features_geom ON features USING GIST (geom);`

---

## ローカル環境との切り替え

### ローカル開発

```bash
# api/.env を編集
ENVIRONMENT=development
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/geo_base
```

### 本番環境（Vercel）

環境変数は Vercel Dashboard で管理されます。

---

## 更新・再デプロイ

コードを変更して GitHub にプッシュすると、Vercel が自動的に再デプロイします。

```bash
git add .
git commit -m "feat: 機能追加"
git push origin main
```

---

## セキュリティに関する注意

1. **環境変数**: 機密情報は必ず環境変数で管理し、コードにハードコードしない
2. **CORS**: 本番環境では `CORS_ORIGINS` を特定のドメインに制限することを推奨
3. **API キー**: 将来的に認証機能を追加する場合は、Supabase Auth の利用を検討

---

## 参考リンク

- [Vercel Python Runtime](https://vercel.com/docs/functions/runtimes/python)
- [Supabase Database](https://supabase.com/docs/guides/database)
- [FastAPI on Vercel](https://vercel.com/guides/using-fastapi-with-vercel)
