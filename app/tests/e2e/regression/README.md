# Regression tests

過去に発生したバグの再発を検出するテスト群を置く。

## 命名規則

- ファイル名: `issue-<NUMBER>-<short-description>.spec.ts`
- 各 spec の冒頭の comment に **対応 issue / PR と発生したリグレッションの説明** を残す
- `@smoke` タグは付けない（regression は full のみで実行）。`@regression` タグを付ける。

## 既存 regression

| Test ID | 元 issue / PR | 内容 |
|---|---|---|
| TS-13 | #102 / PR #103 | 自分の非公開 tileset が `/tilesets` 一覧に表示される |

## 新規追加の流れ

1. 同 PR で「バグ修正」と「regression テスト追加」をセットでコミット
2. CONTRIBUTING ガイドラインに従い、ファイル名・コメントを規約どおりに
3. main マージ後の e2e-full / nightly でグリーンを確認
