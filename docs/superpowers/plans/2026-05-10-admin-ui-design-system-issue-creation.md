# Admin UI デザインシステム移行 — Issue 起票プラン

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** spec `docs/superpowers/specs/2026-05-10-admin-ui-design-system-migration-design.md` に基づき、必要なラベル / マイルストーン / Epic Issue / 子 Issue 10 件 を GitHub に起票し、Project 8 のフィールド設定まで完了させる。

**Architecture:** GitHub の REST/GraphQL API を `gh` CLI 経由で操作する。Issue 番号は実行時に発行されるため、各タスクで取得した番号を環境変数で次タスクに引き継ぐ。Sub-issue 機能（GitHub の native 機能）で Epic と子 Issue を紐付ける。

**Tech Stack:** GitHub CLI (`gh`), GitHub REST API, GitHub Projects v2 (GraphQL)

**前提:**
- ブランチ `docs/admin-ui-design-system-spec` 上に spec ファイル
  (`docs/superpowers/specs/2026-05-10-admin-ui-design-system-migration-design.md`)
  がコミット済み（PR #89 として review 中）
- リポジトリ: `mopinfish/geo-base`、デフォルトブランチ: `develop`
- Project 8 (`mopinfish/projects/8`) は作成済み
- Project 8 のフィールド ID（**起票時点のスナップショット**・本プランで使用）:
  - Project ID: `PVT_kwHOABCFkM4BXQr_`
  - Status field: `PVTSSF_lAHOABCFkM4BXQr_zhSevlg` / Backlog: `f75ad846`
  - Priority field: `PVTSSF_lAHOABCFkM4BXQr_zhSevsw` / P1: `0a877460`, P2: `da944a9c`
  - Size field: `PVTSSF_lAHOABCFkM4BXQr_zhSevs0` / S: `f784b110`, M: `7515a9f1`, L: `817d0097`, XL: `db339eb2`

> **注:** Project の構成（フィールド追加・名称変更・選択肢の編集 / Project 自体の作り直し）で
> 上記 ID は変わり得る。再実行・流用前には以下のコマンドで最新の ID を取得して差し替えること:
> ```fish
> gh project field-list 8 --owner mopinfish --format json
> ```
> 出力される各 field の `id` と、`options[].id` を本セクションの値と照合する。

**実行時に維持する状態（環境変数）:**
- `EPIC_NUM` — Epic Issue の番号（Task 4 で設定）
- `CHILD_<N>_NUM` (N=1..10) — 子 Issue の番号（Task 5–7 で設定）
- `ITEM_EPIC` / `ITEM_<N>` — Project item ID（Task 9 で設定）

各 Task は前 Task で設定した変数を引き継ぐ前提なので、**同一シェルセッション**で順に実行する。途中で中断した場合は `gh issue list --label epic,area:design-system` 等で番号を再取得できる。

---

## Task 1: spec ブランチの push と PR 作成

**目的:** spec を develop に取り込む PR を立てる（マージは後続作業の独立判断）。

- [ ] **Step 1: 現在のブランチ確認**

```fish
git rev-parse --abbrev-ref HEAD
```

Expected: `docs/admin-ui-design-system-spec`

- [ ] **Step 2: ブランチを origin に push**

```fish
git push -u origin docs/admin-ui-design-system-spec
```

Expected: `Branch 'docs/admin-ui-design-system-spec' set up to track 'origin/docs/admin-ui-design-system-spec'.`

- [ ] **Step 3: develop 向けの PR を作成**

fish には bash の `$(...)` 形式のコマンド置換が無いため、PR 本文は一時ファイルに書き出して `--body-file` で参照する。

```fish
cat > /tmp/spec-pr-body.md <<'EOF'
## Summary

- `app/`（Admin UI）をデジタル庁デザインシステムに段階移行するための設計 spec を追加
- Epic 1 + 子 Issue 10 件、Phase 1（基盤トークン）/ Phase 2（コンポーネント刷新）/ Phase 3（a11y 監査）の構成
- 既存テイスト・配置・色相は **非ゴール（変更しない）** として明示
- 必要なラベル・マイルストーン・Project 8 のフィールド割当方針、Issue テンプレートを含む

## Test plan

- [ ] spec 内のリンクが切れていない
- [ ] Issue 起票プラン（`docs/superpowers/plans/2026-05-10-admin-ui-design-system-issue-creation.md`）と整合している
- [ ] 非ゴールの記述が要求どおり（色テイスト保持、shadcn 維持）になっている
EOF

gh pr create \
  --base develop \
  --head docs/admin-ui-design-system-spec \
  --title "docs(spec): Admin UI のデザインシステム移行設計を追加" \
  --body-file /tmp/spec-pr-body.md
```

Expected: PR URL が出力される（例: `https://github.com/mopinfish/geo-base/pull/XX`）

- [ ] **Step 4: PR URL を控える**

`SPEC_PR_URL` として控えておく（後続 Issue 本文の参照に使用）。

```fish
set -x SPEC_PR_URL (gh pr view --json url --jq .url)
echo $SPEC_PR_URL
```

---

## Task 2: 新規ラベルを 2 件作成

**目的:** spec で定義した `area:design-system` と `a11y` を作成。

- [ ] **Step 1: `area:design-system` を作成**

```fish
gh label create "area:design-system" \
  --color "5319e7" \
  --description "デザイントークン・共通コンポーネント・デザインシステム関連"
```

Expected: `✓ Label "area:design-system" created in mopinfish/geo-base`

- [ ] **Step 2: `a11y` を作成**

```fish
gh label create "a11y" \
  --color "0e8a16" \
  --description "アクセシビリティ関連"
```

Expected: `✓ Label "a11y" created in mopinfish/geo-base`

- [ ] **Step 3: 作成確認**

```fish
gh label list | grep -E "^(area:design-system|a11y)\s"
```

Expected: 2 行表示される。

- [ ] **Step 4: コミット不要（GitHub 上の操作）**

ラベル作成はリポジトリ設定操作なので git commit は発生しない。

---

## Task 3: マイルストーン `Admin UI Design System v1` を作成

- [ ] **Step 1: 既存マイルストーンを確認（重複防止）**

```fish
gh api repos/mopinfish/geo-base/milestones --jq '.[].title'
```

Expected: 空 or `Admin UI Design System v1` を含まない。

- [ ] **Step 2: マイルストーンを作成**

```fish
gh api repos/mopinfish/geo-base/milestones \
  -X POST \
  -f title="Admin UI Design System v1" \
  -f description="デジタル庁デザインシステム準拠への段階移行（Epic 配下）。Due は Phase 1 完了後に決定。" \
  -f state=open
```

Expected: JSON が返り、`"number": N` が含まれる。

- [ ] **Step 3: マイルストーン番号を変数に格納**

```fish
set -x MILESTONE_NUM (gh api repos/mopinfish/geo-base/milestones --jq '.[] | select(.title=="Admin UI Design System v1") | .number')
echo $MILESTONE_NUM
```

Expected: 整数（例: `1`）。

---

## Task 4: Epic Issue を作成

**目的:** Epic Issue を立て、`EPIC_NUM` を環境変数に設定。

- [ ] **Step 1: Epic 本文を一時ファイルに用意**

```fish
cat > /tmp/epic-body.md <<'EOF'
## 背景・目的

`app/`（Admin UI）のフロントエンドを **デジタル庁デザインシステム**
（https://design.digital.go.jp/）に準拠させる段階移行。
shadcn/ui を土台として残しつつ、トークン・フォーム規約・a11y
の3軸で「公的サービスのデザイン水準」へ寄せる。

## ゴール

- デザイントークン（色 / タイポ / スペーシング / フォーカス）が
  デジタル庁準拠で `globals.css` に整理されている
- フォーム共通部品（Label / Input / Textarea / Select / エラー / 必須）が
  デジタル庁ガイドラインに準拠
- WCAG 2.1 AA 相当の a11y 監査をパス（コントラスト・キーボード操作・SR 検証）

## 非ゴール（明示）

- 色のテイスト・情報設計・各種ボタン配置は **現状を踏襲**
  （ブランドカラーを丸ごとデジタル庁ブルーに置き換える等はしない）
- shadcn/ui を別ライブラリに置き換えない
- ページ単位の UX/IA 改修（情報整理）は本 Epic のスコープ外
- API / MCP / DB 側への変更は含まない

## サブ Issue（Sub-issues）

子 Issue は GitHub の Sub-issue 機能で本 Epic に紐付く（起票後に追加）。

- [ ] Phase 1 #1 トークン: 色パレット
- [ ] Phase 1 #2 トークン: タイポグラフィ
- [ ] Phase 1 #3 トークン: スペーシング/角丸/シャドウ
- [ ] Phase 1 #4 フォーカスリング & 選択可視状態
- [ ] Phase 2 #5 Button
- [ ] Phase 2 #6 Input/Label/Textarea + エラー・必須・ヘルパー
- [ ] Phase 2 #7 Select/Dropdown
- [ ] Phase 2 #8 Dialog/Alert/AlertDialog
- [ ] Phase 2 #9 Table/Tabs/Switch/Checkbox/Badge/Separator
- [ ] Phase 3 #10 a11y 監査と修正

## 受入条件

- [ ] 全サブ Issue がクローズ
- [ ] a11y 監査（axe-core + 手動キーボード/SR テスト）がパス
- [ ] 主要ページ（login / tilesets / features / settings）の
      ビフォーアフター比較スクショが PR に添付されている
- [ ] spec の "完了" セクションが更新されている

## 関連

- spec: `docs/superpowers/specs/2026-05-10-admin-ui-design-system-migration-design.md`
- spec PR: <SPEC_PR_URL>
- 参考: https://design.digital.go.jp/
EOF

# spec PR URL を本文に差し込む
sed -i.bak "s|<SPEC_PR_URL>|$SPEC_PR_URL|g" /tmp/epic-body.md && rm /tmp/epic-body.md.bak
```

- [ ] **Step 2: Epic Issue を作成し URL を取得**

`gh issue create` は URL を 1 行で返す（JSON フラグは無い）。

```fish
set EPIC_URL (gh issue create \
  --title "Admin UI: デジタル庁デザインシステム準拠への段階移行（Epic）" \
  --body-file /tmp/epic-body.md \
  --label "epic,area:ui,area:design-system,enhancement,priority:high" \
  --milestone "Admin UI Design System v1")
echo "EPIC_URL=$EPIC_URL"
```

Expected: `EPIC_URL` に `https://github.com/mopinfish/geo-base/issues/<番号>` が入る。

- [ ] **Step 3: Epic 番号を環境変数に格納**

URL の末尾要素が Issue 番号。

```fish
set -x EPIC_NUM (basename $EPIC_URL)
echo "EPIC_NUM=$EPIC_NUM"
```

Expected: 整数（Epic Issue 番号）。

---

## Task 5: Phase 1 子 Issue（#1〜#4）を作成

**目的:** 基盤トークン Issue 4 件を作成し `CHILD_1_NUM` 〜 `CHILD_4_NUM` を設定。

- [ ] **Step 1: #1 色トークン**

```fish
cat > /tmp/issue-1.md <<EOF
## 背景

\`app/\` の Admin UI は HSL の CSS 変数で配色管理されている (\`baseColor: neutral\`)。
Epic #$EPIC_NUM の Phase 1 として、デジタル庁デザインシステム準拠の色スケールを導入する。
ただし現状の色テイストは保持する（spec の非ゴール参照）。

## スコープ

- 含む:
  - \`globals.css\` に \`--color-primary-50/100/.../900\` 等のスケール変数を追加
  - 既存 \`--primary\` / \`--secondary\` / \`--accent\` の HSL 値を新スケールから派生させる
  - ライト/ダーク両モードでマッピング
- 含まない:
  - 個別コンポーネントの再スタイル（後続 Issue で実施）
  - フォント/タイポグラフィ（#2 で対応）

## 変更ファイル（想定）

- \`app/src/app/globals.css\`

## 実装ノート

既存 HSL 変数を保持しつつ、デジタル庁準拠の \`--color-primary-50/.../900\` 等のスケールを追加。
\`primary\` の色相は現状寄せ（neutral 系の色相を保つ）。
shadcn の \`@theme inline\` ブロックに新スケール変数のエイリアスを追加して
Tailwind v4 のクラスから参照可能にする。

## 受入条件

- [ ] 既存ユニットテスト（Vitest）が pass
- [ ] \`npm run lint\` が pass
- [ ] \`npm run build\` が pass
- [ ] 主要ページ（login / tilesets / features / settings）で視覚的回帰がないことを目視確認（スクショ添付）

## 関連

- Parent: #$EPIC_NUM
- spec: \`docs/superpowers/specs/2026-05-10-admin-ui-design-system-migration-design.md\`
- 参考: https://design.digital.go.jp/foundations/colors
EOF

set CHILD_1_URL (gh issue create \
  --title "Phase 1 #1 トークン: 色パレット定義と CSS 変数置換" \
  --body-file /tmp/issue-1.md \
  --label "area:ui,area:design-system,tech-debt,priority:high" \
  --milestone "Admin UI Design System v1")
set -x CHILD_1_NUM (basename $CHILD_1_URL)
echo "CHILD_1_NUM=$CHILD_1_NUM"
```

- [ ] **Step 2: #2 タイポグラフィ**

```fish
cat > /tmp/issue-2.md <<EOF
## 背景

Epic #$EPIC_NUM の Phase 1。デジタル庁デザインシステムのタイポグラフィ規約（見出し階層・本文スケール）に揃える。

## スコープ

- 含む:
  - 本文フォントの選定（Noto Sans JP の採用判断、配信コスト確認込み）
  - \`text-display-lg/md/sm\` 等のスケール定義（または Tailwind v4 \`@theme\` への登録）
  - \`<h1>〜<h4>\` に対応する見出し階層を CSS で確立
  - 行間・letter-spacing の整理
- 含まない:
  - 個別ページの見出し書き換え（必要なら別 Issue）

## 変更ファイル（想定）

- \`app/src/app/layout.tsx\`（フォント設定）
- \`app/src/app/globals.css\`
- 必要なら \`next/font\` 設定

## 実装ノート

\`next/font\` で Noto Sans JP を導入する場合は \`subsets\` を絞ること（ファイルサイズ）。
許容外なら \`font-display: swap\` で吸収するか、見送り（spec のリスク参照）。

## 受入条件

- [ ] 既存ユニットテスト（Vitest）が pass
- [ ] \`npm run lint\` が pass
- [ ] \`npm run build\` が pass
- [ ] 主要ページで視覚的回帰がないことを目視確認（スクショ添付）
- [ ] フォント切替後の Lighthouse スコア（Performance）に大きな悪化がない

## 関連

- Parent: #$EPIC_NUM
- spec: \`docs/superpowers/specs/2026-05-10-admin-ui-design-system-migration-design.md\`
- 参考: https://design.digital.go.jp/foundations/typography
EOF

set CHILD_2_URL (gh issue create \
  --title "Phase 1 #2 トークン: タイポグラフィ" \
  --body-file /tmp/issue-2.md \
  --label "area:ui,area:design-system,tech-debt,priority:high" \
  --milestone "Admin UI Design System v1")
set -x CHILD_2_NUM (basename $CHILD_2_URL)
echo "CHILD_2_NUM=$CHILD_2_NUM"
```

- [ ] **Step 3: #3 スペーシング・角丸・シャドウ**

```fish
cat > /tmp/issue-3.md <<EOF
## 背景

Epic #$EPIC_NUM の Phase 1。スペーシング/角丸/シャドウ/ブレークポイントをデジタル庁準拠に整える。

## スコープ

- 含む:
  - \`globals.css\` の \`--radius\` 系、シャドウトークンの整理
  - スペーシングスケール（4/8/12/16/24...）の見直し
  - ブレークポイントの整合確認
- 含まない:
  - 個別コンポーネントのレイアウト変更

## 変更ファイル（想定）

- \`app/src/app/globals.css\`

## 実装ノート

既存値からの差分が大きい場合は、暫定的にエイリアス変数を残して段階移行できるようにする。
シャドウは "elevation" の段階（0/1/2/3）で揃えるとデジタル庁準拠と一致しやすい。

## 受入条件

- [ ] 既存ユニットテスト（Vitest）が pass
- [ ] \`npm run lint\` が pass
- [ ] \`npm run build\` が pass
- [ ] 主要ページで視覚的回帰がないことを目視確認（スクショ添付）

## 関連

- Parent: #$EPIC_NUM
- spec: \`docs/superpowers/specs/2026-05-10-admin-ui-design-system-migration-design.md\`
EOF

set CHILD_3_URL (gh issue create \
  --title "Phase 1 #3 トークン: スペーシング・角丸・シャドウ・ブレークポイント" \
  --body-file /tmp/issue-3.md \
  --label "area:ui,area:design-system,tech-debt,priority:medium" \
  --milestone "Admin UI Design System v1")
set -x CHILD_3_NUM (basename $CHILD_3_URL)
echo "CHILD_3_NUM=$CHILD_3_NUM"
```

- [ ] **Step 4: #4 フォーカスリング**

```fish
cat > /tmp/issue-4.md <<EOF
## 背景

Epic #$EPIC_NUM の Phase 1。WCAG 1.4.11（非テキスト要素のコントラスト 3:1）を満たすフォーカスリングを定義し、全コンポーネントに反映する。a11y 系のため P1。

## スコープ

- 含む:
  - \`--ring\` 色、リング幅、オフセットの定義
  - キーボードフォーカス時のみ表示する制御（\`:focus-visible\`）
  - 全 shadcn コンポーネントの \`focus-visible\` クラスを統一
- 含まない:
  - 個別コンポーネントの見た目刷新（後続 Issue で）

## 変更ファイル（想定）

- \`app/src/app/globals.css\`
- \`app/src/components/ui/*.tsx\`（focus 系クラスの統一）

## 実装ノート

\`focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--ring)]\` のような
ユーティリティを共通化する。リング色は WCAG 1.4.11 を満たすコントラストで選定。

## 受入条件

- [ ] 既存ユニットテスト（Vitest）が pass
- [ ] \`npm run lint\` が pass
- [ ] \`npm run build\` が pass
- [ ] 主要フォーム要素のキーボードフォーカスがすべて視認可能（手動確認 / スクショ添付）
- [ ] axe-core でフォーカス関連の新規違反なし

## 関連

- Parent: #$EPIC_NUM
- spec: \`docs/superpowers/specs/2026-05-10-admin-ui-design-system-migration-design.md\`
- 参考: WCAG 2.1 SC 1.4.11, 2.4.7
EOF

set CHILD_4_URL (gh issue create \
  --title "Phase 1 #4 フォーカスリング & 選択可視状態" \
  --body-file /tmp/issue-4.md \
  --label "area:ui,area:design-system,a11y,tech-debt,priority:high" \
  --milestone "Admin UI Design System v1")
set -x CHILD_4_NUM (basename $CHILD_4_URL)
echo "CHILD_4_NUM=$CHILD_4_NUM"
```

- [ ] **Step 5: 確認**

```fish
echo "Phase 1 issues: #$CHILD_1_NUM #$CHILD_2_NUM #$CHILD_3_NUM #$CHILD_4_NUM"
gh issue list --label area:design-system --milestone "Admin UI Design System v1" --json number,title
```

Expected: 5 件（Epic + Phase 1 の 4 件）。

---

## Task 6: Phase 2 子 Issue（#5〜#9）を作成

- [ ] **Step 1: #5 Button**

```fish
cat > /tmp/issue-5.md <<EOF
## 背景

Epic #$EPIC_NUM の Phase 2。shadcn/ui の Button コンポーネントをデジタル庁ガイドライン準拠で再スタイル。

## スコープ

- 含む:
  - バリアント整理（primary / secondary / outline / ghost / destructive / link）
  - サイズ（sm / md / lg）
  - 無効状態 / ローディング状態のスタイルとアクセシブルな表現
- 含まない:
  - Button 以外のフォーム要素（#6 で対応）

## 変更ファイル（想定）

- \`app/src/components/ui/button.tsx\`
- 関連する利用箇所（必要なら）

## 実装ノート

ローディング状態は \`aria-busy\` を併用し、テキストではなく状態として SR に伝える。
無効状態は \`disabled\` 属性 + 視覚的にコントラストを十分確保（WCAG 1.4.3）。

## 受入条件

- [ ] 既存ユニットテスト（Vitest）が pass
- [ ] \`npm run lint\` / \`npm run build\` が pass
- [ ] 主要ページで視覚的回帰がないことを目視確認（スクショ添付）
- [ ] axe-core で Button に関連する新規違反なし

## 関連

- Parent: #$EPIC_NUM
- 参考: https://design.digital.go.jp/components/button
EOF

set CHILD_5_URL (gh issue create \
  --title "Phase 2 #5 Button 再スタイル" \
  --body-file /tmp/issue-5.md \
  --label "area:ui,area:design-system,tech-debt,priority:medium" \
  --milestone "Admin UI Design System v1")
set -x CHILD_5_NUM (basename $CHILD_5_URL)
echo "CHILD_5_NUM=$CHILD_5_NUM"
```

- [ ] **Step 2: #6 Input/Label/Textarea + エラー**

```fish
cat > /tmp/issue-6.md <<EOF
## 背景

Epic #$EPIC_NUM の Phase 2。フォーム共通部品をデジタル庁ガイドライン準拠で整備。
画面横断の影響範囲が広く Size L。

## スコープ

- 含む:
  - Input / Label / Textarea のスタイルと a11y 関連属性
  - エラー表示の標準化（\`aria-invalid\` / \`aria-describedby\` の連携）
  - 必須マーク（視覚 + SR）
  - ヘルパーテキストパターン
- 含まない:
  - Select / Combobox（#7 で対応）

## 変更ファイル（想定）

- \`app/src/components/ui/input.tsx\`
- \`app/src/components/ui/label.tsx\`
- \`app/src/components/ui/textarea.tsx\`
- 必要なら \`app/src/components/ui/form.tsx\`（新規）

## 実装ノート

\`aria-invalid\`, \`aria-describedby\` の連携を必須化。エラー文言は \`<Form.Message>\` 系で集中管理し、
\`react-hook-form\` の zod resolver と整合する形にする。
必須マークは \`<abbr title="必須" aria-hidden="true">*</abbr>\` + 視覚的 \`required\` 属性で SR にも伝える。

## 受入条件

- [ ] 既存ユニットテスト（Vitest）が pass
- [ ] \`npm run lint\` / \`npm run build\` が pass
- [ ] 主要フォーム（login / settings/profile / settings/password / tilesets/new / features/new）で視覚的回帰がないことを目視確認（スクショ添付）
- [ ] axe-core でフォーム関連の新規違反なし

## 関連

- Parent: #$EPIC_NUM
- 参考: https://design.digital.go.jp/components/textfield
EOF

set CHILD_6_URL (gh issue create \
  --title "Phase 2 #6 Input/Label/Textarea + エラー・必須マーク・ヘルパーテキスト" \
  --body-file /tmp/issue-6.md \
  --label "area:ui,area:design-system,a11y,tech-debt,priority:medium" \
  --milestone "Admin UI Design System v1")
set -x CHILD_6_NUM (basename $CHILD_6_URL)
echo "CHILD_6_NUM=$CHILD_6_NUM"
```

- [ ] **Step 3: #7 Select/Dropdown**

```fish
cat > /tmp/issue-7.md <<EOF
## 背景

Epic #$EPIC_NUM の Phase 2。Select / Dropdown 系コンポーネントをデジタル庁ガイドライン準拠で再スタイル。Combobox パターン採用は本 Issue で判断。

## スコープ

- 含む:
  - \`select.tsx\` / \`dropdown-menu.tsx\` の再スタイル
  - キーボード操作（矢印キー / Enter / Esc）の検証
  - 必要に応じて Combobox 実装の追加検討（YAGNI 判断）
- 含まない:
  - 他のフォーム要素

## 変更ファイル（想定）

- \`app/src/components/ui/select.tsx\`
- \`app/src/components/ui/dropdown-menu.tsx\`

## 実装ノート

Radix UI の \`Select\` は a11y 実装が堅いのでベースは維持し、見た目のみ調整する。
Combobox 採用は影響範囲（既存利用箇所の改修コスト）と便益を見て判断。

## 受入条件

- [ ] 既存ユニットテスト（Vitest）が pass
- [ ] \`npm run lint\` / \`npm run build\` が pass
- [ ] 主要ページで視覚的回帰がないことを目視確認（スクショ添付）
- [ ] キーボード操作で Select / Dropdown が問題なく操作できる
- [ ] axe-core で関連の新規違反なし

## 関連

- Parent: #$EPIC_NUM
- 参考: https://design.digital.go.jp/components/combobox
EOF

set CHILD_7_URL (gh issue create \
  --title "Phase 2 #7 Select / Dropdown" \
  --body-file /tmp/issue-7.md \
  --label "area:ui,area:design-system,a11y,tech-debt,priority:medium" \
  --milestone "Admin UI Design System v1")
set -x CHILD_7_NUM (basename $CHILD_7_URL)
echo "CHILD_7_NUM=$CHILD_7_NUM"
```

- [ ] **Step 4: #8 Dialog/Alert/AlertDialog**

```fish
cat > /tmp/issue-8.md <<EOF
## 背景

Epic #$EPIC_NUM の Phase 2。モーダル系（Dialog / Alert / AlertDialog）の構造とコントラストを整える。

## スコープ

- 含む:
  - Dialog / Alert / AlertDialog の再スタイル
  - フォーカストラップ・ESC で閉じる動作の確認
  - 背景オーバーレイのコントラスト
  - スクロール可能領域の挙動
- 含まない:
  - Toast / Notification（既存に存在しないため）

## 変更ファイル（想定）

- \`app/src/components/ui/dialog.tsx\`
- \`app/src/components/ui/alert.tsx\`
- \`app/src/components/ui/alert-dialog.tsx\`

## 実装ノート

Radix の Dialog はフォーカストラップを内蔵しているため、見た目のみ調整。
\`AlertDialog\` の destructive アクションは色とラベルでリスクを明示する。

## 受入条件

- [ ] 既存ユニットテスト（Vitest）が pass
- [ ] \`npm run lint\` / \`npm run build\` が pass
- [ ] 主要モーダル発火箇所（API キー作成、tileset 削除確認等）で視覚的回帰がないことを目視確認（スクショ添付）
- [ ] ESC キーで閉じる、フォーカストラップが効く、を手動確認
- [ ] axe-core で関連の新規違反なし

## 関連

- Parent: #$EPIC_NUM
EOF

set CHILD_8_URL (gh issue create \
  --title "Phase 2 #8 Dialog / Alert / AlertDialog" \
  --body-file /tmp/issue-8.md \
  --label "area:ui,area:design-system,a11y,tech-debt,priority:medium" \
  --milestone "Admin UI Design System v1")
set -x CHILD_8_NUM (basename $CHILD_8_URL)
echo "CHILD_8_NUM=$CHILD_8_NUM"
```

- [ ] **Step 5: #9 Table 他残コンポーネント**

```fish
cat > /tmp/issue-9.md <<EOF
## 背景

Epic #$EPIC_NUM の Phase 2 最後。残りの shadcn コンポーネントを一括で再スタイル。

## スコープ

- 含む:
  - Table（見出し / 行 / ソート / 選択 / 空状態）
  - Tabs / Switch / Checkbox / Badge / Separator
- 含まない:
  - DataGrid 化や仮想スクロール導入（YAGNI / Epic スコープ外）

## 変更ファイル（想定）

- \`app/src/components/ui/table.tsx\`
- \`app/src/components/ui/tabs.tsx\`
- \`app/src/components/ui/switch.tsx\`
- \`app/src/components/ui/checkbox.tsx\`
- \`app/src/components/ui/badge.tsx\`
- \`app/src/components/ui/separator.tsx\`

## 実装ノート

Table の空状態は \`<caption>\` または十分なメッセージブロックで明示。
Switch / Checkbox はラベルとの関連を \`<label htmlFor>\` で必ず張る（既に shadcn が対応済みのはずだが確認）。

## 受入条件

- [ ] 既存ユニットテスト（Vitest）が pass
- [ ] \`npm run lint\` / \`npm run build\` が pass
- [ ] 主要ページ（tilesets / features / api-keys）で視覚的回帰がないことを目視確認（スクショ添付）
- [ ] axe-core で関連の新規違反なし

## 関連

- Parent: #$EPIC_NUM
EOF

set CHILD_9_URL (gh issue create \
  --title "Phase 2 #9 Table / Tabs / Switch / Checkbox / Badge / Separator" \
  --body-file /tmp/issue-9.md \
  --label "area:ui,area:design-system,tech-debt,priority:medium" \
  --milestone "Admin UI Design System v1")
set -x CHILD_9_NUM (basename $CHILD_9_URL)
echo "CHILD_9_NUM=$CHILD_9_NUM"
```

- [ ] **Step 6: 確認**

```fish
echo "Phase 2 issues: #$CHILD_5_NUM #$CHILD_6_NUM #$CHILD_7_NUM #$CHILD_8_NUM #$CHILD_9_NUM"
```

Expected: 5 個の番号が表示される。

---

## Task 7: Phase 3 子 Issue（#10）を作成

- [ ] **Step 1: #10 a11y 監査**

```fish
cat > /tmp/issue-10.md <<EOF
## 背景

Epic #$EPIC_NUM の Phase 3 / 最終ゲート。Phase 1〜2 の成果を a11y 観点で総点検し、残課題を修正する。

## スコープ

- 含む:
  - axe-core を Playwright に組み込み、主要ページを巡回するスモークテストを追加
  - 手動キーボード操作テスト（Tab / Shift+Tab / Enter / Esc / 矢印キー）
  - 主要 SR（VoiceOver / NVDA のいずれか）での読み上げ検証
  - WCAG 2.1 AA 違反の修正
- 含まない:
  - WCAG AAA 対応
  - 新機能の追加

## 変更ファイル（想定）

- \`app/tests/a11y/*.spec.ts\`（新規、Playwright + axe-core）
- \`app/package.json\`（@axe-core/playwright 等の依存追加）
- 必要に応じて \`app/src/components/ui/*\` への修正

## 実装ノート

巡回対象: \`/login\`, \`/tilesets\`, \`/features\`, \`/settings\`, \`/api-keys\`, \`/teams\`。
axe-core の重大度 \`critical\` / \`serious\` を fail 条件にし、\`moderate\` 以下は warn 扱い。
既存の Vitest（単体テスト）とは別ディレクトリで分離する。

## 受入条件

- [ ] Playwright + axe-core のテスト基盤が \`app/\` に追加されている
- [ ] 主要 6 ページで axe-core の \`critical\` / \`serious\` 違反がゼロ
- [ ] 主要フォーム（login / tilesets/new / features/new）の手動キーボード操作が一通り通る
- [ ] SR で各ページの主要要素が適切に読み上げられる（録画 or メモを PR に添付）

## 関連

- Parent: #$EPIC_NUM
- 参考: https://www.w3.org/WAI/WCAG21/quickref/
EOF

set CHILD_10_URL (gh issue create \
  --title "Phase 3 #10 a11y 監査と修正" \
  --body-file /tmp/issue-10.md \
  --label "area:ui,area:design-system,a11y,tech-debt,test,priority:high" \
  --milestone "Admin UI Design System v1")
set -x CHILD_10_NUM (basename $CHILD_10_URL)
echo "CHILD_10_NUM=$CHILD_10_NUM"
```

- [ ] **Step 2: 全 Issue の番号を整理**

```fish
echo "Epic: #$EPIC_NUM"
echo "Children: #$CHILD_1_NUM #$CHILD_2_NUM #$CHILD_3_NUM #$CHILD_4_NUM #$CHILD_5_NUM #$CHILD_6_NUM #$CHILD_7_NUM #$CHILD_8_NUM #$CHILD_9_NUM #$CHILD_10_NUM"
```

Expected: Epic 1 件 + 子 10 件、計 11 件。

---

## Task 8: 子 Issue を Epic の Sub-issue として紐付け

**目的:** GitHub の native Sub-issue 機能で 10 件を Epic に紐付ける。

- [ ] **Step 1: Epic と各子 Issue の database id を取得**

GitHub の Sub-issue API は **issue の database id (REST `id`)** を要求する（issue number ではない）。

```fish
set -x EPIC_DBID (gh api repos/mopinfish/geo-base/issues/$EPIC_NUM --jq .id)

set -e CHILD_DBIDS
for n in $CHILD_1_NUM $CHILD_2_NUM $CHILD_3_NUM $CHILD_4_NUM $CHILD_5_NUM $CHILD_6_NUM $CHILD_7_NUM $CHILD_8_NUM $CHILD_9_NUM $CHILD_10_NUM
  set -a CHILD_DBIDS (gh api repos/mopinfish/geo-base/issues/$n --jq .id)
end

echo "EPIC_DBID=$EPIC_DBID"
echo "CHILD_DBIDS=$CHILD_DBIDS"
```

Expected: `EPIC_DBID` は整数、`CHILD_DBIDS` は 10 個の整数。

- [ ] **Step 2: 各子 Issue を Epic の Sub-issue として登録**

```fish
for dbid in $CHILD_DBIDS
  gh api -X POST "repos/mopinfish/geo-base/issues/$EPIC_NUM/sub_issues" \
    -F sub_issue_id=$dbid
  echo "Linked sub_issue_id=$dbid"
end
```

Expected: 10 回成功レスポンス（JSON が返る）。

> **注:** API が 404/422 の場合、Sub-issue 機能の preview header が必要なケースがある。その場合は `gh api -H "Accept: application/vnd.github+json"` 等で再試行。

- [ ] **Step 3: Epic ページで Sub-issues セクションを目視確認**

```fish
gh issue view $EPIC_NUM --web
```

Expected: ブラウザで Epic を開き、"Sub-issues" セクションに 10 件が表示されている。

---

## Task 9: 全 Issue を Project 8 に追加し Project item ID を取得

- [ ] **Step 1: Epic を Project 8 に追加**

```fish
set -x ITEM_EPIC (gh project item-add 8 --owner mopinfish \
  --url (gh issue view $EPIC_NUM --json url --jq .url) \
  --format json --jq .id)
echo "ITEM_EPIC=$ITEM_EPIC"
```

Expected: `PVTI_*` の項目 ID。

- [ ] **Step 2: 各子 Issue を Project 8 に追加**

```fish
set -e ITEM_CHILDREN
for n in $CHILD_1_NUM $CHILD_2_NUM $CHILD_3_NUM $CHILD_4_NUM $CHILD_5_NUM $CHILD_6_NUM $CHILD_7_NUM $CHILD_8_NUM $CHILD_9_NUM $CHILD_10_NUM
  set -a ITEM_CHILDREN (gh project item-add 8 --owner mopinfish \
    --url (gh issue view $n --json url --jq .url) \
    --format json --jq .id)
end
echo "ITEM_CHILDREN=$ITEM_CHILDREN"
```

Expected: 10 個の `PVTI_*` ID。

---

## Task 10: Project フィールド（Status / Priority / Size）を設定

**目的:** spec § 7.2 の表に従って各 Project item にフィールド値を設定。

Project ID とフィールド ID は本プラン冒頭の前提を参照。Status は全 Issue で `Backlog`、Priority と Size は Issue ごとに異なる。

- [ ] **Step 1: ヘルパ関数を定義（同セッションで使い回し）**

```fish
function pset
    # usage: pset <ITEM_ID> <FIELD_ID> <OPTION_ID>
    gh project item-edit \
      --id $argv[1] \
      --project-id PVT_kwHOABCFkM4BXQr_ \
      --field-id $argv[2] \
      --single-select-option-id $argv[3]
end

# Field/option IDs（前提から再掲）
set -x F_STATUS PVTSSF_lAHOABCFkM4BXQr_zhSevlg
set -x O_BACKLOG f75ad846
set -x F_PRIORITY PVTSSF_lAHOABCFkM4BXQr_zhSevsw
set -x O_P1 0a877460
set -x O_P2 da944a9c
set -x F_SIZE PVTSSF_lAHOABCFkM4BXQr_zhSevs0
set -x O_S f784b110
set -x O_M 7515a9f1
set -x O_L 817d0097
set -x O_XL db339eb2
```

- [ ] **Step 2: 全 Item の Status を Backlog に**

```fish
for item in $ITEM_EPIC $ITEM_CHILDREN
  pset $item $F_STATUS $O_BACKLOG
end
```

Expected: 11 回更新成功。

- [ ] **Step 3: Priority を設定**

spec § 7.2: Epic / #1 / #2 / #4 / #10 = P1、その他 = P2。
`ITEM_CHILDREN` の並び順は #1〜#10 の順序で push してあるので、添字は 1..10。

```fish
# Epic
pset $ITEM_EPIC $F_PRIORITY $O_P1

# P1: children index 1, 2, 4, 10
for idx in 1 2 4 10
  pset $ITEM_CHILDREN[$idx] $F_PRIORITY $O_P1
end

# P2: children index 3, 5, 6, 7, 8, 9
for idx in 3 5 6 7 8 9
  pset $ITEM_CHILDREN[$idx] $F_PRIORITY $O_P2
end
```

Expected: 11 回更新成功。

- [ ] **Step 4: Size を設定**

spec § 7.2: Epic=XL、#1=M、#2=M、#3=S、#4=S、#5=M、#6=L、#7=M、#8=M、#9=M、#10=L。

```fish
# Epic
pset $ITEM_EPIC $F_SIZE $O_XL

# children
pset $ITEM_CHILDREN[1]  $F_SIZE $O_M
pset $ITEM_CHILDREN[2]  $F_SIZE $O_M
pset $ITEM_CHILDREN[3]  $F_SIZE $O_S
pset $ITEM_CHILDREN[4]  $F_SIZE $O_S
pset $ITEM_CHILDREN[5]  $F_SIZE $O_M
pset $ITEM_CHILDREN[6]  $F_SIZE $O_L
pset $ITEM_CHILDREN[7]  $F_SIZE $O_M
pset $ITEM_CHILDREN[8]  $F_SIZE $O_M
pset $ITEM_CHILDREN[9]  $F_SIZE $O_M
pset $ITEM_CHILDREN[10] $F_SIZE $O_L
```

Expected: 11 回更新成功。

---

## Task 11: 検証

- [ ] **Step 1: ラベル確認**

```fish
gh label list | grep -E "^(area:design-system|a11y)\s"
```

Expected: 2 行（手順 2 で作成した 2 ラベル）。

- [ ] **Step 2: マイルストーン配下の Issue 数確認**

```fish
gh issue list --milestone "Admin UI Design System v1" --state open --json number,title --jq 'length'
```

Expected: `11`（Epic 1 + 子 10）。

- [ ] **Step 3: Epic の Sub-issues 確認**

```fish
gh api repos/mopinfish/geo-base/issues/$EPIC_NUM/sub_issues --jq 'length'
```

Expected: `10`。

- [ ] **Step 4: Project 8 の登録 Item 数確認**

```fish
gh project item-list 8 --owner mopinfish --format json --jq '.items | length'
```

Expected: 既存 6 + 新規 11 = `17`（または既存値 + 11）。

- [ ] **Step 5: ブラウザで最終確認**

```fish
gh issue view $EPIC_NUM --web
open "https://github.com/users/mopinfish/projects/8"
```

確認項目:
- Epic に Sub-issues 10 件が紐づいている
- Project 8 のボードで全 11 件が `Backlog` レーンにある
- Priority / Size が spec 通りに設定されている

- [ ] **Step 6: 一時ファイルを掃除**

```fish
rm /tmp/epic-body.md /tmp/issue-{1,2,3,4,5,6,7,8,9,10}.md
```

---

## 完了条件

- [ ] Task 1: spec PR 作成完了
- [ ] Task 2: ラベル 2 件作成完了
- [ ] Task 3: マイルストーン 1 件作成完了
- [ ] Task 4: Epic Issue 作成完了
- [ ] Task 5–7: 子 Issue 10 件作成完了
- [ ] Task 8: Sub-issue 紐付け 10 件完了
- [ ] Task 9: Project item 追加 11 件完了
- [ ] Task 10: Status / Priority / Size 設定 33 アクション完了
- [ ] Task 11: 検証ステップ全てパス
