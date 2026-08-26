/**
 * geo-base Admin 共通型定義
 */

// APIからの型をre-export
export type {
  Tileset,
  TilesetCreate,
  TilesetUpdate,
  Feature,
  FeatureCreate,
  FeatureUpdate,
  TileJSON,
  HealthStatus,
  ApiError,
} from "@/lib/api";

// ページネーション
export interface PaginationParams {
  page?: number;
  limit?: number;
  offset?: number;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  limit: number;
  hasMore: boolean;
}

// フィルター
export interface TilesetFilter {
  type?: 'vector' | 'raster' | 'pmtiles';
  is_public?: boolean;
  search?: string;
}

export interface FeatureFilter {
  tileset_id?: string;
  layer_name?: string;
  bbox?: string;
}

// フォーム状態
export interface FormState {
  isSubmitting: boolean;
  error: string | null;
}
