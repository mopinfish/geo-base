# GitHub Actions Node.js 24 移行 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** GitHub Actions の Node.js 20 非推奨警告を解消するため action バージョンを一括更新し、Issue #135 をクローズする。

**Architecture:** `.github/` 配下の 6 ファイル（1 composite action + 5 workflow）の action バージョンタグを一括置換する。テストは CI 自体（PR トリガーの unit-tests / e2e-smoke）で代替する。アプリが使う Node.js バージョン（20）は変更しない。

**Tech Stack:** GitHub Actions YAML。変更は sed / Edit ツールによる文字列置換のみ。

---

## 変更対象ファイルと更新バージョン一覧

| ファイル | action | 現行 | 更新後 |
|---|---|---|---|
| `.github/actions/e2e-setup/action.yml` | `actions/setup-python` | `@v5` | `@v6.2.0` |
| `.github/actions/e2e-setup/action.yml` | `astral-sh/setup-uv` | `@v3` | `@v8.1.0` |
| `.github/actions/e2e-setup/action.yml` | `actions/setup-node` | `@v4` | `@v6.4.0` |
| `.github/actions/e2e-setup/action.yml` | `actions/cache` | `@v4` | `@v5.0.5` |
| `.github/workflows/unit-tests.yml` | `actions/checkout` | `@v4` | `@v4.3.1` |
| `.github/workflows/unit-tests.yml` | `actions/setup-node` | `@v4` | `@v6.4.0` |
| `.github/workflows/e2e-full.yml` | `actions/checkout` | `@v4` | `@v4.3.1` |
| `.github/workflows/e2e-full.yml` | `actions/upload-artifact` | `@v4` | `@v7.0.1` |
| `.github/workflows/e2e-nightly.yml` | `actions/checkout` | `@v4` | `@v4.3.1` |
| `.github/workflows/e2e-nightly.yml` | `actions/upload-artifact` | `@v4` | `@v7.0.1` |
| `.github/workflows/e2e-smoke.yml` | `actions/checkout` | `@v4` | `@v4.3.1` |
| `.github/workflows/e2e-smoke.yml` | `actions/upload-artifact` | `@v4` | `@v7.0.1` |
| `.github/workflows/i18n-guard.yml` | `actions/checkout` | `@v4` | `@v4.3.1` |
| `.github/workflows/i18n-guard.yml` | `actions/setup-python` | `@v5` | `@v6.2.0` |

---

### Task 1: 作業ブランチを作成する

**Files:** なし（git 操作のみ）

- [ ] **Step 1: ブランチを作成してプッシュ**

```bash
git checkout -b fix/actions-nodejs24-migration
git push -u origin fix/actions-nodejs24-migration
```

Expected: ブランチ作成 + upstream 設定完了。

---

### Task 2: e2e-setup composite action のバージョンを更新する

**Files:**
- Modify: `.github/actions/e2e-setup/action.yml`

- [ ] **Step 1: setup-python を v5 → v6.2.0 に更新**

`.github/actions/e2e-setup/action.yml` の下記行を編集：

```yaml
# 変更前
      uses: actions/setup-python@v5

# 変更後
      uses: actions/setup-python@v6.2.0
```

- [ ] **Step 2: setup-uv を v3 → v8.1.0 に更新**

同ファイルの下記行を編集：

```yaml
# 変更前
      uses: astral-sh/setup-uv@v3

# 変更後
      uses: astral-sh/setup-uv@v8.1.0
```

- [ ] **Step 3: setup-node を v4 → v6.4.0 に更新**

同ファイルの下記行を編集：

```yaml
# 変更前
      uses: actions/setup-node@v4

# 変更後
      uses: actions/setup-node@v6.4.0
```

- [ ] **Step 4: cache を v4 → v5.0.5 に更新**

同ファイルの下記行を編集：

```yaml
# 変更前
      uses: actions/cache@v4

# 変更後
      uses: actions/cache@v5.0.5
```

- [ ] **Step 5: 変更を確認してコミット**

```bash
grep -n "uses:" .github/actions/e2e-setup/action.yml
```

Expected（抜粋）：
```
37:      uses: actions/setup-python@v6.2.0
42:      uses: astral-sh/setup-uv@v8.1.0
53:      uses: actions/setup-node@v6.4.0
65:      uses: actions/cache@v5.0.5
```

```bash
git add .github/actions/e2e-setup/action.yml
git commit -m "chore(ci): bump e2e-setup composite action to Node.js 24 compatible versions"
```

---

### Task 3: unit-tests.yml のバージョンを更新する

**Files:**
- Modify: `.github/workflows/unit-tests.yml`

- [ ] **Step 1: checkout を v4 → v4.3.1 に更新（3 箇所）**

`unit-tests.yml` には `actions/checkout@v4` が 3 行（`api-lint`・`mcp-lint`・`app-lint` ジョブ）ある。
全箇所を一括置換（macOS の場合 `-i ''`）：

```bash
sed -i '' 's|actions/checkout@v4|actions/checkout@v4.3.1|g' .github/workflows/unit-tests.yml
```

- [ ] **Step 2: setup-node を v4 → v6.4.0 に更新（app-lint ジョブの 1 行）**

`unit-tests.yml` の `app-lint` ジョブの setup-node 行を編集：

```yaml
# 変更前
      - uses: actions/setup-node@v4

# 変更後
      - uses: actions/setup-node@v6.4.0
```

- [ ] **Step 3: 変更を確認してコミット**

```bash
grep -n "checkout\|setup-node" .github/workflows/unit-tests.yml
```

Expected：
```
35:      - uses: actions/checkout@v4.3.1
55:      - uses: actions/checkout@v4.3.1
76:      - uses: actions/checkout@v4.3.1
77:      - uses: actions/setup-node@v6.4.0
```

```bash
git add .github/workflows/unit-tests.yml
git commit -m "chore(ci): bump unit-tests workflow to Node.js 24 compatible action versions"
```

---

### Task 4: E2E ワークフロー 3 件のバージョンを更新する

**Files:**
- Modify: `.github/workflows/e2e-full.yml`
- Modify: `.github/workflows/e2e-nightly.yml`
- Modify: `.github/workflows/e2e-smoke.yml`

- [ ] **Step 1: 3 ファイルの checkout を一括置換（macOS の場合 `-i ''`）**

```bash
sed -i '' 's|actions/checkout@v4|actions/checkout@v4.3.1|g' \
  .github/workflows/e2e-full.yml \
  .github/workflows/e2e-nightly.yml \
  .github/workflows/e2e-smoke.yml
```

- [ ] **Step 2: 3 ファイルの upload-artifact を一括置換（macOS の場合 `-i ''`）**

```bash
sed -i '' 's|actions/upload-artifact@v4|actions/upload-artifact@v7.0.1|g' \
  .github/workflows/e2e-full.yml \
  .github/workflows/e2e-nightly.yml \
  .github/workflows/e2e-smoke.yml
```

- [ ] **Step 3: 変更を確認**

```bash
grep -n "checkout\|upload-artifact" \
  .github/workflows/e2e-full.yml \
  .github/workflows/e2e-nightly.yml \
  .github/workflows/e2e-smoke.yml
```

Expected（各ファイルに 1 行ずつ）：
```
e2e-full.yml:75:        uses: actions/checkout@v4.3.1
e2e-full.yml:143:        uses: actions/upload-artifact@v7.0.1
e2e-nightly.yml:69:        uses: actions/checkout@v4.3.1
e2e-nightly.yml:141:        uses: actions/upload-artifact@v7.0.1
e2e-smoke.yml:70:        uses: actions/checkout@v4.3.1
e2e-smoke.yml:124:        uses: actions/upload-artifact@v7.0.1
```

- [ ] **Step 4: コミット**

```bash
git add \
  .github/workflows/e2e-full.yml \
  .github/workflows/e2e-nightly.yml \
  .github/workflows/e2e-smoke.yml
git commit -m "chore(ci): bump e2e workflows to Node.js 24 compatible action versions"
```

---

### Task 5: i18n-guard.yml のバージョンを更新する

**Files:**
- Modify: `.github/workflows/i18n-guard.yml`

- [ ] **Step 1: checkout と setup-python を更新（macOS の場合 `-i ''`）**

```bash
sed -i '' 's|actions/checkout@v4|actions/checkout@v4.3.1|g' .github/workflows/i18n-guard.yml
sed -i '' 's|actions/setup-python@v5|actions/setup-python@v6.2.0|g' .github/workflows/i18n-guard.yml
```

- [ ] **Step 2: 変更を確認してコミット**

```bash
grep -n "uses:" .github/workflows/i18n-guard.yml
```

Expected：
```
30:      - uses: actions/checkout@v4.3.1
33:        uses: actions/setup-python@v6.2.0
```

```bash
git add .github/workflows/i18n-guard.yml
git commit -m "chore(ci): bump i18n-guard workflow to Node.js 24 compatible action versions"
```

---

### Task 6: PR を作成して CI 確認後 Issue #135 をクローズする

**Files:** なし（git / gh 操作のみ）

- [ ] **Step 1: プッシュして PR を作成**

```bash
git push
gh pr create \
  --repo mopinfish/geo-base \
  --title "chore(ci): bump GitHub Actions to Node.js 24 compatible versions" \
  --body "$(cat <<'EOF'
## Summary

- GitHub Actions の Node.js 20 非推奨警告に対応。2026-06-02 の強制移行前に action バージョンを更新。
- Issue #135（2026-05-11 ナイトリー失敗）の 7 件の E2E 失敗は PR #139 / #140 で解決済み・2026-05-12 ナイトリー全 pass 確認済み。本 PR でクローズする。

## 変更内容

| action | 旧 | 新 |
|---|---|---|
| `actions/checkout` | `@v4` | `@v4.3.1` |
| `actions/setup-node` | `@v4` | `@v6.4.0` |
| `actions/cache` | `@v4` | `@v5.0.5` |
| `actions/upload-artifact` | `@v4` | `@v7.0.1` |
| `actions/setup-python` | `@v5` | `@v6.2.0` |
| `astral-sh/setup-uv` | `@v3` | `@v8.1.0` |

アプリが使う Node.js バージョン（20）は変更しない。

## Test plan

- [ ] PR トリガーの unit-tests (api-lint / mcp-lint / app-lint) が pass
- [ ] PR トリガーの e2e-smoke が pass
- [ ] CI 警告「Node.js 20 actions are deprecated」が消えていること

Closes #135
EOF
)"
```

- [ ] **Step 2: unit-tests CI が pass することを確認**

```bash
gh pr checks --repo mopinfish/geo-base --watch
```

Expected: `unit-tests` ジョブ（api-lint / mcp-lint / app-lint）が全て ✓

- [ ] **Step 3: e2e-smoke CI が pass することを確認**

同じく `e2e-smoke` ジョブが ✓ になることを確認。

- [ ] **Step 4: Node.js 20 警告が消えたことをログで確認**

```bash
gh run view --repo mopinfish/geo-base $(gh run list --repo mopinfish/geo-base --workflow=unit-tests.yml --limit=1 --json databaseId -q '.[0].databaseId') --log | grep "Node.js 20" | wc -l
```

Expected: `0`（警告行なし）

- [ ] **Step 5: PR をマージ**

CI 全 pass を確認してからマージ。

```bash
gh pr merge --repo mopinfish/geo-base --squash --auto
```

`Closes #135` が PR 本文に含まれているため、マージ時に Issue #135 が自動クローズされる。
