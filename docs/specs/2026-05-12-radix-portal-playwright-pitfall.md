# Radix UI Portal × Playwright headless の干渉と回避策

- **Date**: 2026-05-12
- **Status**: Documented (knowledge memo)
- **Owner**: @OtsukaNoboru
- **Related Issues**: #138（tilesets E2E 4 件の固定的 timeout）
- **Related PRs**: features ページの先行回避（`app/src/app/features/page.tsx:517`）

## TL;DR

shadcn/ui の `<Select>` と `<AlertDialog>` は、内部で **Radix UI Portal** を使って `<body>` 直下へコンテンツを切り出してレンダする。Playwright を `headless: true`（CI のデフォルト）で実行すると、その portal 化された要素を `page.getByRole("option", ...)` / `page.getByRole("alertdialog").getByRole("button", { name })` で取りに行く selector が **間欠的に 30s timeout する**。

確認済みの回避策は次の 2 系統:

1. **`<Select>` → ネイティブ `<select>` への置換**（フィルタやドロップダウン用途）
2. **`<AlertDialogAction>` などへの `data-testid` 付与**（モーダル確定ボタン用途）

新規に Radix の Portal 系コンポーネント（`Select`, `AlertDialog`, `Dialog`, `Popover`, `DropdownMenu`, `Tooltip` の `Content`）を E2E で操作する場合は、最初から **role ベース selector を避け、testid で取得する**設計にすること。

## 経緯

### 1 回目の遭遇 — features ページ（時期不明、コメント残置のみ）

`/features` のフィルタ用 `<Select>` が Playwright で安定して操作できず、当時の対応として **ネイティブ `<select>` に置き換えた**。残った痕跡:

```tsx
// app/src/app/features/page.tsx:517
{/* ネイティブselectを使用（Radix UIのポータル問題を回避） */}
<select data-testid="feature-filter-tileset" aria-label="タイルセットで絞り込み">
```

このときは tilesets ページには同じ処置が入らなかった。

### 2 回目の遭遇 — tilesets ページ（Issue #138, 2026-05-12）

`E2E full` で 4 件の固定的 failure:

| # | テスト | 失敗 selector |
|---|---|---|
| TS-03 | `tilesets/list-create.spec.ts` type フィルタ | `getByRole("option", { name: "ベクター" })` |
| TS-04 | `tilesets/list-create.spec.ts` public/private フィルタ | `getByRole("option", { name: "公開", exact: true })` |
| TS-05 | `tilesets/list-create.spec.ts` 一括削除確認 | `getByRole("alertdialog").getByRole("button", { name: /件を削除/ })` |
| TS-11 | `tilesets/delete.spec.ts` 詳細削除確認 | `getByRole("alertdialog").getByRole("button", { name: "削除する" })` |

PR #137 では i18n catalog に合わせて `"ベクタ" → "ベクター"` の文字列を直したが、timeout は変わらず。文字列ではなく **role を持つ要素自体に到達できていない**ことが判明。

## なぜ起きるか（仮説）

- Radix の `SelectContent` / `AlertDialogContent` は **mount 時に `<body>` 直下へ Portal される**。
- React の hydration 完了、Portal の DOM commit、Radix の `data-state="open"` 反映、Playwright の locator polling のタイミングが headless 環境で噛み合わず、`getByRole("option" | "button")` の role 判定が成立する前に 30s 経過する。
- 通常の `headed` 実行（`npm run test:e2e:ui`）や手動操作では再現性が低い。CI の headless + 並列 + リソース制約環境で表面化する。

確証までは至っていない（深く調べるなら Playwright trace の attached `role` 計算を比較する必要がある）が、**Portal 系で同じパターンの timeout** が複数のコンポーネントで再現することから、根本要因は selector 戦略側にあると判断している。

## 回避方針（採用済み）

### 方針 A: ドロップダウン系は **ネイティブ `<select>`** に置き換える

採用箇所: `/features`（先行）, `/tilesets`（Issue #138 で追従）。

利点:

- Playwright の `selectOption({ label })` が確実に動く。
- スクリーンリーダーで自動的に「リスト」として認識される（追加 ARIA 不要）。
- Portal を経由しないため hydration race の影響を受けない。

実装テンプレ（`/features` 由来、`/tilesets` も同型）:

```tsx
<div className="relative">
  <select
    data-testid="tileset-filter-type"
    aria-label={t("filter_type_label")}
    value={typeFilter}
    onChange={(e) => setTypeFilter(e.target.value)}
    className="h-9 w-[150px] appearance-none rounded-md border border-input bg-transparent px-3 py-2 pr-8 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
  >
    <option value="all">{t("filter_type_all")}</option>
    {/* ... */}
  </select>
  <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-4 w-4 -translate-y-1/2 opacity-50" />
</div>
```

テスト側:

```ts
await page.getByTestId("tileset-filter-type").selectOption({ label: "ベクター" });
```

トレードオフ: `<SelectContent>` の柔軟なスタイリング（アイコン入り option, グループ化など）は失われる。ただし geo-base の現行フィルタ用途では十分。

### 方針 B: モーダル確定ボタンは `data-testid` で取得する

`<AlertDialog>` 自体はネイティブ代替がないので置換しない。代わりに `<AlertDialogAction>` / `<AlertDialogCancel>` 等の **アクションボタンに `data-testid` を付与**し、テスト側は role ではなく testid で拾う。

実装テンプレ:

```tsx
<AlertDialogAction
  onClick={handleConfirm}
  data-testid="tileset-delete-confirm"
  className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
>
  {t("confirm")}
</AlertDialogAction>
```

テスト側:

```ts
await page.getByTestId("tileset-delete-button").click();
await page.getByTestId("tileset-delete-confirm").click();
```

testid 命名規則: `<feature>-<action>-confirm` / `<feature>-<action>-cancel`。

## やってはいけない（再発パターン）

- 新規の shadcn `<Select>` / `<AlertDialog>` を入れたあと、テストで `page.getByRole("option", { name })` / `page.getByRole("alertdialog").getByRole("button", { name })` を使う。
- selector が timeout した際に、**i18n 文字列を疑って `{ name: "..." }` のテキストを直す**（PR #137 で実際にやって直らなかった）。文字列ではなく selector 戦略の問題。
- `await expect(...).toBeVisible({ timeout: ... })` で待ち時間を延ばして誤魔化す（根本要因が消えないので flaky のまま）。

## 関連コンポーネントと未対応箇所

将来 E2E を追加する際、以下も同じ罠を踏みうる:

- `app/src/components/ui/dialog.tsx`（`Dialog` 一般）
- `app/src/components/ui/popover.tsx`
- `app/src/components/ui/dropdown-menu.tsx`
- `app/src/components/ui/tooltip.tsx`
- `app/src/components/ui/select.tsx`（このメモ時点で `/datasources`, `/teams`, `/api-keys` などにも残置）

新規 E2E を書く時点で **「Radix Portal 系コンポーネントを操作するか」** をチェックし、該当する場合は最初から testid ベースで設計する。
