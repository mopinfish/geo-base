# Admin UI i18n 規約 (Phase 3 確立)

> 本ドキュメントは Admin UI (`app/`) を `next-intl` で多言語化する際の運用規約をまとめる。Phase 3 (Issue #107) の PR-A 〜 PR-D のレビューを通して確立した実装パターンに基づく。新しい画面 / コンポーネントを catalog 化する際の参考に。
>
> - **対象範囲**: `app/src/` 配下の TypeScript / React コード
> - **目的**: EN / JA 切替時に視覚バグや情報漏洩を起こさないための実装ベストプラクティス
> - **関連**:
>   - 戦略全体: [`docs/superpowers/specs/2026-05-10-i18n-strategy-design.md`](./superpowers/specs/2026-05-10-i18n-strategy-design.md)
>   - PR 分割計画: [`docs/superpowers/plans/2026-05-11-i18n-phase3.md`](./superpowers/plans/2026-05-11-i18n-phase3.md)
>   - Epic: #109、Phase 3 Issue: #107

## 1. Namespace と catalog 構成

### 1.1 Namespace の追加手順

新しい domain (例: `tilesets`) を追加するとき:

1. `app/src/i18n/config.ts` の `NAMESPACES` 配列に名前を追加:
   ```typescript
   export const NAMESPACES = ["common", "api-errors", "auth", "tilesets"] as const;
   ```
2. `app/src/locales/en/<namespace>.json` と `app/src/locales/ja/<namespace>.json` を新規作成
3. `app/src/locales/__tests__/keysets.test.ts` は `NAMESPACES` 配列を反復するため、新規 test 追加不要 (en/ja の同期は自動チェック)

### 1.2 キー設計の 3 階層原則

`<page-or-component>.<section>.<element>` の 3 階層を基本とする。深すぎる入れ子は禁止 (4 階層以上は再設計)。

例:
```json
{
  "login": {
    "title": "Sign in",
    "email_placeholder": "Email",
    "submit": "Sign in"
  },
  "passwordReset": {
    "request": {
      "title": "Reset password",
      "submit": "Send"
    }
  }
}
```

NG: `passwordReset.request.form.fields.email.placeholder` (5 階層)

### 1.3 EN / JA キーの完全一致

`keysets.test.ts` が `flatKeys()` で再帰展開した key set が EN と JA で完全一致することを assert する。**片方にしかないキー / typo は CI で fail する**。

## 2. ICU MessageFormat と動的値

### 2.1 単純な値埋め込み

`{name}` プレースホルダで埋め込み:

```json
{
  "edit": {
    "subtitle_template": "{name} を編集します"
  }
}
```

```tsx
t("subtitle_template", { name: tileset.name })
```

### 2.2 複数値

```json
{
  "invitation": {
    "title": "チーム招待: {team}",
    "role": "役割: {role}"
  }
}
```

### 2.3 数値 (件数表記)

`{count}` で渡す。次の数値以降の単位は文中に書く (EN / JA で語順が違うため):

```json
{
  "list": {
    "selected_count": "{count}件を選択中",
    "bulk_delete_button": "{count}件を削除",
    "bulk_delete_description": "選択した {count} 件のデータを削除します。..."
  }
}
```

EN 版でも `{count} selected` / `Delete {count}` のように単純な置換で対応可。

### 2.4 リッチテキスト (HTML タグ含む) は基本避ける

`<strong>{name}</strong>` のような強調を含む文字列を `t.rich` で扱うことは可能だが、catalog が複雑になる。基本は **プレーンテキストに統一** する判断を Phase 3d で採用 (例: 旧 `<strong>{name}</strong> を編集します` → `{name} を編集します` にプレーン化)。

どうしても必要な場合のみ `t.rich` を使う。

## 3. 日付・時刻フォーマット

### 3.1 NG パターン

ハードコードされた locale は EN UI でも日本語フォーマットになる:

```tsx
// ❌ DO NOT
new Date(s).toLocaleString("ja-JP", { year: "numeric", ... });
```

### 3.2 OK パターン

`useLocale()` から取得した locale を BCP47 タグに正規化して `toLocaleString` に渡す:

```tsx
import { useLocale } from "next-intl";

function Component() {
  const locale = useLocale();
  // BCP47 タグに正規化 ("ja" → "ja-JP", "en" → "en-US")。
  // primary subtag だけでも動くが、明示的に region を渡したほうが安定する。
  const dateLocale = locale === "ja" ? "ja-JP" : "en-US";

  const formatDate = (s: string) =>
    new Date(s).toLocaleString(dateLocale, {
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });

  return <p>{formatDate(item.created_at)}</p>;
}
```

### 3.3 component の冒頭で `dateLocale` を 1 度計算

複数箇所で日付表示する場合、`dateLocale` を component scope で計算して関数内で使い回す (PR-D で確立したパターン)。

## 4. アクセシビリティ (a11y)

### 4.1 アイコンのみのボタンには `aria-label` を必ず付ける

`title` 属性は screen reader の accessible name として確実ではない。`aria-label` を併記する:

```tsx
// ❌ title のみ
<Button variant="ghost" size="icon" title={t("action_view")}>
  <Eye className="h-4 w-4" />
</Button>

// ✓ aria-label + title (同じ翻訳キー)
<Button
  variant="ghost"
  size="icon"
  title={t("action_view")}
  aria-label={t("action_view")}
>
  <Eye className="h-4 w-4" />
</Button>
```

### 4.2 単一選択 dropdown は `DropdownMenuRadioGroup` を使う

`DropdownMenuItem` + `aria-current` ではなく、`DropdownMenuRadioGroup` + `DropdownMenuRadioItem` を使うと `role="menuitemradio"` + `aria-checked` が自動で付く (PR #129 round 2 で確立)。例: `LanguageSwitcher`。

### 4.3 axe-core spec で違反ゼロを保つ

`app/tests/e2e/a11y/` 配下に主要画面ごとの spec を置く (Issue #100、PR #130 / #133 で 6 ページ整備済み)。`expectNoA11ySeriousViolations(page, { awaitReady })` で hydrate 完了を待ってから WCAG 2.1 AA タグでスキャンし、`serious` / `critical` 違反のみ fail。

## 5. React hook の依存配列

### 5.1 NG: `eslint-disable-next-line react-hooks/exhaustive-deps`

stale closure バグの温床になる:

```tsx
// ❌ DO NOT
const fetchData = async () => {
  /* uses `id`, `t` */
};

useEffect(() => {
  fetchData();
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [id, isReady]);
```

### 5.2 OK: `useCallback` で deps を明示

```tsx
// ✓
const fetchData = useCallback(async () => {
  /* uses `id`, `t` */
}, [api, id, isReady, t]);

useEffect(() => {
  if (isReady) fetchData();
}, [isReady, fetchData]);
```

## 6. デバッグログとデータ漏洩

### 6.1 NG: API レスポンスの全件 `console.log`

ブラウザ console に metadata や PII が流出するリスク + ノイズ:

```tsx
// ❌ DO NOT
const data = await api.getTileset(id);
console.log("Tileset data:", data);
setTileset(data);
```

### 6.2 OK: `console.warn` / `console.error` のみ (例外パスのみ)

成功時の payload を出さない。失敗時の operational signal は残す:

```tsx
try {
  const data = await api.getTileset(id);
  setTileset(data);
} catch (err) {
  console.error("Tileset fetch failed:", err);
  setError(/* ... */);
}
```

### 6.3 部分失敗の `console.warn`

複数 API を並列で叩いて一部が失敗しても全体は継続する場合は `console.warn` で残す:

```tsx
try {
  const tj = await api.getTilesetTileJSON(id);
  setTileJSON(tj);
} catch {
  // TileJSON 取得失敗しても詳細ページは表示する想定 (期待される partial failure)。
  console.warn("TileJSON fetch failed, but continuing without it");
}
```

## 7. fire-and-forget と UI ブロッキング

### 7.1 UI 反映と DB 永続化を分ける

UX 上、ユーザー操作の即時フィードバック (cookie / state 更新) は同期的に行い、DB 永続化は **fire-and-forget** で投げる。API レイテンシで UI 反映を遅延させない:

```tsx
const switchTo = (locale: Locale) => {
  // 1) cookie は同期で書く
  document.cookie = `${LOCALE_COOKIE_NAME}=${locale}; ...`;

  // 2) DB 永続化は fire-and-forget。失敗は silent warn。
  void authClient.setPreferredLocale(locale).catch((err) => {
    console.warn("[useLocaleSwitcher] setPreferredLocale failed:", err);
  });

  // 3) startTransition は同期コールバックで呼ぶ (isPending 追跡のため)。
  startTransition(() => {
    router.refresh();
  });
};
```

### 7.2 `startTransition` は同期コールバックで呼ぶ

`startTransition(async () => { await ... })` は `await` 以降が transition 外で実行され、`isPending` が pending 状態を表さない (React の既知の挙動)。

## 8. E2E selector

### 8.1 testid を変更しない (catalog 化時)

i18n 化時にテキストは変わるが、`data-testid` は触らない。既存 E2E spec を破壊しない原則:

```tsx
// テキストだけ catalog 化、testid は維持
<Button data-testid="tileset-form-submit">
  {t("submit_create")}
</Button>
```

### 8.2 `getByText` を使う既存 E2E に注意

E2E 中の `getByText("ログイン")` は catalog 化で文字列が変わると壊れる。Phase 2 で多くを `getByTestId` に置き換え済みだが、残存する `getByText` は catalog 化時に併せて修正する。

## 9. 表記揺れの統一

複数箇所で同じ概念を扱う場合、表記を統一する。例:

| 概念 | 統一表記 (JA) | 統一表記 (EN) |
|---|---|---|
| Vector tile | ベクター (長音記号あり) | Vector |
| Raster tile | ラスター (長音記号あり) | Raster |
| Email | メールアドレス | Email |
| Password (n chars) | パスワード(8文字以上) | Password (8+ characters) |

新規 catalog を追加する際は、既存 namespace の似た文字列を grep して合わせること。`keysets.test.ts` は構造一致しか見ないため、内容の表記揺れは人手レビューが必要。

## 10. コメントは review-round を参照しない

PR レビューで修正したコードのコメントに `"(Copilot PR #N round M 指摘)"` のような review-round 参照を入れない (`CLAUDE.md` の規約: コメントは現在の task/fix を参照しない)。理由は **PR description に書く**。

```tsx
// ❌ DO NOT
// region 付き BCP47 タグの方が安定 (Copilot PR #132 round 1 指摘)

// ✓
// region 付き BCP47 タグの方が toLocaleString の表示が安定する。
```

## 11. 関連リファレンス

- [next-intl docs](https://next-intl-docs.vercel.app/) — ICU 構文、useTranslations / getTranslations の使い分け
- `app/src/i18n/config.ts` — 現在の locales / namespaces 一覧
- `app/src/locales/__tests__/keysets.test.ts` — missing-key CI チェック
- `app/.github/workflows/scripts/i18n_guard.py` — 公開 API / MCP 表面の JA 漏れ検出 (本規約とは別系統だが関連)
