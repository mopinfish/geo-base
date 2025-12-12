# geo-base Admin UI

geo-base タイルサーバーの管理画面です。

## 技術スタック

- **フレームワーク**: Next.js 16 (App Router)
- **言語**: TypeScript
- **スタイリング**: Tailwind CSS v4
- **UIコンポーネント**: shadcn/ui (手動セットアップ)
- **アイコン**: Lucide React

## 開発環境のセットアップ

```bash
# 依存関係のインストール
npm install

# 開発サーバーの起動
npm run dev

# ビルド
npm run build

# 本番サーバーの起動
npm start
```

## ディレクトリ構成

```
app/
├── src/
│   ├── app/                    # App Router ページ
│   │   ├── page.tsx            # ダッシュボード
│   │   ├── layout.tsx          # ルートレイアウト
│   │   ├── globals.css         # グローバルスタイル
│   │   ├── login/              # ログインページ
│   │   ├── tilesets/           # タイルセット管理
│   │   ├── features/           # フィーチャー管理
│   │   ├── datasources/        # データソース
│   │   └── settings/           # 設定
│   ├── components/
│   │   ├── ui/                 # shadcn/ui コンポーネント
│   │   └── layout/             # レイアウトコンポーネント
│   ├── lib/
│   │   ├── api.ts              # APIクライアント
│   │   └── utils.ts            # ユーティリティ関数
│   ├── hooks/                  # カスタムフック
│   └── types/                  # 型定義
├── public/                     # 静的ファイル
├── .env.example                # 環境変数サンプル
├── .env.local                  # ローカル環境変数
├── package.json
├── tailwind.config.ts
└── tsconfig.json
```

## 環境変数

`.env.local` を作成し、以下の環境変数を設定してください：

```env
# API設定
NEXT_PUBLIC_API_URL=https://geo-base-puce.vercel.app

# Supabase設定（Step 3.2で使用）
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

## 機能

### Step 3.1（現在）

- [x] Next.js プロジェクトセットアップ
- [x] Tailwind CSS + shadcn/ui セットアップ
- [x] 基本レイアウト（サイドバーナビゲーション）
- [x] ダッシュボードページ
- [x] タイルセット一覧ページ
- [x] フィーチャー一覧ページ
- [x] APIクライアント
- [x] プレースホルダーページ（ログイン、設定、データソース）

### Step 3.2（予定）

- [ ] Supabase Auth 連携
- [ ] ログイン/ログアウト機能
- [ ] セッション管理
- [ ] 認証ミドルウェア

### Step 3.3（予定）

- [ ] タイルセット詳細ページ
- [ ] タイルセット作成/編集フォーム
- [ ] MapLibre GL JS によるプレビュー

### Step 3.4（予定）

- [ ] フィーチャー詳細ページ
- [ ] フィーチャー作成/編集
- [ ] GeoJSON/Shapefile アップロード

## 接続先API

- **本番API**: https://geo-base-puce.vercel.app
- **MCPサーバー**: https://geo-base-mcp.fly.dev

## ライセンス

MIT
