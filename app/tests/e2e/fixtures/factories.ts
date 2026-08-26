/**
 * E2E テスト用シードファクトリ。
 *
 * 各関数は POST <endpoint> を叩いてサーバから ID 付きエンティティを返す。
 * Playwright 側に SQL を散らさず、API レイヤーで境界を持たせる方針。
 *
 * NOTE: API contract と Phase 1 plan のシグネチャがいくつかズレている部分は
 * ファクトリ側で吸収している:
 *
 * - `TilesetCreate` は `format` が必須 (vector→pbf, raster→png, pmtiles→pbf)。
 *   呼び出し側に強制せず、`type` から既定を導く。
 * - `DatasourceCreate` は `tileset_id` 必須で、`name` / `is_public` フィールドは
 *   存在しない (それらは親 tileset の責務)。`tilesetId` を省略した場合は
 *   `name` を使って親 tileset を自動作成する。
 */
import { createApiClient } from "./api-client";

export interface CreatedTileset {
  id: string;
  name: string;
  type: string;
  format: string;
  is_public: boolean;
}

export interface CreatedDatasource {
  id: string;
  tileset_id: string;
  url: string;
  type: string;
}

export interface CreatedTeam {
  id: string;
  name: string;
  slug: string;
}

type TilesetType = "vector" | "raster" | "pmtiles";
type DatasourceType = "pmtiles" | "cog";

function defaultFormatForType(type: TilesetType): string {
  switch (type) {
    case "raster":
      return "png";
    case "pmtiles":
    case "vector":
    default:
      return "pbf";
  }
}

/**
 * `type` から親 tileset の type を逆算する。
 * pmtiles datasource → pmtiles tileset、cog datasource → raster tileset。
 */
function tilesetTypeForDatasource(type: DatasourceType): TilesetType {
  return type === "cog" ? "raster" : "pmtiles";
}

export async function createTileset(input: {
  name: string;
  type?: TilesetType;
  format?: string;
  isPublic?: boolean;
}): Promise<CreatedTileset> {
  const ctx = await createApiClient();
  try {
    const type = input.type ?? "vector";
    const res = await ctx.post("/api/tilesets", {
      data: {
        name: input.name,
        type,
        format: input.format ?? defaultFormatForType(type),
        is_public: input.isPublic ?? false,
      },
    });
    if (!res.ok()) {
      throw new Error(
        `createTileset failed: ${res.status()} ${await res.text()}`,
      );
    }
    return (await res.json()) as CreatedTileset;
  } finally {
    await ctx.dispose();
  }
}

export async function createDatasource(input: {
  name: string;
  url: string;
  type?: DatasourceType;
  isPublic?: boolean;
  tilesetId?: string;
}): Promise<CreatedDatasource> {
  const type = input.type ?? "pmtiles";

  // `tilesetId` が無ければ親 tileset を作って紐付ける。Phase 1 plan の
  // `createDatasource({ name, url, type })` 呼び出しを成立させるための糖衣。
  let tilesetId = input.tilesetId;
  if (!tilesetId) {
    const parent = await createTileset({
      name: input.name,
      type: tilesetTypeForDatasource(type),
      isPublic: input.isPublic,
    });
    tilesetId = parent.id;
  }

  const ctx = await createApiClient();
  try {
    const res = await ctx.post("/api/datasources", {
      data: {
        tileset_id: tilesetId,
        type,
        url: input.url,
      },
    });
    if (!res.ok()) {
      throw new Error(
        `createDatasource failed: ${res.status()} ${await res.text()}`,
      );
    }
    return (await res.json()) as CreatedDatasource;
  } finally {
    await ctx.dispose();
  }
}

export async function createTeam(input: {
  name: string;
  slug?: string;
}): Promise<CreatedTeam> {
  const ctx = await createApiClient();
  try {
    const res = await ctx.post("/api/teams", {
      data: { name: input.name, slug: input.slug },
    });
    if (!res.ok()) {
      throw new Error(`createTeam failed: ${res.status()} ${await res.text()}`);
    }
    return (await res.json()) as CreatedTeam;
  } finally {
    await ctx.dispose();
  }
}

/**
 * Feature レスポンスは GeoJSON Feature 形式。`tileset_id` は top-level に
 * 存在せず、`properties.layer_name` に layer 名が射影される
 * (`api/lib/routers/features.py` の create_feature 参照)。
 * 呼び出し側で tileset_id が必要な場合は、リクエスト時の値を保持しておくこと。
 */
export interface CreatedFeature {
  id: string;
  type: "Feature";
  geometry: unknown;
  properties: Record<string, unknown>;
}

export async function createFeature(input: {
  tilesetId: string;
  layer: string;
  geometry: unknown;
  properties?: Record<string, unknown>;
}): Promise<CreatedFeature> {
  const ctx = await createApiClient();
  try {
    // API は `layer_name` を受け取る (FeatureCreate モデル)。Phase 1 plan の
    // `layer` フィールドはこちらに射影する。
    const res = await ctx.post("/api/features", {
      data: {
        tileset_id: input.tilesetId,
        layer_name: input.layer,
        geometry: input.geometry,
        properties: input.properties ?? {},
      },
    });
    if (!res.ok()) {
      throw new Error(`createFeature failed: ${res.status()} ${await res.text()}`);
    }
    return (await res.json()) as CreatedFeature;
  } finally {
    await ctx.dispose();
  }
}

/**
 * 作成直後の API キー。`key` は POST /api/api-keys のレスポンスでのみ返り、
 * 以降の GET では取得できない平文 key (ApiKeyCreatedResponse 参照)。
 */
export interface CreatedApiKey {
  id: string;
  name: string;
  prefix: string;
  // 作成直後だけ返ってくる平文 key
  key?: string;
}

export async function createApiKey(input: {
  name: string;
  scopes?: string[];
  /**
   * 作成時に有効期限を付ける場合の日数 (1..365)。`ApiKeyCreate.expires_in_days`
   * に射影される。過去日付の expires_at を作りたい場合は本フィールドではなく、
   * `expireApiKey` (test_helpers) を使って既存キーを更新する。
   */
  expiresInDays?: number;
}): Promise<CreatedApiKey> {
  const ctx = await createApiClient();
  try {
    const data: Record<string, unknown> = {
      name: input.name,
      scopes: input.scopes ?? ["read"],
    };
    if (input.expiresInDays !== undefined) {
      data.expires_in_days = input.expiresInDays;
    }
    const res = await ctx.post("/api/api-keys", { data });
    if (!res.ok()) {
      throw new Error(`createApiKey failed: ${res.status()} ${await res.text()}`);
    }
    return (await res.json()) as CreatedApiKey;
  } finally {
    await ctx.dispose();
  }
}

/**
 * E2E 専用: 既存 API キーの `expires_at` を過去日時に書き換える。
 * `ApiKeyCreate.expires_in_days` は 1..365 の正の範囲しか許さないので、
 * 「すでに期限切れ」の状態を作るために test_helpers エンドポイントを使う。
 */
export async function expireApiKey(input: {
  keyId: string;
  minutesAgo?: number;
}): Promise<void> {
  // test_helpers は API_BASE 側の `/api/test/api-keys/expire` に同居している。
  // resetDatabase と同じく認証不要の request context で直接叩く。
  const { request } = await import("@playwright/test");
  const apiBase = process.env.PLAYWRIGHT_API_BASE_URL || "http://localhost:8000";
  // utils/reset-db.ts と utils/token-fetch.ts と同じく、非認証 test endpoint を
  // 本番に向けて叩かないよう localhost guard を入れる (Copilot PR #122 指摘)。
  const apiHost = new URL(apiBase).hostname;
  if (!["localhost", "127.0.0.1"].includes(apiHost)) {
    throw new Error(
      `Refusing to call /api/test/api-keys/expire against non-local host: ${apiHost}`,
    );
  }
  const ctx = await request.newContext({ baseURL: apiBase });
  try {
    const res = await ctx.post("/api/test/api-keys/expire", {
      data: {
        key_id: input.keyId,
        minutes_ago: input.minutesAgo ?? 60,
      },
    });
    if (!res.ok()) {
      throw new Error(
        `expireApiKey failed: ${res.status()} ${await res.text()}`,
      );
    }
  } finally {
    await ctx.dispose();
  }
}

/**
 * Team 招待を作成する。`token` は created レスポンスに含まれる
 * (`api/lib/routers/teams.py` の create_team_invitation 参照)。
 * 招待を受諾するには `/accept-invitation?token=...` 経由でフロントから入る
 * か、authClient.acceptInvitation を直接叩く。
 *
 * NOTE: `expires_in_days` を渡す場合は 1..30 の範囲 (TeamInvitationCreate)。
 */
export interface CreatedInvitation {
  id: string;
  team_id: string;
  email: string;
  /** 招待 token (受諾前のみ存在)。pending → accepted/expired/cancelled で NULL に書き換えられる。 */
  token: string | null;
  role: string;
  status: string;
}

export type TeamInviteRole = "administrator" | "member" | "guest";

export async function inviteMember(input: {
  teamId: string;
  email: string;
  role?: TeamInviteRole;
}): Promise<CreatedInvitation> {
  const ctx = await createApiClient();
  try {
    const res = await ctx.post(`/api/teams/${input.teamId}/invitations`, {
      data: {
        email: input.email,
        role: input.role ?? "member",
      },
    });
    if (!res.ok()) {
      throw new Error(
        `inviteMember failed: ${res.status()} ${await res.text()}`,
      );
    }
    return (await res.json()) as CreatedInvitation;
  } finally {
    await ctx.dispose();
  }
}
