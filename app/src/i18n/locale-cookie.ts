/**
 * Locale cookie constants (Phase 3 / Issue #107).
 *
 * `proxy.ts` がリクエスト受信時に解決して set し、`i18n/request.ts` が
 * Server Components 時に読む。Client Component 側で言語切替時にも同じ名前で
 * cookie を上書きする。
 */

/** Cookie 名は spec 5.3 で定義された `NEXT_LOCALE` を採用 (next-intl 互換)。 */
export const LOCALE_COOKIE_NAME = "NEXT_LOCALE";

/** 1 年 (秒)。expire = 1 year で書く。 */
export const LOCALE_COOKIE_MAX_AGE = 60 * 60 * 24 * 365;
