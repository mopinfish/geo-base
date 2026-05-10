# インフラ移行検討記録 — Cloudflare 一本化の実現可能性

**作成日**: 2026-05-08
**ステータス**: 検討完了 / Cloudflare 集約は当面見送り。代わりに **Supabase 依存を 2026-05-10 に完全廃止** し、Fly Postgres + local Auth に切替済み。

> [!IMPORTANT]
> ## 2026-05-10 アップデート: Supabase 完全廃止
>
> 本ドキュメント本文は 2026-05-08 時点の調査記録だが、その後の状況変化により
> インフラ構成の一部は前提が変わった。以下を踏まえて読むこと:
>
> - **DB**: Supabase Free Plan の長期 paused 復旧不能を機に、本番 DB を
>   **Fly Machine 上の自前 PostGIS (`geo-base-pg` app, region nrt)** に移行
>   (PR #73、`docs/POSTGRES_SETUP.md` 参照)
> - **Auth**: `AUTH_PROVIDER=supabase` を完全廃止し、自前の **local provider**
>   (`api/lib/auth/`) で JWT を発行する構成に切替 (PR #71 / #74、`docs/AUTH_SETUP.md` 参照)
> - **Storage**: COG/PMTiles のアップロード backend は Issue #72 Phase 1.2 で
>   **Fly Tigris (S3 互換)** に切替予定
> - **MCP / Admin UI**: 配置先 (Fly.io / Vercel) は変更なし
>
> 結果として、Supabase ダッシュボード上の `geo-base` / `geo-mcp` プロジェクトと
> Supabase アカウント自体も 2026-05-10 に削除済み (Issue #72 Phase 4)。
> Cloudflare 集約は引き続き「将来検討」の状態 (本文の結論と同じ)。
>
> Issue #72 (Supabase 完全廃止トラッキング) も参照。

---

## 背景

現行の geo-base は以下の3社にまたがってホストされている：

| サービス | プラットフォーム |
|---|---|
| API（FastAPI） | Fly.io |
| MCP Server（FastMCP） | Fly.io |
| Admin UI（Next.js） | Vercel |
| PostgreSQL + PostGIS | Supabase |
| Auth | Supabase |
| Storage（COG/PMTiles） | Supabase Storage（旧 Vercel Blob） |
| Redis（キャッシュ） | Upstash |

これを **Cloudflare 1社に集約** することで、運用先・コスト・ベンダー管理の一元化が可能か検討した。

---

## 結論

### 1. 「真の Cloudflare 100% 単一ベンダー」は **技術的に不可能**

**主要ブロッカー**: PostGIS。

- Cloudflare D1 は SQLite ベースで PostGIS 非対応（公式に "PostGIS は D1 にはない複雑な PostgreSQL 機能" と明言）
- Cloudflare には PostGIS をサポートするマネージド PostgreSQL サービスが存在しない
- geo-base のコア機能（`ST_AsMVT` による動的ベクタータイル生成、空間分析）は PostGIS 必須

→ PostgreSQL+PostGIS は **必ず外部に置く必要がある**（Neon, Supabase 維持, 自前ホスティング 等）

### 2. 「Cloudflare 中心 + 外部 PostGIS」構成は **実現可能**

2026年4月に **Cloudflare Containers が GA**（Workers Paid プラン）したことで、Python/FastAPI + GDAL/rio-tiler を含む現行 API もコンテナ化して Cloudflare 上で動かせる。

| 現行 | 移行先候補 | 実現性 |
|---|---|:---:|
| Vercel: Next.js Admin UI | Cloudflare Pages（+ `@opennextjs/cloudflare`） | ◯ |
| Fly.io: FastAPI | Cloudflare Containers（GA: 2026-04） | △（GA 直後で運用ノウハウ薄い） |
| Fly.io: FastAPI | Cloudflare Workers（Python） | ✕（Pyodide ベースで C 拡張不可：rasterio/rio-tiler/GDAL/Shapely 全滅） |
| Fly.io: FastMCP | Cloudflare Containers / Workers | ◯ |
| Supabase: PostgreSQL+PostGIS | Cloudflare D1 | **✕**（PostGIS 非対応） |
| Supabase: PostgreSQL+PostGIS | 外部 Postgres（Neon 等）+ Hyperdrive | ◯（Cloudflare 外） |
| Supabase Auth | 自前 JWT / Better Auth / Clerk 等 | △（後述） |
| Supabase Storage | Cloudflare R2（S3 互換） | ◎ |
| Upstash Redis | Cloudflare KV / Cache API / Durable Objects | ◯ |

### 3. 認証・認可（RBAC）の Cloudflare 移行可能性

**Cloudflare 純正の Supabase Auth 同等マネージドサービスは存在しない**：
- **Cloudflare Access / Zero Trust**: 社内ツール向け。ユーザーデータベースを持たず、外部 IdP（Google/GitHub/SAML/OIDC）へ委譲。**消費者向けアプリの認証には不適合**
- **Cloudflare RBAC（Bach）**: Cloudflare アカウント自身の管理用であり、アプリケーションのユーザー RBAC とは無関係
- **workers-oauth-provider**: OAuth トークン発行のみ。ユーザー登録 UI / パスワード管理 / MFA / ソーシャルログインは含まれない

**実現するなら自前構築**：
- **Better Auth + Cloudflare D1/KV/Workers**: 機能面では Supabase Auth と同等以上を構築可能（Email/Password、OAuth、MFA、Organizations プラグインによる RBAC 等）
- ただし **マネージド利便性は低下**（メール送信プロバイダ別途契約、運用責任、既知バグ追従）

**重要な認識**：
- Supabase Auth 自体は RBAC のマネージド機能を提供していない（`teams`/`team_members` 等は自前テーブル設計）
- → **geo-base の Phase 3 で実装中の RBAC は、Supabase Auth ロックインの度合いが想定より小さい**
- 「Postgres を残せば Auth はどこでも動かせる」状態を作っておくのが最もコスト効率的

---

## 移行パスの選択肢

### パス1: 段階移行（移行する場合の推奨）

| ステップ | 内容 | 工数感 |
|---|---|---|
| 1 | ストレージ → R2 | 1〜2週 |
| 2 | Admin UI → Cloudflare Pages | 1〜2週 |
| 3 | Upstash Redis → Cache API / KV | 2〜3週 |
| 4 | API → Cloudflare Containers | 3〜6週 |
| 5 | MCP → Cloudflare Containers | 2週 |
| 6 | PostgreSQL → Neon + Hyperdrive | 4〜8週 |
| 7 | Supabase Auth → 自前 JWT | 4〜8週 |

ステップ 1〜5 で 2〜3ヶ月、6〜7 まで含めると合計 4〜6ヶ月。

### パス2: 部分移行（最も現実的）

ストレージ・キャッシュ・UI のみ Cloudflare に寄せ、API/DB/認証は Fly.io+Supabase 維持。コスト削減と CDN 性能向上は得られるが「単一ベンダー化」目標は未達成。

### パス3: ビッグバン

非推奨。Phase 3 の進行を完全に止める必要があり、リスクが高すぎる。

---

## タイミング検討（Phase 3 = team/role 実装との関係）

### 「team/role 前」に移行 — ❌ 非推奨

- Phase 3 開発が 3〜6ヶ月停滞
- Cloudflare Containers が GA 直後で本番運用ノウハウ・障害事例・最適化ベストプラクティスが蓄積されていない
- 既に着手済みの実装が宙に浮く

### 「team/role 後」に移行 — ✅ 推奨

- Phase 3 の delivery を止めない
- Containers がさらに半年〜1年成熟する間に Phase 3 を本番投入し、移行設計の精度を上げる
- 移行作業が新機能開発と並行する必要がない
- Phase 3 完了時点でテスト網が拡充されており、リグレッション検出が容易

### 中立的な事実

移行コストの大半は **team/role の有無に依存しない**：
1. Python/GDAL イメージを Cloudflare Containers でビルド・運用する
2. PostgreSQL 移行とデータ転送
3. Supabase Auth → 別実装
4. R2 / KV / Cache API 対応

→ 「前にやる優位性」は想定より小さい。

---

## 当面の方針（2026-05-08 決定）

1. **Cloudflare 一本化移行は当面見送り**
2. **Phase 3（team/role）の作り込みを優先**
3. **ただし将来の移行可能性を残すため、Supabase 依存を極力薄くする設計を Phase 3 で採用する**

---

## 将来移行する場合に備えた準備工程（Phase 3 進行中に並行実施）

### Phase 3 内で実施
1. **`api/lib/auth.py` の JWT 検証を発行者非依存にリファクタ**
   - `SUPABASE_JWT_SECRET` を `JWT_SECRET` に汎用化（環境変数の後方互換は維持）
   - audience を環境変数で設定可能に
   - JWKS（公開鍵）方式への拡張余地を残す
2. **新規 RLS は Supabase 専用関数（`auth.uid()`）への直接依存を最小化**
   - `current_setting('app.user_id')` 等でアプリ層から値を渡す方式を採用
   - Supabase 専用関数を使う場合はラッパー関数を経由
3. **Admin UI の Supabase クライアント呼び出しを抽象化**
   - `app/src/lib/auth/` レイヤーを作り、将来 Better Auth 等に差し替え可能にする
4. **Postgres 拡張機能の利用箇所を棚卸し**
   - `pg_cron`, `pgsodium`, `pg_net` 等の Supabase 固有拡張を使っていないか確認

### Phase 3 完了後（PoC 段階）
5. **Cloudflare Containers PoC**（1〜2 スプリント）
   - 既存 Dockerfile を Cloudflare Containers にデプロイ
   - ベクタータイル配信のコールドスタート時間 / コスト / 観測性を実測
6. **Better Auth on Cloudflare PoC**（1〜2 スプリント）
   - geo-base のサブセット（Admin UI ログインだけ）を Better Auth に置換
   - 既知バグ（KV TTL、cookieCache フォールバック）の影響範囲を実測
7. **PoC 結果に基づき次の判断**
   - 良好 → Phase 移行計画を本格策定
   - 課題大 → 部分移行（パス2）に留める
   - マネージド最優先 → Clerk/Auth0 検討

---

## Phase 3 で実施済みの準備工程（2026-05-08 完了）

Phase 3 / Step 3.3-A（プラガブル認証）の実装に伴い、上記「Phase 3 内で実施」のうち 1〜4 が完了:

- ✅ **`api/lib/auth.py` をパッケージ化、JWT 発行者非依存にリファクタ**
  - 単一ファイルから `api/lib/auth/` パッケージへ分割（`provider.py`, `providers/{local,supabase}.py`, `jwt_utils.py`, `tokens.py`, `password.py`, `rate_limit.py`, `email_backends/`, `cli.py` 等）
  - `JWT_SECRET` を汎用化（`SUPABASE_JWT_SECRET` は supabase モード専用に縮退）
  - `AUTH_PROVIDER=local|supabase` 環境変数で発行者を切替（factory pattern）
- ✅ **新規 RLS は permissive のまま、アプリ層認可で対応**
  - `auth.uid()` への直接依存を新規スキーマで排除
  - 行レベル認可は `lib/auth/api_key_auth.py` の `check_tileset_access_v2` 等でアプリ層実施
  - ポータブル RLS（`current_setting('app.user_id')`）への移行は Phase 4 で対応予定
- ✅ **Admin UI の Supabase クライアントを完全撤去**
  - `app/src/lib/supabase/`、`app/src/contexts/auth-context.tsx`、`app/src/app/auth/callback/` を削除
  - `app/src/lib/auth/` の `AuthClient` シングルトン + `AuthProvider` で抽象化
  - `@supabase/ssr` および `@supabase/supabase-js` 依存を `package.json` から削除
- ✅ **Supabase 固有 Postgres 拡張は使っていないことを確認**
  - `pg_cron` 不使用 → 期限切れトークン削除は CLI コマンド `python -m lib.auth.cli cleanup-expired` で実施（運用は scheduled machine or 外部 cron を推奨）
  - `pgsodium`, `pg_net` も不使用

実装規模:
- Backend: 32 コミット、auth テスト 130+（全 479 テスト PASS）
- Admin UI: 10 コミット、Supabase クライアント完全撤去 + 認証ページ 6 ページ新規実装
- ドキュメント: `docs/AUTH_SETUP.md`、`docs/AUTH_MIGRATION.md` 新規

将来 Cloudflare 寄せ移行する際、認証層の手直しは不要となる状態を確立。

---

## 参考リンク

- [Cloudflare Containers and Sandboxes are now generally available (2026-04)](https://developers.cloudflare.com/changelog/post/2026-04-13-containers-sandbox-ga/)
- [Cloudflare D1 GeoSpatial queries feature request (#9324)](https://github.com/cloudflare/workers-sdk/issues/9324)
- [Easy Postgres integration on Cloudflare Workers with Neon.tech](https://blog.cloudflare.com/neon-postgres-database-from-workers/)
- [Managed OAuth for Cloudflare Access](https://blog.cloudflare.com/managed-oauth-for-access/)
- [Better Auth on Cloudflare (Hono)](https://hono.dev/examples/better-auth-on-cloudflare)
- [better-auth-cloudflare integration library](https://github.com/zpg6/better-auth-cloudflare)

---

## 改訂履歴

| 日付 | 著者 | 変更内容 |
|---|---|---|
| 2026-05-08 | Claude（調査）/ otsuka（決定） | 初版作成。Cloudflare 一本化は当面見送り、Phase 3 を優先する方針で記録 |
| 2026-05-08 | Claude | Phase 3 / Step 3.3-A 完了に伴い「Phase 3 で実施済みの準備工程」を追記 |
