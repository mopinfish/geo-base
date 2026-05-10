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
