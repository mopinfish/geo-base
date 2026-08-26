# geo-base

> [English](./README.md) | 日本語

geo-baseは、小規模チーム向けのセルフホスト可能なオープンソース地理空間プラットフォームです。FastAPIタイルAPI、Next.js管理画面、PostGIS、ラスター／ベクタータイル配信、AIクライアント向けMCPサーバーを組み合わせています。

## FOSS4G 2026 Hiroshima

発表「A Self-Hostable Open-Source Geospatial Platform for Small Teams, with Natural Language Querying via MCP」と再現可能なデモは、[docs/foss4g-2026](./docs/foss4g-2026/README.md)で公開しています。

## 構成

- `api/`: FastAPIによるラスター／ベクタータイルAPI
- `app/`: Next.js管理画面
- `mcp/`: 地理空間操作を提供するFastMCPサーバー
- `docker/`: ローカル用PostGIS・Redis

## ローカル起動

Python 3.11以上、Node.js 20以上、Docker、Docker Compose、[uv](https://docs.astral.sh/uv/)が必要です。

```bash
git clone https://github.com/mopinfish/geo-base.git
cd geo-base
docker compose -f docker/docker-compose.yml up -d
```

別々のターミナルで各サービスを起動します。

```bash
cd api && uv sync && uv run uvicorn lib.main:app --reload --port 8000
cd mcp && uv sync && uv run python server.py
cd app && npm install && npm run dev
```

詳しくは[ローカル開発](./docs/manuals/LOCAL_DEVELOPMENT.ja.md)、[デプロイ](./docs/manuals/DEPLOY.ja.md)、[テスト](./docs/manuals/TESTING.ja.md)を参照してください。

## コントリビューションとライセンス

IssueとPull Requestを歓迎します。[CONTRIBUTING.md](./CONTRIBUTING.md)と[SECURITY.md](./SECURITY.md)をご確認ください。ライセンスは[MIT](./LICENSE)です。
