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
  type?: "vector" | "raster";
  is_public?: boolean;
  search?: string;
}

export interface FeatureFilter {
  tileset_id?: string;
  layer?: string;
  bbox?: string;
  search?: string;
}

// ユーザー
export interface User {
  id: string;
  email: string;
  name?: string;
  avatar_url?: string;
  created_at: string;
}

// 認証状態
export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

// ナビゲーション
export interface NavItem {
  title: string;
  href: string;
  icon?: React.ComponentType<{ className?: string }>;
  disabled?: boolean;
  children?: NavItem[];
}

// テーブル
export interface Column<T> {
  key: keyof T | string;
  title: string;
  sortable?: boolean;
  render?: (value: unknown, item: T) => React.ReactNode;
}

// フォーム
export interface FormFieldProps {
  label: string;
  name: string;
  type?: string;
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
  error?: string;
  helperText?: string;
}
