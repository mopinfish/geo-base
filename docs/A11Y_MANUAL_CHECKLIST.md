# Admin UI 手動 a11y チェックリスト

> Issue #100 (Phase 3 a11y 監査) の受入条件のうち、**axe-core では検出できない領域** をカバーする手動テスト項目。
>
> axe-core spec によるカバレッジは `app/tests/e2e/a11y/` に整備済み (PR #130 / #133 で 6 ページ完成)。本ドキュメントは:
> 1. **キーボード操作** (Tab / Shift+Tab / Enter / Esc / 矢印キー)
> 2. **screen reader (SR) 読み上げ** (VoiceOver / NVDA)
>
> を 6 ページごとに実機検証するためのテンプレ。

## 共通の前提

- ローカル開発環境で `npm run dev` を起動し、`http://localhost:3000` で実施
- ログインは admin user で行う (login spec の admin@example.com 等、`tests/e2e/utils/session.ts` 参照)
- **キーボードのみで操作** (マウス使わない)
- VoiceOver (macOS): Cmd+F5 で起動 / 終了。Ctrl+Option+→ で次の要素読み上げ
- NVDA (Windows): 起動後、NVDA キー (CapsLock or Insert) + 矢印で読み上げ

## ページ別チェック項目

### A. `/` (ダッシュボード)

#### A-1. キーボード操作
- [ ] Tab で sidebar → header → main の順に focus が移動する
- [ ] Sidebar の各 nav 項目 (ダッシュボード / タイルセット / フィーチャー / データソース / チーム / API キー / 設定) に Tab で到達可能
- [ ] Sidebar の active 状態 (現在ページ) が visible focus ring で見える
- [ ] `LanguageSwitcher` (地球儀アイコン) に Tab で到達 → Enter で開く → 矢印キーで項目選択 → Enter で確定 → Esc で閉じる
- [ ] LogOut ボタンに Tab で到達可能、Enter で動作

#### A-2. SR 読み上げ
- [ ] LanguageSwitcher の trigger ボタンが「言語を切り替える、ボタン」のように読まれる (`aria-label` 効いている)
- [ ] `EN` / `JA` ラベルが視覚補助以外で読まれる
- [ ] dashboard の counts (tilesets/features/datasources) が「タイルセット 3 件」のように読まれる (placeholder の "-" は読まない)
- [ ] sidebar の active 項目が `aria-current="page"` で読まれる

---

### B. `/tilesets` (一覧)

#### B-1. キーボード操作
- [ ] 「新規作成」ボタンに Tab で到達 → Enter で `/tilesets/new` へ遷移
- [ ] 検索 input に Tab で到達 → 文字入力できる
- [ ] type filter / public filter の Select に Tab で到達 → Enter or Space で開く → 矢印で選択 → Enter で確定
- [ ] table 内の各 row (checkbox / リンク / 操作アイコン) に Tab で順に到達できる
- [ ] 一括削除ダイアログ: 開いたら Esc で閉じる、Tab で Cancel / Delete を行き来できる

#### B-2. SR 読み上げ
- [ ] icon-only ボタン (View / Edit) が「詳細、ボタン」「編集、ボタン」のように読まれる (`aria-label` 効いている)
- [ ] table のヘッダ行 (名前 / タイプ / フォーマット / 公開 / 更新日 / 操作) が列ラベルとして読まれる
- [ ] 公開 / 非公開バッジが読まれる
- [ ] 一括選択数 (`5件を選択中` 等) が読まれる

---

### C. `/settings/profile`

#### C-1. キーボード操作
- [ ] settings nav の「プロフィール」「パスワード」タブに Tab で到達 → Enter で切替
- [ ] 名前 / メールアドレスの input に Tab で到達 → 編集可能
- [ ] 「更新」ボタンに Tab で到達 → Enter で submit
- [ ] エラー / 成功表示が出たとき、focus が予期しない位置に飛ばない

#### C-2. SR 読み上げ
- [ ] 各 input が Label と紐づいて読まれる ("名前、必須、テキスト入力" 等)
- [ ] disabled 状態の button が「無効」と読まれる
- [ ] エラーメッセージが live region として読まれる (AlertCircle + テキスト)
- [ ] 成功メッセージ (`profile-success` testid) が読まれる

---

### D. `/api-keys`

#### D-1. キーボード操作
- [ ] 「新規作成」ボタンで dialog が開く
- [ ] dialog 内: name input → scopes checkboxes → expires_in_days select → submit に Tab 順
- [ ] dialog を Esc で閉じる
- [ ] 一覧の各 row の dropdown menu (3 点アイコン) に Tab で到達 → Enter で開く → 矢印で項目選択 → Enter で確定
- [ ] failed key / revoked key の状態 badge に focus が回らない (display only)

#### D-2. SR 読み上げ
- [ ] masked key (`gb_live_********`) が読まれる
- [ ] plaintext key 表示時の警告文 (`この API キーは二度と表示されません`) が live region として読まれる
- [ ] revoked / expired badge が「失効」「期限切れ」のように読まれる

---

### E. `/features`

#### E-1. キーボード操作
- [ ] tileset filter / layer filter の Select に Tab で到達 → 操作可能
- [ ] table 内の各 row に Tab で順に到達できる
- [ ] 一括選択 + 一括更新 / 削除 dialog の操作が完結する
- [ ] export button → 形式 select (GeoJSON / CSV) → ダウンロードまで完了

#### E-2. SR 読み上げ
- [ ] icon-only ボタンが `aria-label` で読まれる (※ PR-E 後の確認項目: `tilesets/page.tsx` で追加した aria-label と同じパターンが適用されているか)
- [ ] geometry type (Point / LineString / Polygon) badge が読まれる
- [ ] 一括操作ダイアログの description が読まれる

---

### F. `/teams`

#### F-1. キーボード操作
- [ ] 「新規チーム作成」ボタンで dialog が開く
- [ ] dialog: name input → slug input → 作成ボタンに Tab 順
- [ ] team card がリンクとして Tab で到達可能 (`team-card` testid)
- [ ] 空状態 (`team-empty-state`) からも「新規作成」CTA に Tab で到達

#### F-2. SR 読み上げ
- [ ] team card が「<team name>、リンク」のように読まれる
- [ ] member count / role が読まれる
- [ ] 招待リンクコピーボタンが「コピー、ボタン」のように読まれる、コピー後の確認 (`✓` icon) も SR で伝わる

---

### G. `/teams/[id]` (detail) — オプション (Phase 3g 完了後に追加)

PR-G (Phase 3g) で catalog 化されたら本セクションを実施する。

---

## 全ページ共通の最終確認

### G-1. focus visibility
- [ ] すべての focusable 要素で focus ring が明確に見える (Issue #94 で対応済みだが目視確認)
- [ ] focus ring の色 / コントラストが WCAG 2.1 AA を満たす
- [ ] focus 状態のまま page reload / 言語切替してもフォーカスが失われない (or 失われても OK な配置)

### G-2. ESC / Enter / Space の挙動
- [ ] modal / dialog はすべて Esc で閉じる
- [ ] form 内で Enter は submit、Esc は cancel に対応
- [ ] checkbox / switch は Space で toggle

### G-3. SR landmark
- [ ] `<header>` `<nav>` `<main>` の landmark が読まれる
- [ ] heading 順 (h1 → h2 → h3) が論理的 (skip しない)
- [ ] dialog open 時、focus が dialog 内にトラップされる

## 実施結果の記録方法

実施後、本 issue (#100) にコメントとして以下を貼る:

```markdown
## 手動 a11y チェック結果 (YYYY-MM-DD 実施)

- 環境: macOS 15 / Chrome 135 + VoiceOver
- 実施者: <username>

### ページ別

- /: ✓ (issue なし)
- /tilesets: ⚠ X-X で focus visibility 弱い → 別 issue 化 (#XXX)
- /settings/profile: ✓
- ...
```

録画 (Loom / screen capture) を添付できれば理想ですが、文章メモでも構いません。

## 関連リファレンス

- [WCAG 2.1 AA quick reference](https://www.w3.org/WAI/WCAG21/quickref/)
- [VoiceOver commands cheatsheet](https://www.apple.com/voiceover/info/guide/_1119.html)
- [NVDA basic shortcuts](https://www.nvaccess.org/files/nvda/documentation/userGuide.html#KeyboardCommands)
- axe-core spec: `app/tests/e2e/a11y/` (PR #130 / #133 で整備済み)
- Issue #100 受入条件: 上記 1-2 + 主要 6 ページで axe critical/serious ゼロ
