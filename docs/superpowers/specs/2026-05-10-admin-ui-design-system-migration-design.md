# Admin UI: デジタル庁デザインシステム準拠への段階移行 — 設計

- 起票日: 2026-05-10
- 対象: `app/`（Admin UI、Next.js 16 + React 19 + Tailwind v4 + shadcn/ui）
- ステータス: 設計段階（Issue 起票前）
- リポジトリ: `mopinfish/geo-base`
- GitHub Project: <https://github.com/users/mopinfish/projects/8>

## 1. 背景

`app/` は現在、shadcn/ui (`style: new-york`, `baseColor: neutral`) を土台に
構築されている。配色は HSL の CSS 変数で管理され、ライト/ダーク両対応。
ページは login / password-reset / accept-invitation / api-keys /
datasources / features / settings / teams / tilesets を含む 23 ページ規模。

[デジタル庁デザインシステム](https://design.digital.go.jp/) は β 版で
公開されており、主配布物は **Figma ライブラリ** + **HTML/CSS スニペット**
（GitHub 順次展開予定）。**npm パッケージや公式 React 実装は提供されていない**。
そのため本件の "移行" は、shadcn/ui を土台として残しつつ、**トークン・
フォーム規約・a11y の 3 軸でデジタル庁準拠に寄せる** 作業になる。

## 2. ゴール / 非ゴール

### 2.1 ゴール

- デザイントークン（色 / タイポ / スペーシング / フォーカス）が
  デジタル庁準拠で `globals.css` に整理されている
- フォーム共通部品（Label / Input / Textarea / Select / エラー / 必須）が
  デジタル庁ガイドラインに準拠
- WCAG 2.1 AA 相当の a11y 監査をパス（コントラスト・キーボード操作・SR 検証）

### 2.2 非ゴール（明示）

- 色のテイスト・情報設計・各種ボタン配置は **現状を踏襲**
  （ブランドカラーを丸ごとデジタル庁ブルーに置き換える等はしない）
- shadcn/ui を別ライブラリに置き換えることはしない
- ページ単位の UX/IA 改修（情報整理）は本件のスコープ外
- API / MCP / DB 側への変更は含まない

## 3. アプローチ

選択した方針は **「トークン整備 + フォーム/アクセシビリティ準拠」**
（ブレスト時の選択肢 c）。

理由:

- 既存の色テイスト・配置・情報設計を維持したいというユーザー要求と整合する
- デジタル庁 DS の最大の価値は a11y/フォーム規約・公文書系の見出し階層に
  あり、その部分の取り込みが投資対効果が高い
- shadcn を捨てるとメンテナンス負担が大きく、価値に見合わない

## 4. 進め方（Epic + Sub-issues）

GitHub の **Sub-issue 機能**で Epic 1 + 子 Issue 10 を紐付け、Project 8 の
`Parent issue` / `Sub-issues progress` フィールドで進捗を集計する。

### 4.1 Phase 1 — 基盤トークン

| # | タイトル | 主な変更 |
|---|---|---|
| 1 | トークン: 色パレット定義と CSS 変数置換 | `globals.css` の HSL 変数を再編。デジタル庁準拠スケール (`--color-primary-50/100/.../900`) を追加。色相は現状寄せ |
| 2 | トークン: タイポグラフィ | 本文 Noto Sans JP の採用判断、`text-display-lg/md/sm` 等のスケール定義、見出し階層 |
| 3 | トークン: スペーシング・角丸・シャドウ・ブレークポイント | 既存値の整理 + デジタル庁スケールへ寄せる |
| 4 | フォーカスリング & 選択可視状態 | WCAG 1.4.11（3:1 コントラスト）を満たすリング色・オフセット、全コンポーネント反映 |

### 4.2 Phase 2 — コンポーネント刷新（既存 shadcn を再スタイル）

| # | タイトル | 主な変更 |
|---|---|---|
| 5 | Button | バリアント・サイズ・無効・ローディングの整理 |
| 6 | Input / Label / Textarea + エラー・必須・ヘルパー | `aria-invalid` / `aria-describedby` 連携、エラー文言の集中管理 |
| 7 | Select / Dropdown | デジタル庁の Combobox パターン踏襲を検討 |
| 8 | Dialog / Alert / AlertDialog | 構造・コントラスト・ESC・フォーカストラップ |
| 9 | Table / Tabs / Switch / Checkbox / Badge / Separator | 残コンポーネント一括再スタイル |

### 4.3 Phase 3 — 横断検証

| # | タイトル | 主な変更 |
|---|---|---|
| 10 | a11y 監査と修正 | axe-core を Playwright に組み込み、主要ページ（login / tilesets / features / settings）の巡回スモーク。コントラスト・キーボード操作・SR 検証 |

## 5. ラベル設計

### 5.1 新規追加（2 件）

| ラベル | 色 | 用途 |
|---|---|---|
| `area:design-system` | `#5319e7` | 本件で新設するデザイントークン・共通コンポーネント関連 |
| `a11y` | `#0e8a16` | アクセシビリティに直接関連する Issue / PR |

### 5.2 既存ラベルの流用

- `epic` — Epic Issue に付与
- `area:ui` — 全子 Issue に付与（`area:design-system` と併用）
- `tech-debt` — 全子 Issue に付与
- `enhancement` — Epic に付与
- `priority:high` — Project の Priority P1 と対応（#1, #2, #4, #10）
- `priority:medium` — Project の Priority P2 と対応（#3, #5–#9）、デフォルト

## 6. マイルストーン

| Title | Description | Due |
|---|---|---|
| `Admin UI Design System v1` | デジタル庁デザインシステム準拠への段階移行（Epic 配下） | 未設定（Phase 1 完了後に決定） |

## 7. Project 8 フィールド割当方針

### 7.1 全 Issue 共通

- **Status**: `Backlog` で起票
- **Repository**: `mopinfish/geo-base`
- **Milestone**: `Admin UI Design System v1`
- **Parent issue**: 子 Issue は Epic を親に設定

### 7.2 Issue ごとの Priority / Size

| # | Issue | Priority | Size |
|---|---|---|---|
| Epic | デザインシステム移行 Epic | P1 | XL |
| 1 | 色トークン | P1 | M |
| 2 | タイポグラフィ | P1 | M |
| 3 | スペーシング・角丸・シャドウ | P2 | S |
| 4 | フォーカスリング | P1 | S |
| 5 | Button | P2 | M |
| 6 | Input/Label/Textarea/Error | P2 | L |
| 7 | Select/Dropdown | P2 | M |
| 8 | Dialog/Alert/AlertDialog | P2 | M |
| 9 | Table/Tabs/Switch/Checkbox/Badge/Separator | P2 | M |
| 10 | a11y 監査 | P1 | L |

方針メモ:

- P1 = 基盤系（#1, #2, #4）と最終ゲート（#10）。これらの遅延が全体を止める
- P0 は使わない（本番障害クラスを社内予約）
- Size XS は使わない（最小 S）
- Estimate / Start date / Target date は空で起票し運用しながら埋める

## 8. Issue テンプレート

### 8.1 Epic Issue

```markdown
## 背景・目的

`app/`（Admin UI）のフロントエンドを **デジタル庁デザインシステム**
（https://design.digital.go.jp/）に準拠させる段階移行。
shadcn/ui を土台として残しつつ、トークン・フォーム規約・a11y
の3軸で「公的サービスのデザイン水準」へ寄せる。

## ゴール

- デザイントークンがデジタル庁準拠で `globals.css` に整理されている
- フォーム共通部品がデジタル庁ガイドラインに準拠
- WCAG 2.1 AA 相当の a11y 監査をパス

## 非ゴール（明示）

- 色のテイスト・情報設計・各種ボタン配置は **現状を踏襲**
- shadcn/ui を別ライブラリに置き換えない
- ページ単位の UX/IA 改修は本 Epic のスコープ外

## サブ Issue（Sub-issues）

- [ ] #1 トークン: 色パレット
- [ ] #2 トークン: タイポグラフィ
- [ ] #3 トークン: スペーシング/角丸/シャドウ
- [ ] #4 フォーカスリング & 選択可視状態
- [ ] #5 Button
- [ ] #6 Input/Label/Textarea + エラー・必須・ヘルパー
- [ ] #7 Select/Dropdown
- [ ] #8 Dialog/Alert/AlertDialog
- [ ] #9 Table/Tabs/Switch/Checkbox/Badge/Separator
- [ ] #10 a11y 監査と修正

## 受入条件

- [ ] 全サブ Issue がクローズ
- [ ] a11y 監査（axe-core + 手動キーボード/SR テスト）がパス
- [ ] 主要ページ（login / tilesets / features / settings）の
      ビフォーアフター比較スクショが PR に添付されている
- [ ] 本 spec の "完了" セクションが更新されている
```

### 8.2 子 Issue（共通フォーマット）

```markdown
## 背景

（この Issue が Epic のどこを担うか、1〜2 段落）

## スコープ

- 含む: ...
- 含まない: ...

## 変更ファイル（想定）

- `app/src/app/globals.css`
- `app/src/components/ui/<対象>.tsx`
- `app/src/lib/...`

## 実装ノート

（3〜5 行: 設計判断、参照仕様、注意点）

## 受入条件

- [ ] 既存ユニットテスト（Vitest）が pass
- [ ] `npm run lint` が pass
- [ ] `npm run build` が pass
- [ ] 主要ページで視覚的回帰がないことを目視確認（スクショ添付）
- [ ] （該当する場合）axe-core で当該コンポーネントに新規違反なし

## 関連

- Parent: #<Epic 番号>
- 参考: https://design.digital.go.jp/components/<該当>
```

### 8.3 個別 Issue の実装ノート（要旨）

- **#1 色パレット**: 既存 HSL 変数を保持しつつ、デジタル庁準拠の `--color-primary-50/100/.../900` 等のスケールを追加。`primary` の色相は現状寄せ
- **#2 タイポグラフィ**: 本文に Noto Sans JP を採用判断（Vercel 配信コストを事前確認）。`<h1>〜<h4>` に対応する `text-display-lg/md/sm` 等を定義
- **#4 フォーカスリング**: WCAG 1.4.11（3:1 コントラスト）を満たすリング色とオフセットを `--ring` で定義し、全コンポーネントに反映
- **#6 Input/Label/Error**: `aria-invalid`, `aria-describedby` の連携を必須化。エラー文言は `<Form.Message>` 系で集中管理
- **#10 a11y 監査**: axe-core を Playwright に組み込み、`/login`, `/tilesets`, `/features`, `/settings` を巡回するスモークテストを追加

## 9. リスクと対策

| リスク | 対策 |
|---|---|
| デジタル庁 DS 側にライセンス記載が現時点でない | Issue 起票前に再確認。商用利用が不明なら "参考" 扱いに留め、独自実装する |
| Noto Sans JP の Vercel 配信コスト | #2 で計測。許容外なら `next/font` のサブセット化、または `font-display: swap` で吸収 |
| 視覚的回帰の見落とし | 各子 Issue でビフォーアフター比較スクショを必須化。将来的に Visual Regression テスト導入を検討（本 Epic 外） |
| Phase 2 の PR が肥大化 | 子 Issue の Size を見直し、必要なら更に分割（例: #6 → Input + Label / Textarea / Error の 3 分割） |

## 10. 完了

（各 Phase 完了時に追記）

- Phase 1 完了日: TBD
- Phase 2 完了日: TBD
- Phase 3 完了日: TBD
- ビフォーアフター比較リンク: TBD
