# Admin UI デザインシステム Phase 1 トークン実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Issue #91〜#94（Epic #90 Phase 1）を実装し、`globals.css` にデジタル庁デザインシステム準拠のデザイントークン（色・タイポグラフィ・スペーシング・フォーカスリング）を整備する。

**Architecture:** 4 Issue すべてが `app/src/app/globals.css` を変更するため、直列に実装する（#91→#92→#93→#94）。単一 feature ブランチ上で各 Issue を 1 コミットとし、Phase 1 完了後に PR を作成する。

**Tech Stack:** Next.js 16 + React 19 + Tailwind v4 + shadcn/ui (new-york, neutral) + Vitest + Playwright + @axe-core/playwright

---

## ファイル変更マップ

| Task | Issue | 変更ファイル |
|------|-------|-------------|
| 1 | #91 色パレット | `app/src/app/globals.css` |
| 2 | #92 タイポグラフィ | `app/src/app/globals.css`, `app/src/app/layout.tsx` |
| 3 | #93 スペーシング・角丸・シャドウ | `app/src/app/globals.css` |
| 4 | #94 フォーカスリング | `app/src/app/globals.css`, `app/src/components/ui/button.tsx`, `app/src/components/ui/input.tsx`, `app/src/components/ui/textarea.tsx`, `app/src/components/ui/select.tsx`, `app/src/components/ui/checkbox.tsx`, `app/src/components/ui/tabs.tsx`, `app/src/components/ui/switch.tsx`, `app/src/components/ui/badge.tsx`, `app/src/components/ui/dialog.tsx` |

---

## Task 0: ブランチ作成

**Files:**
- Git branch: `feat/design-system-phase1`

- [ ] **Step 1: feature ブランチを作成**

```bash
cd /Users/otsuka/ws/projects/geofirm/geo-base
git checkout -b feat/design-system-phase1
```

Expected: `Switched to a new branch 'feat/design-system-phase1'`

---

## Task 1: Issue #91 — 色パレット定義（CSS 変数追加）

**目的:** デジタル庁準拠の `--color-primary-50〜900` スケールを Tailwind v4 の `@theme inline` ブロックに追加する。既存の shadcn HSL 変数（`--primary`, `--secondary` 等）は変更しない（色テイスト維持）。

**Files:**
- Modify: `app/src/app/globals.css`

### 現状確認

- [ ] **Step 1: 現在の globals.css を確認**

```bash
cat app/src/app/globals.css
```

Expected: `@import "tailwindcss"` で始まり、`:root` に HSL 変数、`.dark` ブロック、`@theme inline` ブロックが続く。

### 実装

- [ ] **Step 2: `@theme inline` ブロック末尾に色スケール変数を追加**

`app/src/app/globals.css` の `@theme inline { ... }` 閉じ括弧の直前に以下を追加する：

```css
  /* Issue #91: Primary color scale (hue 240, デジタル庁準拠 neutral-cool) */
  --color-primary-50: hsl(240 20% 98%);
  --color-primary-100: hsl(240 15% 96%);
  --color-primary-200: hsl(240 10% 91%);
  --color-primary-300: hsl(240 8% 83%);
  --color-primary-400: hsl(240 6% 70%);
  --color-primary-500: hsl(240 5.9% 55%);
  --color-primary-600: hsl(240 5.9% 40%);
  --color-primary-700: hsl(240 5.9% 28%);
  --color-primary-800: hsl(240 5.9% 18%);
  --color-primary-900: hsl(240 5.9% 10%);
```

変更後の `@theme inline` ブロック全体（完全版）:

```css
@theme inline {
  --color-background: hsl(var(--background));
  --color-foreground: hsl(var(--foreground));
  --color-card: hsl(var(--card));
  --color-card-foreground: hsl(var(--card-foreground));
  --color-popover: hsl(var(--popover));
  --color-popover-foreground: hsl(var(--popover-foreground));
  --color-primary: hsl(var(--primary));
  --color-primary-foreground: hsl(var(--primary-foreground));
  --color-secondary: hsl(var(--secondary));
  --color-secondary-foreground: hsl(var(--secondary-foreground));
  --color-muted: hsl(var(--muted));
  --color-muted-foreground: hsl(var(--muted-foreground));
  --color-accent: hsl(var(--accent));
  --color-accent-foreground: hsl(var(--accent-foreground));
  --color-destructive: hsl(var(--destructive));
  --color-destructive-foreground: hsl(var(--destructive-foreground));
  --color-border: hsl(var(--border));
  --color-input: hsl(var(--input));
  --color-ring: hsl(var(--ring));
  --radius-lg: var(--radius);
  --radius-md: calc(var(--radius) - 2px);
  --radius-sm: calc(var(--radius) - 4px);
  /* Issue #91: Primary color scale (hue 240, デジタル庁準拠 neutral-cool) */
  --color-primary-50: hsl(240 20% 98%);
  --color-primary-100: hsl(240 15% 96%);
  --color-primary-200: hsl(240 10% 91%);
  --color-primary-300: hsl(240 8% 83%);
  --color-primary-400: hsl(240 6% 70%);
  --color-primary-500: hsl(240 5.9% 55%);
  --color-primary-600: hsl(240 5.9% 40%);
  --color-primary-700: hsl(240 5.9% 28%);
  --color-primary-800: hsl(240 5.9% 18%);
  --color-primary-900: hsl(240 5.9% 10%);
}
```

### 検証

- [ ] **Step 3: ビルドを実行して構文エラーがないことを確認**

```bash
cd app && npm run build 2>&1 | tail -20
```

Expected: `✓ Compiled successfully` または `Route (app)` の一覧。エラーなし。

- [ ] **Step 4: Lint を実行**

```bash
npm run lint 2>&1 | tail -10
```

Expected: エラーなし（warning は許容）。

- [ ] **Step 5: ユニットテストを実行**

```bash
npm run test 2>&1 | tail -10
```

Expected: `Tests 1 passed (1)` 等、fail なし。

### コミット

- [ ] **Step 6: コミット**

```bash
cd ..
git add app/src/app/globals.css
git commit -m "feat(ui): add color scale tokens for #91 (--color-primary-50..900)"
```

---

## Task 2: Issue #92 — タイポグラフィトークン

**目的:** Noto Sans JP フォントを導入し、デジタル庁準拠のタイポグラフィスケールを定義する。

**Files:**
- Modify: `app/src/app/layout.tsx`
- Modify: `app/src/app/globals.css`

### 実装: フォント設定

- [ ] **Step 1: `layout.tsx` に Noto Sans JP を追加**

`app/src/app/layout.tsx` を以下のように変更する：

変更前:
```tsx
import type { Metadata } from "next";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getMessages, getTranslations } from "next-intl/server";

import "./globals.css";
import { AuthProvider } from "@/lib/auth/context";
```

変更後:
```tsx
import type { Metadata } from "next";
import { Noto_Sans_JP } from "next/font/google";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getMessages, getTranslations } from "next-intl/server";

import "./globals.css";
import { AuthProvider } from "@/lib/auth/context";

const notoSansJP = Noto_Sans_JP({
  subsets: ["latin"],
  weight: ["400", "500", "700"],
  display: "swap",
  variable: "--font-noto-sans-jp",
  preload: false,
});
```

- [ ] **Step 2: `<html>` 要素に font 変数クラスを追加**

変更前:
```tsx
  return (
    <html lang={locale}>
      <body className="antialiased">
```

変更後:
```tsx
  return (
    <html lang={locale} className={notoSansJP.variable}>
      <body className="antialiased">
```

### 実装: タイポグラフィ CSS 変数

- [ ] **Step 3: `globals.css` の `@theme inline` にフォント・タイポグラフィトークンを追加**

`@theme inline` ブロック末尾（Issue #91 の色スケール変数の後）に追加する：

```css
  /* Issue #92: Font family */
  --font-sans: var(--font-noto-sans-jp), -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  /* Issue #92: Font size scale (デジタル庁準拠) */
  --font-size-display-lg: 3rem;
  --font-size-display-md: 2.25rem;
  --font-size-display-sm: 1.875rem;
  --font-size-heading-lg: 1.5rem;
  --font-size-heading-md: 1.25rem;
  --font-size-heading-sm: 1.125rem;
  --font-size-heading-xs: 1rem;
  /* Issue #92: Line height */
  --line-height-display: 1.2;
  --line-height-heading: 1.4;
  /* Issue #92: Letter spacing */
  --letter-spacing-display: -0.02em;
  --letter-spacing-heading: -0.01em;
```

- [ ] **Step 4: `body` スタイルを更新してフォント変数を参照**

`globals.css` の `body` ルールを変更する：

変更前:
```css
body {
  background-color: hsl(var(--background));
  color: hsl(var(--foreground));
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}
```

変更後:
```css
body {
  background-color: hsl(var(--background));
  color: hsl(var(--foreground));
  font-family: var(--font-sans);
}
```

- [ ] **Step 5: 見出し階層スタイルを `globals.css` に追加**

`globals.css` の末尾（`body` ルールの後）に追加する：

```css
/* Issue #92: 見出し階層（デジタル庁デザインシステム準拠） */
h1 {
  font-size: var(--font-size-heading-lg);
  font-weight: 700;
  line-height: var(--line-height-heading);
  letter-spacing: var(--letter-spacing-heading);
}

h2 {
  font-size: var(--font-size-heading-md);
  font-weight: 700;
  line-height: var(--line-height-heading);
}

h3 {
  font-size: var(--font-size-heading-sm);
  font-weight: 600;
  line-height: var(--line-height-heading);
}

h4 {
  font-size: var(--font-size-heading-xs);
  font-weight: 600;
  line-height: var(--line-height-heading);
}
```

### 検証

- [ ] **Step 6: TypeScript 型チェックとビルド**

```bash
cd app && npm run build 2>&1 | tail -20
```

Expected: エラーなし。`Noto_Sans_JP` のインポートが正常に解決される。

- [ ] **Step 7: Lint 実行**

```bash
npm run lint 2>&1 | tail -10
```

Expected: エラーなし。

- [ ] **Step 8: ユニットテスト**

```bash
npm run test 2>&1 | tail -10
```

Expected: fail なし。

### コミット

- [ ] **Step 9: コミット**

```bash
cd ..
git add app/src/app/layout.tsx app/src/app/globals.css
git commit -m "feat(ui): add typography tokens and Noto Sans JP for #92"
```

---

## Task 3: Issue #93 — スペーシング・角丸・シャドウ・ブレークポイント

**目的:** elevation シャドウトークン（`--shadow-1/2/3`）と補完的な radius トークン（`--radius-full`）を追加する。スペーシング・ブレークポイントは Tailwind v4 デフォルトが既にデジタル庁準拠に近いため、確認のみとする。

**Files:**
- Modify: `app/src/app/globals.css`

### 実装

- [ ] **Step 1: `:root` に shadow 変数を追加**

`globals.css` の `:root { ... }` 閉じ括弧の直前に追加する：

```css
  /* Issue #93: Elevation shadow tokens (デジタル庁準拠) */
  --shadow-1: 0 1px 2px 0 hsl(var(--foreground) / 0.05);
  --shadow-2: 0 2px 4px 0 hsl(var(--foreground) / 0.10);
  --shadow-3: 0 4px 8px 0 hsl(var(--foreground) / 0.15);
```

- [ ] **Step 2: `@theme inline` に shadow・radius トークンを追加**

`@theme inline` ブロック末尾（Issue #92 変数の後）に追加する：

```css
  /* Issue #93: Shadow tokens */
  --shadow-sm: var(--shadow-1);
  --shadow-md: var(--shadow-2);
  --shadow-lg: var(--shadow-3);
  /* Issue #93: Full radius for pills/avatars */
  --radius-full: 9999px;
```

### 検証

- [ ] **Step 3: ビルド**

```bash
cd app && npm run build 2>&1 | tail -20
```

Expected: エラーなし。

- [ ] **Step 4: Lint**

```bash
npm run lint 2>&1 | tail -10
```

Expected: エラーなし。

- [ ] **Step 5: ユニットテスト**

```bash
npm run test 2>&1 | tail -10
```

Expected: fail なし。

### コミット

- [ ] **Step 6: コミット**

```bash
cd ..
git add app/src/app/globals.css
git commit -m "feat(ui): add shadow elevation and radius tokens for #93"
```

---

## Task 4: Issue #94 — フォーカスリング & 選択可視状態

**目的:** WCAG 1.4.11（非テキスト要素コントラスト 3:1）を満たすフォーカスリングを定義し、全 shadcn コンポーネントに反映する。`focus-visible:ring-*`（box-shadow）から `focus-visible:outline-*`（CSS outline）へ移行し、`:focus` → `:focus-visible` に統一する。

**Files:**
- Modify: `app/src/app/globals.css`
- Modify: `app/src/components/ui/button.tsx`
- Modify: `app/src/components/ui/input.tsx`
- Modify: `app/src/components/ui/textarea.tsx`
- Modify: `app/src/components/ui/select.tsx`
- Modify: `app/src/components/ui/checkbox.tsx`
- Modify: `app/src/components/ui/tabs.tsx`
- Modify: `app/src/components/ui/switch.tsx`
- Modify: `app/src/components/ui/badge.tsx`
- Modify: `app/src/components/ui/dialog.tsx`

### 実装: globals.css

- [ ] **Step 1: `:root` の `--ring` 値を WCAG 準拠値として明示**

現状の `--ring: 240 5.9% 10%`（ライトモード）と `--ring: 240 4.9% 83.9%`（ダークモード）は既に WCAG 1.4.11 の 3:1 コントラスト要件を満たしている。値は変更せず、フォーカスリング専用トークンを `:root` に追加する：

```css
  /* Issue #94: Focus ring tokens */
  --focus-ring-width: 2px;
  --focus-ring-offset: 2px;
```

これを `:root { ... }` の `--radius: 0.5rem;` の後に追加する。

- [ ] **Step 2: `@theme inline` にフォーカスリングユーティリティを追加**

`@theme inline` ブロック末尾に追加する：

```css
  /* Issue #94: Focus ring (outline approach) */
  --outline-width-focus: var(--focus-ring-width);
  --outline-offset-focus: var(--focus-ring-offset);
```

### 実装: button.tsx

- [ ] **Step 3: `button.tsx` のフォーカスクラスを更新**

変更前 (`buttonVariants` の base クラス):
```
focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring
```

変更後:
```
focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring
```

完全な変更後の base クラス文字列:
```
"inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0"
```

### 実装: input.tsx

- [ ] **Step 4: `input.tsx` のフォーカスクラスを更新**

変更前:
```
focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring
```

変更後:
```
focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring
```

完全な変更後のクラス文字列:
```
"flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-base shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring disabled:cursor-not-allowed disabled:opacity-50 md:text-sm"
```

### 実装: textarea.tsx

- [ ] **Step 5: `textarea.tsx` のフォーカスクラスを更新**

変更前:
```
ring-offset-background ... focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2
```

変更後（`ring-offset-background`, `focus-visible:ring-offset-2` を削除し outline に変更）:
```
"flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-base placeholder:text-muted-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring disabled:cursor-not-allowed disabled:opacity-50 md:text-sm"
```

### 実装: select.tsx

- [ ] **Step 6: `select.tsx` の `SelectTrigger` フォーカスクラスを更新**

変更前:
```
ring-offset-background ... focus:outline-none focus:ring-1 focus:ring-ring
```

変更後（`focus:` → `focus-visible:` に変更、outline アプローチ）:
```
"flex h-9 w-full items-center justify-between whitespace-nowrap rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring disabled:cursor-not-allowed disabled:opacity-50 [&>span]:line-clamp-1"
```

### 実装: checkbox.tsx

- [ ] **Step 7: `checkbox.tsx` のフォーカスクラスを更新**

変更前:
```
ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2
```

変更後:
```
"peer h-4 w-4 shrink-0 rounded-sm border border-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring disabled:cursor-not-allowed disabled:opacity-50 data-[state=checked]:bg-primary data-[state=checked]:text-primary-foreground"
```

### 実装: tabs.tsx

- [ ] **Step 8: `tabs.tsx` の `TabsTrigger` フォーカスクラスを更新**

`TabsTrigger` の変更前:
```
ring-offset-background ... focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2
```

変更後:
```
"inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium transition-all focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring disabled:pointer-events-none disabled:opacity-50 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-sm"
```

`TabsContent` の変更前:
```
ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2
```

変更後:
```
"mt-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
```

### 実装: switch.tsx

- [ ] **Step 9: `switch.tsx` のフォーカスクラスを更新**

変更前:
```
focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background
```

変更後:
```
"peer inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring disabled:cursor-not-allowed disabled:opacity-50 data-[state=checked]:bg-primary data-[state=unchecked]:bg-input"
```

### 実装: badge.tsx

- [ ] **Step 10: `badge.tsx` のフォーカスクラスを更新（`focus:` → `focus-visible:`）**

変更前:
```
focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2
```

変更後:
```
"inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
```

### 実装: dialog.tsx

- [ ] **Step 11: `dialog.tsx` の Close ボタンフォーカスクラスを更新**

変更前:
```
focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2
```

変更後（`focus:` → `focus-visible:`、outline アプローチ）:
```tsx
<DialogPrimitive.Close className="absolute right-4 top-4 rounded-sm opacity-70 transition-opacity hover:opacity-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring disabled:pointer-events-none data-[state=open]:bg-accent data-[state=open]:text-muted-foreground">
```

### 検証

- [ ] **Step 12: ビルド**

```bash
cd app && npm run build 2>&1 | tail -20
```

Expected: エラーなし。

- [ ] **Step 13: Lint**

```bash
npm run lint 2>&1 | tail -10
```

Expected: エラーなし。

- [ ] **Step 14: ユニットテスト**

```bash
npm run test 2>&1 | tail -10
```

Expected: fail なし。

- [ ] **Step 15: 開発サーバーで目視確認**

```bash
npm run dev &
sleep 5
```

ブラウザで以下のページを開き、Tab キーでフォーカス移動してリングが表示されることを確認：
- http://localhost:3000/login → フォームの Input, Button にフォーカスリングが見える
- 各主要ページ（/tilesets, /features, /settings）でフォーカスリングを確認

- [ ] **Step 16: 開発サーバーを停止**

```bash
kill %1 2>/dev/null || pkill -f "next dev"
```

### コミット

- [ ] **Step 17: コミット**

```bash
cd ..
git add app/src/app/globals.css \
        app/src/components/ui/button.tsx \
        app/src/components/ui/input.tsx \
        app/src/components/ui/textarea.tsx \
        app/src/components/ui/select.tsx \
        app/src/components/ui/checkbox.tsx \
        app/src/components/ui/tabs.tsx \
        app/src/components/ui/switch.tsx \
        app/src/components/ui/badge.tsx \
        app/src/components/ui/dialog.tsx
git commit -m "feat(ui): migrate focus ring to outline-based WCAG 1.4.11 for #94"
```

---

## Task 5: PR 作成

- [ ] **Step 1: ブランチをリモートにプッシュ**

```bash
git push -u origin feat/design-system-phase1
```

- [ ] **Step 2: PR を作成**

```bash
gh pr create \
  --title "feat(ui): Phase 1 design tokens — color, typography, spacing, focus ring (#91-#94)" \
  --body "$(cat <<'EOF'
## Summary

- **#91**: `@theme inline` に `--color-primary-50〜900`（hue 240 neutral-cool）スケールを追加。既存 HSL 変数は変更なし（色テイスト維持）
- **#92**: Noto Sans JP を `next/font/google` で導入。タイポグラフィスケール（`--font-size-display-lg/md/sm`, `--font-size-heading-lg/md/sm/xs`）と見出し階層スタイルを追加
- **#93**: Elevation shadow トークン（`--shadow-1/2/3`、`--shadow-sm/md/lg`）と `--radius-full` を追加
- **#94**: 全 shadcn コンポーネントのフォーカス実装を `focus-visible:ring-*`（box-shadow）から `focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring` へ移行。`focus:` → `focus-visible:` に統一（WCAG 2.1 SC 1.4.11 準拠）

## Test plan

- [ ] `npm run build` pass
- [ ] `npm run lint` pass
- [ ] `npm run test` pass（Vitest ユニットテスト）
- [ ] 主要ページ（login / tilesets / features / settings）でフォーカスリングが Tab キーで視認可能
- [ ] ライト/ダーク両モードで視覚的回帰がないことを目視確認
EOF
)"
```

- [ ] **Step 3: Issue をクローズのため PR にリンク**

```bash
gh pr edit --body "$(gh pr view --json body --jq .body)

Closes #91
Closes #92
Closes #93
Closes #94"
```

---

## 注意事項

- **`ring-offset-background` の削除**: outline アプローチでは ring-offset は不要なため削除している。視覚上の変化は最小限（box-shadow → outline への切り替えのみ）
- **`focus:` vs `focus-visible:`**: badge, dialog の close ボタンは元が `focus:` だったが `focus-visible:` に統一。これにより「マウスクリック後にリングが残る」現象が解消される
- **Noto Sans JP のサイズ**: `preload: false` で初期ロードには含めず、`display: swap` で Flash of Unstyled Text を許容。Lighthouse Performance への影響は PR 後に確認する
- **色スケールは追加のみ**: 既存の `--primary`/`--secondary`/`--accent` 変数は変更しないため、視覚的回帰リスクは低い
