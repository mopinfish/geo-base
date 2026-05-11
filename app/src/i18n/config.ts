/**
 * i18n config (Phase 3 / Issue #107).
 *
 * - サポート locale 一覧 (`LOCALES`)
 * - デフォルト locale (`DEFAULT_LOCALE`)
 * - Accept-Language フォールバック (`FALLBACK_LOCALE_FOR_ACCEPT_LANGUAGE`)
 * - namespace 一覧 (`NAMESPACES`) — `src/locales/<locale>/<ns>.json`
 *
 * 新しい namespace を追加した際は本配列にも追加すること
 * (missing-key Vitest テストが本配列を反復する)。
 */

export const LOCALES = ["en", "ja"] as const;
export type Locale = (typeof LOCALES)[number];

/** デフォルト locale (spec 5.3 の優先順位 4 番目)。 */
export const DEFAULT_LOCALE: Locale = "en";

/**
 * 既存日本語ユーザー保護のため、Cookie 未設定 + Accept-Language が空または
 * サポート外のときに「ja」を採用する (spec 11 リスク表「既存日本語ユーザーの
 * 体験劣化」緩和)。明示切替 (`preferred_locale` or `NEXT_LOCALE` cookie) が
 * 入っていればそちらが優先される。
 */
export const FALLBACK_LOCALE_FOR_ACCEPT_LANGUAGE: Locale = "ja";

/**
 * Catalog namespace 一覧。`src/locales/<locale>/<ns>.json` が実体。
 *
 * - `common`: 横断的 (app title / nav / button labels 等)
 * - `api-errors`: API code → user-facing message のマップ。Phase 2b の
 *   `app/src/lib/api-errors.ts:JA_MESSAGES` を JSON 化したもの。
 *
 * PR-C 以降 (auth / tilesets / features / ...) で domain 別に namespace を
 * 追加していく。
 */
export const NAMESPACES = ["common", "api-errors"] as const;
export type Namespace = (typeof NAMESPACES)[number];
