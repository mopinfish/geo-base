# アクセス制御仕様 レビュー（2026-05-09 時点）

geo-base のアクセス制御は **認証** (Phase 3 / Step 3.3-A プラガブル認証) と **認可** (チーム / API キー / タイルセット共有) の組み合わせで構成される。本ドキュメントは **現状の実装からの逆引き** で仕様を整理し、運用上のリスクと改善ポイントをレビューする。

> 関連ドキュメント:
> - 認証本体: [`AUTH_SETUP.md`](./AUTH_SETUP.md)
> - スペック (設計): [`superpowers/specs/2026-05-08-pluggable-auth-design.md`](./superpowers/specs/2026-05-08-pluggable-auth-design.md)
> - DB スキーマ: `docker/postgis-init/04_auth_schema.sql`, `05_teams_schema.sql`, `06_api_keys_schema.sql`

---

## 1. データモデル

```
users (auth)                                   teams
  id (uuid)                                      id (uuid)
  email                                          name, slug, description
  role (admin | authenticated)                   owner_user_id → users.id
  password_hash                                  
                                              team_members
tilesets                                        team_id, user_id
  id (uuid)                                     role (owner | administrator | member | guest)
  user_id → users.id     (NULL = orphan)        joined_at
  is_public (BOOLEAN)
  metadata               (JSONB)              team_invitations
                                                team_id, email
team_tilesets                                   token (unique)
  team_id, tileset_id                           role, expires_at, status
  permission_level (read|write|admin)           (pending | accepted | expired | cancelled)
  added_by_user_id

api_keys                                      api_key_rate_limits
  id, user_id (owner), team_id (NULL=personal)  api_key_id, window_minute, count
  name, key_hash (sha256), key_prefix         api_key_usage_logs
  scopes TEXT[] (read|write|delete|admin)       api_key_id, endpoint, status_code, ts
  rate_limit_per_minute, rate_limit_per_day
  is_active, expires_at, revoked_at
```

**所有・共有モデル:**
- タイルセットは **個人所有** (`user_id` 設定 + `team_tilesets` 行なし) と **チーム共有** (`team_tilesets` 経由) が併存
- `is_public=true` で誰でも読める公開タイルセットになる（書き込みは別途認可必須）
- API キーは **個人キー** (`team_id IS NULL`) と **チームキー** (`team_id` 紐付け) の 2 種類

---

## 2. 認証コンテキスト

### `Depends` の使い分け（`api/lib/auth/__init__.py`）

| Dependency | JWT | API キー | 認証必須 | 用途 |
|---|---|---|---|---|
| `require_auth` | ✓ | ✗ | ✓ | ユーザーが必須なエンドポイント (writes, /me 等) |
| `get_current_user` | ✓ | ✗ | – | 任意認証（公開リソースの読み取りで「誰が読んだか」判別したい場面） |
| `require_auth_context` | ✓ | ✓ | ✓ | JWT または API キーで認証必須（タイル配信など） |
| `get_auth_context_optional` | ✓ | ✓ | – | 任意認証だが API キー対応版 |

### `AuthContext` の中身

```python
@dataclass
class AuthContext:
    user_id: str | None
    is_api_key: bool
    api_key_id: str | None       # API キー時のみ
    team_id: str | None          # API キーの team_id (個人キーは None)
    scopes: list[str]            # JWT は ["read","write","delete","admin"] を持つ
```

- **JWT 経由**: `AuthContext.from_jwt_user(user)` → 全スコープ付与
- **API キー経由**: `AuthContext.from_api_key(record)` → DB の `scopes` 配列をそのまま採用
- `has_scope("read")` は **階層判定** (admin > delete > write > read)

---

## 3. チームロール権限マトリクス

> 凡例: ✅ 可 / ❌ 不可 / ⚠️ 一部条件付き

| 操作 | owner | administrator | member | guest |
|---|---|---|---|---|
| **チーム情報** |  |  |  |  |
| 一覧表示 | ✅ | ✅ | ✅ | ✅ |
| 詳細表示 | ✅ | ✅ | ✅ | ✅ |
| 名前 / slug / description 変更 | ✅ | ✅ | ❌ | ❌ |
| チーム削除 | ✅ | ❌ | ❌ | ❌ |
| 所有権譲渡 (`transfer-ownership`) | ✅ | ❌ | ❌ | ❌ |
| **メンバー** |  |  |  |  |
| メンバー一覧 | ✅ | ✅ | ✅ | ✅ |
| ロール変更 | ✅ | ✅ (※owner 除く) | ❌ | ❌ |
| メンバー削除 (他人) | ✅ | ✅ (※owner 除く) | ❌ | ❌ |
| 自分自身の削除 | ❌ (transfer 必須) | ✅ | ✅ | ✅ |
| **招待** |  |  |  |  |
| 招待リスト表示 | ✅ | ✅ | ❌ | ❌ |
| 招待発行 | ✅ | ✅ | ❌ | ❌ |
| 招待キャンセル | ✅ | ✅ | ❌ | ❌ |
| 招待受諾 | – | – | – | – (email 一致した user 全員) |
| **チームタイルセット (`team_tilesets`)** |  |  |  |  |
| 一覧表示 | ✅ | ✅ | ✅ | ✅ |
| 追加 (`POST /api/teams/{team_id}/tilesets`) | ✅ | ✅ | ❌ | ❌ |
| 削除 (`DELETE /api/teams/{team_id}/tilesets/{tileset_id}`) | ✅ | ✅ | ❌ | ❌ |

> 追加と削除の権限は Issue #54 (案 B) で `[OWNER, ADMINISTRATOR]` に統一済み（2026-05-11）。member 以下は team-shared なタイルセットの「利用（読み取り / 配信）」のみ可能。

実装: `api/lib/routers/teams.py` の `check_team_permission(conn, team_id, user_id, required_roles)` が `team_members` から取得した `role` を `required_roles` (Python の `list[TeamRole]`) に含めるかで真偽を返す。各エンドポイントが必要なロール集合を明示的に渡すスタイル。member/guest 区別は不徹底（後述）。

---

## 4. タイルセットアクセス制御マトリクス

### 読み取り (GET) — `check_tileset_access_v2()` 経由のもの

| 主体 | 公開 (is_public=true) | 自分の個人タイル (user_id=me) | チーム共有 (team_tilesets 経由で所属) | 他人 / 他チーム |
|---|---|---|---|---|
| 未認証 | ✅ | ❌ (401) | ❌ | ❌ |
| JWT (個人) | ✅ | ✅ | ✅ | ❌ (403) |
| JWT (member) | ✅ | ✅ | ✅ | ❌ |
| API キー (個人, scope=read) | ✅ | ✅ (キー所有者と一致時) | ❌ (個人キーはチーム不参照) | ❌ |
| API キー (チーム, scope=read) | ✅ | ❌ | ✅ (キーの team_id と一致時) | ❌ |

**実装場所:**
- `api/lib/auth/__init__.py:check_tileset_access_v2()` が AuthContext + tileset 行を受け取り bool を返す
- 適用ルート: `api/lib/routers/tilesets.py` の GET 系、`api/lib/routers/tiles/*.py` 全般

⚠️ **`api/lib/routers/features.py`** および **`api/lib/routers/datasources.py`** はまだ旧版の `check_tileset_access()` を使用しており、**チーム共有を考慮していない**（C-3 参照）。

> **注**: `is_public=true` は **認証 / CORS / レート制限すべてを素通りする恒久的な公開設定** であり、未認証アクセス時の保護機構もアプリ層には存在しない。一度公開したタイルは CDN / クライアントキャッシュに残るため、`is_public` を後から false に戻しても完全には取り戻せない。商用埋め込み濫用や bot による大量取得の余地も含め、設定時は影響範囲を確認すること。詳細は §7 M-7 参照。

### 書き込み (POST / PATCH / DELETE)

| 主体 | 個人タイル新規作成 | 自分の個人タイル更新 / 削除 | チーム共有タイルの更新 / 削除 | 他人のタイル |
|---|---|---|---|---|
| 未認証 | ❌ | ❌ | ❌ | ❌ |
| JWT (任意) | ✅ | ✅ | ❌ ⚠️ | ❌ |
| API キー | ❌ ⚠️ | ❌ ⚠️ | ❌ ⚠️ | ❌ |

**実装場所:**
- `api/lib/routers/tilesets.py:625, 727, 845` — いずれも `if str(row[1]) != user.id: raise 403` の **単純 owner 比較**
- 書き込み系は **`require_auth`** で JWT 必須（API キー不可）

⚠️ **重要**: チームメンバー（member 含む owner/admin でも）が **チーム共有タイルセット（team_tilesets 経由）を編集する経路が未実装**。`team_tilesets.permission_level` カラムや `can_user_perform_action()` SQL 関数は **DB 側に定義済みだがアプリから一切呼ばれていない**。

---

## 5. API キー権限モデル

### スコープ階層

| スコープ | 包含する操作 |
|---|---|
| `read` | GET 系 |
| `write` | `read` + POST / PATCH |
| `delete` | `write` + DELETE |
| `admin` | 全操作（API キー管理含む） |

`AuthContext.has_scope(required)` は `LEVEL = {read:1, write:2, delete:3, admin:4}` で `max_level >= required_level` を判定（`api/lib/auth/context.py`）。

### キー種別

| 種別 | `team_id` | アクセス可能リソース | 管理可能ユーザー |
|---|---|---|---|
| 個人キー | NULL | 所有者の個人タイルセット + 公開タイルセット | キー所有者本人のみ |
| チームキー | 紐付けあり | チーム共有タイルセット + 公開タイルセット | チームの owner/admin |

### レート制限

- `rate_limit_per_minute` (デフォルト 60) と `rate_limit_per_day` (デフォルト 10000)
- DB の `api_key_rate_limits` テーブルでウィンドウごとの count を管理
- 超過時 `RateLimited` → 429 を返す

### 検証フロー (`api/lib/auth/api_key_auth.py`)

1. リクエストの `Authorization: Bearer gb_xxx...` ヘッダから抽出
2. SHA-256 ハッシュで DB lookup
3. `is_active = true AND revoked_at IS NULL AND (expires_at IS NULL OR expires_at > NOW())` で有効性確認
4. レート制限チェック
5. `AuthContext.from_api_key()` 構築
6. `last_used_at` 更新 + 使用ログ記録

---

## 6. 招待フロー

```
1. POST /teams/{id}/invitations  (owner / admin)
   → token = secrets.token_urlsafe(32)  (~64 文字)
   → expires_at = now() + 7 days
   → status = "pending"
   → メール送信（失敗しても招待 DB は残る）

2. GET /api/auth/invitations/{token}  (公開エンドポイント)
   → チーム情報・既存ユーザー有無を返す（パスワードフォーム表示判定用）

3. POST /api/auth/accept-invitation  (token + password + name)
   → token 有効 / pending / expires_at > now() 確認
   → email 一致確認 (lower-case)
   → サインアップ → team_members に INSERT
   → 自動ログイン (JWT 発行)

4. DELETE /teams/{id}/invitations/{invitation_id}  (owner / admin)
   → status = "cancelled"
```

email の検証は受諾時のみ (`api/lib/routers/teams.py:743-744`):
```python
if user.email.lower() != invitation.email.lower():
    raise HTTPException(403, "Invitation email mismatch")
```

---

## 7. セキュリティレビュー

### 🔴 Critical（本番運用前に対応推奨）

#### C-1. チーム所有タイルセットの書き込み権限が破綻している

**症状:** `team_tilesets` 経由で共有されたタイルセットを、**所有者以外のチームメンバー（owner/admin/member 全て）が更新・削除できない**。

`api/lib/routers/tilesets.py:625, 727, 845` の判定は:
```python
if str(row[1]) != user.id:  # row[1] = tilesets.user_id
    raise HTTPException(403, ...)
```

`team_tilesets.permission_level` も DB 関数 `can_user_perform_action()` も無視されている。

**影響:** 「team owner が編集できないチームタイルセット」が発生し、チーム共有が事実上 read-only。

**対応:** `check_tileset_write_access_v2()` 相当を新設し、`(user_id == owner) OR (team_tilesets で write 以上の permission)` で判定する。

#### C-2. API キーで write/delete 操作ができない

`require_auth` を使う書き込み系はすべて JWT 必須。**`write`/`delete` スコープを持つ API キーは事実上 read 専用** で、外部システム連携（CI からのタイルアップロードなど）が不可能。

**対応:** `require_auth_context` + `ctx.has_scope("write")` 系チェックに置換。`POST/PATCH/DELETE /api/tilesets/*` および `/api/features/*` の代表的なエンドポイントに適用。

#### C-3. `features` / `datasources` のチーム共有読み取り未対応

両 router は `check_tileset_access()` (旧版) のみ使用。チームメンバーが共有タイルセットの **個別フィーチャー** や **データソース詳細** を読めない。

**対応:** `check_tileset_access_v2()` に統一する。

**MCP 経由への波及:** MCP サーバー (`mcp/tools/`) は本 API への薄いプロキシで、`mcp/config.py` の `api_token` を `Authorization: Bearer ...` でそのまま転送するだけの構造。MCP 側に独自の認可ロジックは無く、API 側の `Depends()` が認証可否を決めるため、C-3 が解消されるまで以下の MCP ツールはチーム共有タイルセットを扱えない（API キー・JWT いずれでも個人所有タイルセットしか見えない）:

- `features.search_features` / `features.get_feature` (`GET /api/features[/{id}]`)
- `stats.*` 4 ツール（内部で `GET /api/features` を呼び出す）
- `analysis.*` 3 ツール（同上）
- C-2 解消までは `crud.*` の write/delete 系も JWT 必須

問題なく動くのは `tilesets.list_tilesets` / `get_tileset` / `get_tilejson` などタイルセットメタデータ系のみ。Issue #51 の動作確認チェックリストには **MCP 経由の動作確認も含めることを推奨**。

### 🟡 Important（早めに対応すべき）

#### I-1. メンバーがチームタイルセットを「追加」できるが「削除」できない非対称 ✅ 対応済み

`api/lib/routers/teams.py` の `add_team_tileset` (POST `/api/teams/{team_id}/tilesets`) は member も許可していたが、`remove_team_tileset` (DELETE `/api/teams/{team_id}/tilesets/{tileset_id}`) は owner/admin のみ。誤って追加したものを当人が取り消せなかった。

**対応（Issue #54、案 B）:** 追加側 (`add_team_tileset`) の `check_team_permission` から `TeamRole.MEMBER` を外し、削除側と同じ `[OWNER, ADMINISTRATOR]` に統一。「owner/admin = 管理、member = 利用」の境界を明確化。回帰テスト `api/tests/test_routers/test_team_tileset_permissions.py` で owner/admin/member × add/delete の 6 ケースを検証。

#### I-2. 招待トークンが受諾後も DB に残る

`team_invitations.status='accepted'` に遷移するだけで、token カラムは平文（hash 化なし）で保持され続ける。expires_at までの間に DB を盗まれた場合、再受諾は `team_members` の UNIQUE で防がれるが、**他の攻撃面（メール再送による誤誘導など）**に使える可能性。

**対応:** 受諾後に token を NULL にするか、'used' status を追加して expires_at < now() に縮める cleanup ジョブを回す。すでに `cleanup-expired` CLI はあるが定期実行が未運用 ([Issue #42](https://github.com/mopinfish/geo-base/issues/42))。

#### I-3. レート制限が DB 同期で書き込み競合を起こしうる

`api_key_rate_limits` を DB INSERT で集計するため、高頻度アクセスで lock contention が発生。本番想定のトラフィックでは Redis または in-memory アグリゲーション + 定期 flush が必要。

#### I-4. middleware の保護パスが deny-list (Issue #46)

既知。`/_internal` のような新規ルートを追加した時に保護漏れが起きやすい構造。allow-list 化は別 Issue で追跡中。

#### I-5. RLS のアプリ層連携が未完（Issue #44）

DB の RLS は permissive のまま、アプリ層認可で代替。`auth.uid()` 等の Supabase 固有関数への依存は Issue #72 Phase 1.5 (docker init / 本番 DB RLS 整理) でも併せて掃除する予定。元々のポータブル化トラッキングは [Issue #44](https://github.com/mopinfish/geo-base/issues/44)。

### 🟢 Minor（時間を見て対応）

#### M-1. owner ロール直接割り当ての二重防御不徹底

`TeamMemberAdd` バリデータで "Cannot assign owner role" を弾くが、`transfer-ownership` 経由ではバイパス可能（仕様）。ドキュメントで意図を明記すべき。

#### M-2. API キーの DELETE と revoke の使い分けがドキュメントなし

DELETE は物理削除（CASCADE で rate_limit / usage_logs まで消える）、`POST /revoke` は soft-delete。監査要件がある場合は DELETE を禁止する運用。

#### M-3. JWT に team_ids[] が含まれない

JWT 発行時に「現在所属しているチームの id 配列」を埋め込めば、毎リクエストで `team_members` SELECT が不要になる。ただし所属変更がトークン期限まで反映されない trade-off あり。

#### M-4. invitation の email case-insensitivity 不徹底

発行時は照合せず、受諾時のみ `.lower()` 比較。違う case で同じメールに重複招待が可能。`UNIQUE(team_id, lower(email), status)` 相当の index で根絶できる。

#### M-5. AuthContext.team_id が API キー専用

JWT 経由ではこのフィールドが NULL。混在環境で「現在のチームコンテキスト」を扱いたいなら、JWT の場合も `team_members` 参照ヘルパーを統一する。

#### M-6. API キーフォーマット検証が呼ばれていない

`validate_api_key_format()` 関数は定義だけで未使用。

#### M-7. 公開タイルセットに Origin 制限・レート制限・利用上限が一切無い

`is_public=true` のタイルセットは認証スキップ（`check_tileset_access_v2` の最初の分岐、`api/lib/auth/__init__.py:230-231`）に加え、CORS は `allow_origins=["*"]` 固定（`api/lib/cors_middleware.py` の public tier）。アプリ層レート制限は API キー認証時のみ機能するため、**未認証の公開タイル取得は実質無制限**。Origin / Referer ロックや利用回数上限の機構もアプリ層には未実装。

**影響:**

- 商用サイトへの無断埋め込みによる帯域コスト発生（Fly.io 帯域がそのまま課金される）
- `is_public` を false に戻しても CDN / クライアントキャッシュに残ったタイルは引き続き配信される（取り消し不能）
- DDoS 的な大量取得に対するアプリ層の防御線がない

**緩和策候補:**

- タイルセット単位の `allowed_origins TEXT[]` カラム追加 → CORS ミドルウェアで origin 検証
- 未認証アクセス向けの IP / `X-Forwarded-For` プレフィックスベースのソフトレート制限
- CDN レイヤー（Fly.io 前段に Cloudflare 等）でのリファラ・地域制限
- タイルセットに `daily_request_limit` を持たせ、超過時 429

---

## 8. 改善ロードマップ

| 優先度 | 項目 | 推奨アクション |
|---|---|---|
| 🔴 Critical | C-1 チームタイルセット書き込み | 新規 Issue 起票推奨 |
| 🔴 Critical | C-2 API キー write/delete | 新規 Issue 起票推奨 |
| 🔴 Critical | C-3 features/datasources チーム対応 | 新規 Issue 起票推奨 |
| 🟡 Important | I-1 メンバー追加/削除非対称 | ✅ 対応済み（Issue #54、案 B = 両方 owner/admin のみ） |
| 🟡 Important | I-2 招待 token 永続化 | Issue #42 (cleanup-expired) と合わせて対応 |
| 🟡 Important | I-3 レート制限 Redis 化 | 本番運用前に必須 |
| 🟡 Important | I-4 middleware allow-list | [Issue #46](https://github.com/mopinfish/geo-base/issues/46) |
| 🟡 Important | I-5 ポータブル RLS | [Issue #44](https://github.com/mopinfish/geo-base/issues/44) |
| 🟢 Minor | M-1〜M-6 | 必要に応じて |
| 🟢 Minor | M-7 公開タイルセットの濫用対策 | 商用埋め込み濫用が顕在化したタイミングで対応（Origin 制限 / 未認証レート制限 / CDN 層制御） |

---

## 9. 参考: 主要実装箇所

| ファイル | 行 | 内容 |
|---|---|---|
| `api/lib/auth/__init__.py` | `check_tileset_access_v2` | タイルセット読み取り認可（v2 = AuthContext 対応） |
| `api/lib/auth/context.py` | `AuthContext`, `has_scope` | 認証コンテキストの統一データ構造 |
| `api/lib/auth/api_key_auth.py` | `validate_api_key`, `verify_request` | API キー検証・レート制限・使用ログ |
| `api/lib/routers/teams.py` | `check_team_permission` (L76-79) | チームロール認可ヘルパー |
| `api/lib/routers/tilesets.py` | L625, 727, 845 | 書き込み系の owner 単純比較（C-1 起因箇所） |
| `api/lib/routers/api_keys.py` | L60-72, 189-194 | API キーの所有権確認、リスト取得 |
| `docker/postgis-init/05_teams_schema.sql` | L154-217 | `get_team_permission()`, `can_user_perform_action()`（**未呼出**） |
| `docker/postgis-init/06_api_keys_schema.sql` | L162-189 | `api_key_has_scope()` SQL 関数 |

---

## 改訂履歴

| 日付 | 著者 | 変更内容 |
|---|---|---|
| 2026-05-09 | Claude (audit) | 初版。Phase 3 / Step 3.3-A 完了時点の実装を逆引き、Critical 3 件・Important 5 件・Minor 6 件のレビュー所見をまとめ |
