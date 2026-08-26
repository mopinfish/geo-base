-- i18n Phase 3 (Issue #107):
-- `users.preferred_locale` カラム追加。null 許容 (= cookie / Accept-Language
-- フォールバック)。ユーザーが Admin UI から言語切替したときに API
-- (PATCH /api/auth/me/locale) 経由で更新される。
--
-- 初期は 'en' / 'ja' の 2 値だが、将来 3 言語目以降を追加する想定で
-- CHECK 制約は付けない (アプリ層で許容 locale を検証する)。
-- VARCHAR(8) は BCP 47 の最小ケース (`en`, `ja`) と将来の `en-US` 等を
-- 想定した余裕長。

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS preferred_locale VARCHAR(8);

COMMENT ON COLUMN users.preferred_locale IS
    'User-selected UI locale (e.g. ja, en). NULL means fall back to cookie / Accept-Language. See Issue #107.';
