# GitHub Actions Node.js 24 移行設計

- **Date**: 2026-05-13
- **Status**: Approved
- **Owner**: @OtsukaNoboru
- **Related Issues**: #135（E2E nightly failure 2026-05-11）
- **Deadline**: 2026-06-02（GitHub が Node.js 24 を強制適用）

## 背景

GitHub Actions の Node.js 20 ランタイムが 2026-06-02 に強制的に Node.js 24 へ移行される。現行ワークフローが参照するいくつかの action は Node.js 20 ベースのバージョンを使用しており、CI ログに以下の警告が出続けている：

```
Node.js 20 actions are deprecated. The following actions are running on Node.js 20 and may not work as expected:
  actions/cache@v4, actions/checkout@v4, actions/setup-node@v4,
  actions/setup-python@v5, actions/upload-artifact@v4, astral-sh/setup-uv@v3
```

あわせて Issue #135（2026-05-11 ナイトリー失敗）も本 PR でクローズする。
Issue #135 の起因となった 7 件の E2E 失敗（tilesets Radix Portal 問題 + a11y 違反）は
PR #139 および PR #140 によって修正済みであり、2026-05-12 ナイトリーは全 77 テスト合格している。

## スコープ

- **対象**: `.github/` 配下の action バージョンタグのみ更新
- **対象外**: アプリが使う Node.js バージョン（現行 20）の変更、ワークフロー構造の変更、`cleanup-expired.yml`（superfly/flyctl-actions は SHA ピン済みのため CI 警告対象外）

### バージョン選定方針

- `actions/checkout` は v4.3.1（v6 バックポートパッチ）で v4 系に留める。checkout は credential 処理に絡むため major 変更のリスクを最小化。
- その他の action は最新 stable の major バージョンに揃える（v4/v5 系に Node.js 24 互換バックポートがない、または最新 major との差が小さい）。

## 変更対象ファイルと更新内容

### `.github/actions/e2e-setup/action.yml`

| 行 | 現行 | 更新後 |
|---|---|---|
| `actions/setup-python` | `@v5` | `@v6.2.0` |
| `astral-sh/setup-uv` | `@v3` | `@v8.1.0` |
| `actions/setup-node` | `@v4` | `@v6.4.0` |
| `actions/cache` | `@v4` | `@v5.0.5` |

### `.github/workflows/unit-tests.yml`

| 行 | 現行 | 更新後 |
|---|---|---|
| `actions/checkout` | `@v4` | `@v4.3.1` |
| `actions/setup-node` | `@v4` | `@v6.4.0` |

### `.github/workflows/e2e-full.yml`

| 行 | 現行 | 更新後 |
|---|---|---|
| `actions/checkout` | `@v4` | `@v4.3.1` |
| `actions/upload-artifact` | `@v4` | `@v7.0.1` |

### `.github/workflows/e2e-nightly.yml`

| 行 | 現行 | 更新後 |
|---|---|---|
| `actions/checkout` | `@v4` | `@v4.3.1` |
| `actions/upload-artifact` | `@v4` | `@v7.0.1` |

### `.github/workflows/e2e-smoke.yml`

| 行 | 現行 | 更新後 |
|---|---|---|
| `actions/checkout` | `@v4` | `@v4.3.1` |
| `actions/upload-artifact` | `@v4` | `@v7.0.1` |

### `.github/workflows/i18n-guard.yml`

| 行 | 現行 | 更新後 |
|---|---|---|
| `actions/checkout` | `@v4` | `@v4.3.1` |
| `actions/setup-python` | `@v5` | `@v6.2.0` |

## 破壊的変更の評価

### `actions/setup-node` v4 → v6

v6 で「自動キャッシュを npm 限定に絞り込み」「always-auth 削除」の breaking change がある。
本プロジェクトはキャッシュを `cache: "npm"` で使用しており影響なし。always-auth も使用していない。

### `actions/cache` v4 → v5

v5 は Actions Runner v2.327.1+ が必要。GitHub hosted runner (`ubuntu-latest`) は常に最新なので問題なし。

### `actions/upload-artifact` v4 → v7

v5〜v7 を通じてアーティファクト名・path 指定の API は互換が維持されている。
現行ワークフローは `name:` と `path:` のみ使用しており影響なし。

### `astral-sh/setup-uv` v3 → v8

`enable-cache`・`cache-dependency-glob`・`version` の各入力は v8 でも継続サポートされている。

## 確認方法

1. PR をプッシュして unit-tests workflow（PR トリガー）が成功することを確認
2. e2e-smoke workflow が成功することを確認（PR トリガー）
3. マージ後、翌日のナイトリーが成功することを確認

## Issue #135 クローズ手順

PR 説明文に `Closes #135` を含める。
コメントとして以下を記載：

> 7 件の E2E 失敗は PR #139（tilesets Radix Portal 対策）と PR #140（a11y aria-label 追加）で修正済み。
> 2026-05-12 のナイトリー（77 passed）で確認済み。
> 本 PR では GitHub Actions の Node.js 24 移行（6/2 対応期限）をあわせて対処する。
