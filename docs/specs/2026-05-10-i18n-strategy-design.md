# i18n 戦略デザイン

- **Date**: 2026-05-10
- **Status**: Approved (brainstorming completed)
- **Owner**: @OtsukaNoboru
- **Related Issues**: TBD（本ドキュメント承認後に Epic + 子 Issue を起票）

## 1. 背景

`geo-base` は地理空間タイルサーバーシステムのモノレポであり、現在は日本語を基本としてドキュメント・UI 文言・API エラーメッセージが書かれている。コード識別子（変数名・関数名・型）は英語で記述されている。

このリポジトリを「全世界で利用可能な OSS」として発展させていくにあたり、国際化（i18n）対応が必要となる。一方、社内開発の速度を落とさないこと、既存の社内向けドキュメント資産を翻訳コストで埋もれさせないこと、もまた重要である。

## 2. ゴール

1. OSS としての発見性とコントリビューション障壁を下げる（README、Issue/PR テンプレ、ライセンス周りを英語化）。
2. 公開コード表面（API レスポンス、MCP ツール記述）から日本語混入を取り除き、海外ユーザーが直接利用できる状態にする。
3. 管理 UI を i18n 化し、JA + EN の 2 言語で動作させる（仕組みは多言語拡張可能な形）。
4. 公開対象のドキュメントを英語で提供しつつ、社内向けドキュメントは日本語のまま維持する。

## 3. 全体方針

### 3.1 ハイブリッド方針

- **公開表面 = 英語 primary**
  - `README.md`、`CONTRIBUTING.md`、Issue/PR テンプレート
  - コードコメント・docstring（触った箇所から段階移行）
  - API エラーメッセージ・OpenAPI 記述
  - MCP ツール記述
- **社内向け運用ドキュメント = 日本語のまま**
  - `HANDOVER_*.md`、`ROADMAP_*.md`、`AUTH_E2E_CHECKLIST.md`、`INFRA_MIGRATION_INVESTIGATION.md`、`CLAUDE.md` など
- **管理 UI = i18n 化**
  - 初期は JA + EN の 2 言語、仕組みは多言語拡張可能。

### 3.2 機械向け表面の言語

- API エラーレスポンス・MCP ツール記述は **英語固定**。
- `Accept-Language` での出し分けは行わない（OSS 慣行・実装コスト・OSSとしての標準性を考慮）。
- API は machine-readable な `code` を必ず返し、UI 側のメッセージ catalog で訳出する。

## 4. 表面ごとのスコープ

| 表面 | 方針 | 備考 |
|---|---|---|
| `README.md` | 英語 primary | `README.ja.md` を併設、相互リンク |
| `CONTRIBUTING.md` | 英語 primary | 新設 |
| Issue / PR テンプレート | 英語 primary | `.github/ISSUE_TEMPLATE/`、`.github/PULL_REQUEST_TEMPLATE.md` |
| `LICENSE` | 英語 | 既に英語、変更なし |
| `SECURITY.md` | 英語 | 新設（OSS 慣行） |
| API エラーメッセージ | 英語固定 | `code` 付与必須 |
| OpenAPI description / summary | 英語 | FastAPI のルーター・モデルの description |
| MCP ツール記述・docstring | 英語 | AI 学習データと整合 |
| 管理 UI 文言 | i18n 化（JA + EN） | `next-intl` を採用 |
| `docs/API_REFERENCE.md` | 英語 primary | Phase 4 |
| `docs/AUTH_SETUP.md` | 英語 primary | Phase 4 |
| `docs/POSTGRES_SETUP.md` | 英語 primary | Phase 4 |
| `docs/REDIS_SETUP.md` | 英語 primary | Phase 4 |
| `docs/LOCAL_DEVELOPMENT.md`（リポジトリ直下にもある） | 英語 primary | Phase 4 |
| `docs/ACCESS_CONTROL_REVIEW.md` | 英語 primary | Phase 4（公開対象として再検討の余地あり） |
| `HANDOVER_*.md` | 日本語のまま | 社内向け |
| `ROADMAP_*.md` | 日本語のまま | 社内向け |
| `docs/AUTH_E2E_CHECKLIST.md` | 日本語のまま | 社内向け運用 |
| `docs/INFRA_MIGRATION_INVESTIGATION.md` | 日本語のまま | 社内向け（履歴文書） |
| `docs/AUTH_MIGRATION.md` | 日本語のまま | 社内向け（履歴文書） |
| `CLAUDE.md` | 日本語のまま | 社内開発者向け |
| `docs/specs/*.md` | 日本語のまま | 社内設計記録 |

## 5. Admin UI のアーキテクチャ

### 5.1 ライブラリ選定

採用: **`next-intl`**

理由:
- Next.js 16 App Router との 1st-class 統合（Server Components 内で `getTranslations()` がそのまま使える）。
- 型安全（メッセージキーが TypeScript で補完される）。
- ミドルウェアでロケール検出が可能（`Accept-Language` / Cookie / pathname のすべてに対応）。
- バンドルサイズが小さく、catalog の動的ロードが可能。

不採用候補:
- `react-i18next`: 成熟しているが App Router での RSC 統合がぎこちない。
- `paraglide-js`: モダンだが Next.js 専用ツールが薄く、エコシステム未成熟。
- `lingui`: 良いが Next.js 専用機能が `next-intl` ほど整備されていない。

### 5.2 メッセージ catalog の構造

```
app/src/locales/
  en/
    common.json
    tilesets.json
    auth.json
    teams.json
    api-keys.json
    settings.json
    ...
  ja/
    common.json
    tilesets.json
    ...
```

- namespace（ファイル）単位で分割。
- キーは `camelCase`（例: `tilesets.upload.success`）。
- 補間プレースホルダは ICU MessageFormat（`{name}`、複数形対応）。

### 5.3 ロケール解決の優先順位

1. ユーザー DB 設定（`users.preferred_locale` カラム新設、null 許容）
2. Cookie（`NEXT_LOCALE`）
3. ブラウザの `Accept-Language` ヘッダ
4. デフォルト = `en`

`users.preferred_locale` の初期値は null（ユーザーが UI から明示的に切り替えた時に永続化）。既存ユーザーが急に英語表示にならないよう、Cookie 永続を最優先で扱う。

### 5.4 言語切替 UI

- ヘッダー右上にドロップダウンを配置（地球儀アイコン + 現在のロケール）。
- 切替時に Cookie + DB（ログイン中の場合）を更新。

### 5.5 CI チェック

- Vitest で missing-key 検知テスト（en と ja のキーセット差分が 0 であることを assert）。
- `eslint-plugin-i18next` 等で UI コードのハードコード文字列を検出（試験導入、ノイズが多ければ外す）。

## 6. API エラーレスポンス設計

### 6.1 レスポンス形式

```json
{
  "error": {
    "code": "tileset_not_found",
    "message": "The requested tileset does not exist.",
    "details": { "tileset_id": "..." }
  }
}
```

- `code`: 英語スネークケース、安定した識別子。
- `message`: 英語、人間可読。
- `details`: オプション、構造化データ。

### 6.2 既存エラーの取り扱い

- Phase 2 で全エンドポイントを棚卸し、日本語文言を英語化＋ `code` 付与。
- `code` の命名規則は `<domain>_<reason>`（例: `tileset_not_found`、`auth_invalid_credentials`）。
- 既存クライアント（Admin UI）は `code` ベースで訳出するように同時改修。

### 6.3 OpenAPI description の英語化

- `lib/routers/*.py` の `summary` / `description`、`lib/models/*.py` の `Field(..., description=...)` を英語化。
- 既存日本語 docstring は段階的に置き換え（Phase 2 のスコープ）。

## 7. MCP ツール記述

- `mcp/tools/*.py` の `@mcp.tool()` の docstring と引数説明を英語化。
- ツール名（識別子）は既に英語。
- `mcp/API_REFERENCE.md` も Phase 2 で英語化。

## 8. 翻訳ワークフロー

- すべて **インリポジトリ（PR ベース）** で運用。Crowdin / Lokalise 等の外部 SaaS は導入しない。
- 翻訳作業:
  1. AI 翻訳（Claude）で初稿を作成。
  2. メンテナがレビューしてマージ。
- 言語追加（CN/KR/ES 等）は将来のコントリビューションとして歓迎するが、Phase 1 では着手しない。`CONTRIBUTING.md` に「3 言語目以降の追加方法」を簡潔に記載。

## 9. フェーズ計画

### Phase 1: OSS 表玄関の英語化

**スコープ**:
- `README.md` を英語化、日本語版を `README.ja.md` として残す。トップに相互リンクを配置。
- `CONTRIBUTING.md` を新設（英語）。
- `.github/ISSUE_TEMPLATE/`（bug_report、feature_request）と `.github/PULL_REQUEST_TEMPLATE.md` を英語で整備。
- `SECURITY.md` を新設（英語）。
- GitHub リポジトリの About 説明・Topics・Description を英語化。
- ラベルの整理（必要なら英語化）。

**完了の定義**:
- リポジトリトップを英語ネイティブが訪問してもプロジェクト概要・セットアップ・コントリビュート方法が理解できる。
- すべての Issue / PR テンプレートが英語。

**見積もり**: 1〜2 PR、1〜3 日。

### Phase 2: 公開コード表面の英語化

**スコープ**:
- API エラーメッセージの棚卸しと英語化＋ `code` 付与（`api/lib/routers/*.py`、`api/lib/errors.py`）。
- OpenAPI description / summary の英語化（FastAPI ルーター・Pydantic モデル）。
- MCP ツール docstring の英語化（`mcp/tools/*.py`）。
- `mcp/API_REFERENCE.md` の英語化。
- 新規コミットメッセージ・新規追加コードのコメントは英語化。既存コメントは「触った箇所から」段階移行（一括書き換えはしない）。

**完了の定義**:
- API レスポンス（`message` フィールド）と OpenAPI スキーマに日本語が含まれない（grep で検証）。
- MCP ツール記述に日本語が含まれない。
- 既存クライアント（Admin UI）が `code` ベースで訳出に切り替わっており、ユーザー体験のリグレッションがない。

**見積もり**: 数 PR に分割、1〜2 週間。

### Phase 3: Admin UI の i18n 化

**スコープ**:
- `next-intl` 導入、`app/src/locales/{en,ja}/*.json` の catalog 構造を確立。
- 全画面の文言を catalog 化（ハードコード排除）。
- 言語切替 UI（ヘッダー）。
- ロケール永続化（Cookie + ユーザー DB の `preferred_locale` カラム）。
- Vitest で missing-key 検知テスト。
- API エラー `code` → catalog 訳出のフロー実装。

**完了の定義**:
- `?lang=en` または明示切替で UI が完全に英語動作する。
- ハードコード文字列が 0（Lint チェックを通る）。
- en / ja の catalog キーセットが一致（CI で検証）。

**見積もり**: 大型 PR、2〜4 週間。複数 PR に分割可能（例: 基盤導入 → 画面ごとの段階移行）。

### Phase 4: 公開ドキュメントの英語化

**スコープ**:
- 公開対象の `docs/*.md`（API_REFERENCE、AUTH_SETUP、POSTGRES_SETUP、REDIS_SETUP、LOCAL_DEVELOPMENT、DEPLOY、ACCESS_CONTROL_REVIEW など）を英語化。
- 日本語版は `*.ja.md` として残す。
- ルート直下の公開対象ドキュメント（`DEPLOY.md`、`LOCAL_DEVELOPMENT.md`、`TESTING.md`）も同様。

**完了の定義**:
- 公開対象として識別したドキュメントすべてに英語版が存在する。
- README から英語版へのリンクが整備されている。

**見積もり**: 数 PR、1〜2 週間。

## 10. 非ゴール（Out of scope）

- DB 内のユーザー生成コンテンツ（タイルセット名・説明など）の翻訳: ユーザー責務。
- 3 言語目以降（CN/KR/ES など）の翻訳: 仕組みは用意するが、初期翻訳作業は対象外。
- 社内向けドキュメント（`HANDOVER_*`、`ROADMAP_*`、`AUTH_E2E_CHECKLIST`、`CLAUDE.md` など）の英語化。
- 監視・ログ出力の i18n 化: 運用上不要。
- コード内コメントの一括英語化: 段階移行とする（触ったところから）。

## 11. リスクと緩和策

| リスク | 緩和策 |
|---|---|
| コードコメント英語化の摩擦・PR レビュー停滞 | 一括書き換えはしない。「触った箇所から」のルールを `CONTRIBUTING.md` に明記。 |
| 既存日本語ユーザーの体験劣化（突然英語表示になる） | ロケール解決優先順位で Cookie / `Accept-Language` を尊重。明示切替まで JA を維持。 |
| AI 翻訳の品質ばらつき | メンテナレビュー必須。`CONTRIBUTING.md` に翻訳プロセスを明記。 |
| Phase 2 でのエラーレスポンス変更が UI を壊す | UI 側の `code` ベース訳出への切替を Phase 2 のスコープに含める（API と UI を同期改修）。 |
| `preferred_locale` カラム追加のマイグレーション | 既存ユーザーは null（フォールバック動作）。マイグレーションは追加のみで非破壊。 |

## 12. 成功指標

- **Phase 1**: GitHub の `geo-base` リポジトリを英語ネイティブが訪問しても、ドキュメント・Issue テンプレが理解できる。
- **Phase 2**: API レスポンス・MCP ツール記述に日本語混入なし（CI で grep 検証）。
- **Phase 3**: Admin UI が EN/JA で完全動作、CI で missing-key 検知。
- **Phase 4**: 公開対象ドキュメントすべてに英語版が存在。

## 13. 起票する Issue 構造

- **Epic**: 「i18n strategy: enable global OSS adoption」(English title)
  - 本ドキュメントへリンク
  - Phase 1〜4 のチェックリストを掲載
- **Sub-issue 1**: Phase 1 — OSS frontdoor English localization
- **Sub-issue 2**: Phase 2 — Public code surface English standardization
- **Sub-issue 3**: Phase 3 — Admin UI i18n with `next-intl` (JA + EN)
- **Sub-issue 4**: Phase 4 — Public documentation English localization

各 Sub-issue は独立して PR にできる粒度とし、Epic から進捗を追跡する。

## 14. 参考

- `next-intl` 公式: https://next-intl-docs.vercel.app/
- OSS i18n の慣行: GitHub・Stripe・Linear などの API は英語固定 + `code` の構造を採用。
- 内部の関連スキル: `superpowers:brainstorming`、`superpowers:writing-plans`。
