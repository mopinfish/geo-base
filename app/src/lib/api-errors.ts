/**
 * API error code → 日本語メッセージのマッピング (i18n Phase 2b / Issue #106)。
 *
 * Backend (`api/lib/errors.py`) は `{error: {code, message, details?}}` の
 * envelope を返す。本モジュールは `code` をキーに日本語メッセージへ訳出する。
 *
 * 旧来の `{detail: "..."}` レスポンスも依然返り得る (Phase 2b 期間中の段階
 * 移行 + 401 など `headers=` 保持のため意図的に envelope 化見送りの 15 件)
 * ので、`extractApiError()` は両方を許容する形にしている。
 *
 * Phase 3 (`next-intl` 導入) では `JA_MESSAGES` を
 * `app/src/locales/ja/api-errors.json` に移管する想定。本ファイルの key
 * 設計 (= ErrorCode.value) はそのまま JSON にコピーできる構造。
 */

/** Backend `{error: {code, message, details?}}` の構造 */
export interface ApiErrorPayload {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

/** UI が catch しやすいよう Error を継承 */
export class ApiClientError extends Error {
  readonly code: string;
  readonly details?: Record<string, unknown>;

  constructor(payload: ApiErrorPayload) {
    super(payload.message);
    this.name = "ApiClientError";
    this.code = payload.code;
    this.details = payload.details;
  }
}

/**
 * fetch のレスポンス JSON から API error を抽出する。
 *
 * 戻り値の優先順:
 * 1. envelope `{error: {code, message, details?}}` → ApiClientError
 * 2. legacy `{detail: "..."}` → 通常の Error (code 無し)
 * 3. それ以外 → null (呼び出し側で fallback メッセージ)
 */
export function extractApiError(body: unknown): ApiClientError | Error | null {
  if (!body || typeof body !== "object") return null;
  const obj = body as Record<string, unknown>;

  // envelope shape
  const envelope = obj.error;
  if (envelope && typeof envelope === "object") {
    const env = envelope as Record<string, unknown>;
    if (typeof env.code === "string" && typeof env.message === "string") {
      return new ApiClientError({
        code: env.code,
        message: env.message,
        details: (env.details ?? undefined) as
          | Record<string, unknown>
          | undefined,
      });
    }
  }

  // legacy `detail` shape
  if (typeof obj.detail === "string") {
    return new Error(obj.detail);
  }

  return null;
}

/**
 * 日本語フォールバック辞書。`api/lib/errors.py:ErrorCode` の全 value を含む。
 * Phase 3 で next-intl の JSON catalog に置き換える。
 *
 * 既存ユーザー体験を維持するために、英語 message そのままではなく日本語に
 * 訳出する。新規 code 追加時はここに同期させる責任が PR 作成者にある
 * (CI 等での強制は将来検討)。
 */
const JA_MESSAGES: Record<string, string> = {
  // auth
  auth_invalid_credentials: "メールアドレスまたはパスワードが正しくありません",
  auth_forbidden: "この操作を実行する権限がありません",
  auth_unauthorized: "ログインが必要です",
  auth_token_expired: "セッションの有効期限が切れました。再度ログインしてください",
  auth_token_invalid: "認証トークンが無効です",
  auth_refresh_failed: "セッションの更新に失敗しました。再度ログインしてください",
  auth_rate_limited: "ログイン試行回数が多すぎます。しばらく時間を置いてください",
  auth_user_already_exists: "このメールアドレスは既に登録されています",
  auth_user_not_found: "ユーザーが見つかりません",
  auth_weak_password: "パスワードが脆弱です。より複雑なものを設定してください",
  auth_origin_not_allowed: "このオリジンからのアクセスは許可されていません",
  auth_invitation_not_found: "招待が見つかりません",
  auth_invitation_invalid: "招待が無効です",
  auth_invitation_expired: "招待の有効期限が切れています",
  auth_provider_error: "認証プロバイダーでエラーが発生しました",

  // tileset
  tileset_not_found: "タイルセットが見つかりません",
  tileset_forbidden: "このタイルセットへのアクセス権限がありません",
  tileset_name_conflict: "同名のタイルセットが既に存在します",
  tileset_layer_not_found: "指定したレイヤーがタイルセットに存在しません",
  tileset_invalid: "タイルセットの内容が不正です",

  // feature
  feature_not_found: "フィーチャーが見つかりません",
  feature_invalid_geometry: "ジオメトリの形式が不正です",
  feature_forbidden: "このフィーチャーへのアクセス権限がありません",

  // datasource
  datasource_not_found: "データソースが見つかりません",
  datasource_forbidden: "このデータソースへのアクセス権限がありません",
  datasource_upload_failed: "ファイルのアップロードに失敗しました",
  datasource_unsupported_format: "対応していないファイル形式です",
  datasource_invalid: "データソースの内容が不正です",
  datasource_already_exists: "同じデータソースが既に存在します",

  // team
  team_not_found: "チームが見つかりません",
  team_forbidden: "このチームへのアクセス権限がありません",
  team_owner_required: "この操作はチームのオーナーのみ可能です",
  team_member_exists: "既にこのチームのメンバーです",
  team_member_not_found: "メンバーが見つかりません",
  team_invitation_not_found: "招待が見つかりません",
  team_invitation_expired: "招待の有効期限が切れています",
  team_invitation_already_used: "招待は既に使用済みです",
  team_invitation_already_exists: "この招待は既に存在します",
  team_invitation_email_mismatch: "招待先のメールアドレスと一致しません",
  team_invitation_invalid_status: "招待の状態が不正です",
  team_invalid: "チームの内容が不正です",
  team_tileset_already_shared: "このタイルセットは既にチームと共有されています",

  // api_key
  api_key_not_found: "API キーが見つかりません",
  api_key_forbidden: "この API キーへのアクセス権限がありません",
  api_key_revoked: "この API キーは無効化されています",
  api_key_expired: "この API キーは期限切れです",
  api_key_invalid_scope: "この操作に必要な権限が API キーに含まれていません",
  api_key_invalid: "API キーが不正です",

  // tile
  tile_not_found: "タイルが見つかりません",
  tile_invalid_coordinate: "タイル座標が不正です",
  tile_render_failed: "タイルの描画に失敗しました",
  tile_source_unavailable: "タイルのソースに接続できません",
  tile_service_unavailable: "タイル配信サービスが利用できません",

  // colormap
  colormap_not_found: "指定したカラーマップが見つかりません",

  // validation
  validation_field_required: "必須項目が入力されていません",
  validation_invalid_value: "入力値が不正です",
  validation_out_of_range: "値が範囲外です",
  validation_invalid: "入力内容が不正です",

  // internal
  internal_db_error: "データベースエラーが発生しました",
  internal_storage_error: "ストレージエラーが発生しました",
  internal_unexpected: "想定外のエラーが発生しました",
};

/**
 * ApiClientError または一般 Error をユーザー向け日本語メッセージに変換する。
 *
 * - `ApiClientError` で `code` が `JA_MESSAGES` にあれば日本語訳を返す
 * - `code` が未知なら英語 `message` をそのまま返す (forward-compat)
 * - `ApiClientError` でなければ `error.message` をそのまま返す
 *
 * Phase 3 で next-intl に置き換える際、本関数は `useTranslations()` 呼び出しに
 * 差し替える。`JA_MESSAGES` キー == ErrorCode value の構造を維持していれば
 * 機械的に JSON 移行可能。
 */
export function translateApiError(err: unknown): string {
  if (err instanceof ApiClientError) {
    return JA_MESSAGES[err.code] ?? err.message;
  }
  if (err instanceof Error) return err.message;
  return "予期しないエラーが発生しました";
}
