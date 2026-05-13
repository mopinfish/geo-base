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
 * - `auth`: 認証系画面 (login / password-reset / invitation) の UI 文言
 *   (Phase 3c / Issue #107)。
 * - `tilesets`: タイルセット系画面 (一覧 / 新規 / 詳細 / 編集 + form +
 *   delete dialog) の UI 文言 (Phase 3d / Issue #107)。
 * - `features`: フィーチャー系画面 (一覧 / 新規 / 詳細 / 編集 / インポート + form +
 *   dialog) の UI 文言 (Phase 3e / Issue #107)。
 *
 * PR-E 以降 (features / datasources / ...) で domain 別に namespace を追加していく。
 */
export const NAMESPACES = ["common", "api-errors", "auth", "tilesets", "features"] as const;
export type Namespace = (typeof NAMESPACES)[number];
