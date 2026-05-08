/**
 * geo-base タイルサーバー API クライアント
 */

// 環境変数からAPIのベースURLを取得
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://geo-base-api.fly.dev';

// ============================
// 基本型定義
// ============================

export interface Tileset {
  id: string;
  name: string;
  description?: string;
  type: 'vector' | 'raster' | 'pmtiles';
  format: 'pbf' | 'png' | 'webp' | 'jpg' | 'geojson';
  min_zoom?: number;
  max_zoom?: number;
  bounds?: number[];
  center?: number[];
  attribution?: string;
  is_public: boolean;
  owner_id?: string;
  created_at: string;
  updated_at: string;
  metadata?: Record<string, unknown>;
}

export interface TilesetCreate {
  name: string;
  description?: string;
  type: 'vector' | 'raster' | 'pmtiles';
  format: 'pbf' | 'png' | 'webp' | 'jpg' | 'geojson';
  min_zoom?: number;
  max_zoom?: number;
  bounds?: number[];
  center?: number[];
  attribution?: string;
  is_public?: boolean;
  metadata?: Record<string, unknown>;
}

export interface TilesetUpdate {
  name?: string;
  description?: string;
  min_zoom?: number;
  max_zoom?: number;
  bounds?: number[];
  center?: number[];
  attribution?: string;
  is_public?: boolean;
  metadata?: Record<string, unknown>;
}

export interface Feature {
  id: string;
  tileset_id: string;
  layer_name: string;
  properties: Record<string, unknown>;
  geometry: GeoJSON.Geometry;
  created_at: string;
  updated_at: string;
}

export interface FeatureCreate {
  tileset_id: string;
  layer_name?: string;
  properties?: Record<string, unknown>;
  geometry: GeoJSON.Geometry;
}

export interface FeatureUpdate {
  layer_name?: string;
  properties?: Record<string, unknown>;
  geometry?: GeoJSON.Geometry;
}

export interface BulkFeatureCreate {
  tileset_id: string;
  layer_name?: string;
  features: GeoJSON.Feature[];
}

export interface BulkFeatureResponse {
  success_count: number;
  failed_count: number;
  feature_ids: string[];
  errors: string[];
}

export interface TileJSON {
  tilejson: string;
  name: string;
  description?: string;
  version?: string;
  attribution?: string;
  tiles: string[];
  minzoom: number;
  maxzoom: number;
  bounds?: number[];
  center?: number[];
}

export interface HealthStatus {
  status: string;
  timestamp: string;
  environment?: string;
  database?: string;
  postgis?: string;
}

export interface ApiError {
  detail: string;
}

// ============================
// データソース型定義
// ============================

export type DatasourceType = 'pmtiles' | 'cog';
export type StorageProvider = 'supabase' | 's3' | 'http';

export interface Datasource {
  id: string;
  tileset_id: string;
  tileset_name: string;
  type: DatasourceType;
  url: string;
  storage_provider: StorageProvider;
  tile_type?: string;
  compression?: string;
  layers?: unknown[];
  band_count?: number;
  band_descriptions?: string[];
  native_crs?: string;
  native_resolution?: number;
  min_zoom?: number;
  max_zoom?: number;
  bounds?: number[] | Record<string, number>;
  center?: number[] | Record<string, number>;
  metadata?: Record<string, unknown>;
  is_public: boolean;
  user_id?: string;
  created_at: string;
  updated_at: string;
}

export interface DatasourceCreate {
  tileset_id: string;
  type: DatasourceType;
  url: string;
  storage_provider?: StorageProvider;
  metadata?: Record<string, unknown>;
}

export interface DatasourceTestResult {
  status: 'ok' | 'error';
  type: DatasourceType;
  url?: string;
  message?: string;
  metadata?: Record<string, unknown>;
  info?: Record<string, unknown>;
}

export interface CalculateBoundsResult {
  message: string;
  tileset_id: string;
  feature_count: number;
  bounds: number[] | null;
  center: number[] | null;
}

// ============================
// 統計API 型定義
// ============================

export interface SystemStats {
  tilesets: {
    total: number;
    by_type: Record<string, number>;
    public: number;
    private: number;
  };
  features: {
    total: number;
    by_geometry_type: Record<string, number>;
  };
  datasources: {
    pmtiles: number;
    raster: number;
    total: number;
  };
  top_tilesets_by_features: Array<{
    id: string;
    name: string;
    type: string;
    feature_count: number;
  }>;
}

export interface TilesetStats {
  tileset_id: string;
  tileset_name: string;
  tileset_type: string;
  feature_count: number;
  geometry_types: Record<string, number>;
  bounds: number[] | null;
  latest_update: string | null;
  message?: string;
}

// ============================
// バッチ操作 型定義
// ============================

export interface ExportRequest {
  tileset_id?: string;
  feature_ids?: string[];
  layer_name?: string;
  bbox?: number[];
  properties_filter?: Record<string, unknown>;
  limit?: number;
  format?: 'geojson' | 'csv';
  include_metadata?: boolean;
}

export interface ExportResult {
  type: 'FeatureCollection';
  features: GeoJSON.Feature[];
  metadata?: {
    tileset_id: string;
    total_count: number;
    exported_count: number;
    exported_at: string;
    filters: {
      layer_name?: string;
      bbox?: number[];
      properties_filter?: Record<string, unknown>;
      limit?: number;
    };
  };
}

export interface BatchUpdateRequest {
  feature_ids?: string[];
  tileset_id?: string;
  filter?: {
    layer_name?: string;
    bbox?: number[];
    properties?: Record<string, unknown>;
  };
  updates: {
    layer_name?: string;
    properties?: Record<string, unknown>;
    geometry?: GeoJSON.Geometry;
  };
  merge_properties?: boolean;
  limit?: number;
}

export interface BatchDeleteRequest {
  feature_ids?: string[];
  tileset_id?: string;
  filter?: {
    layer_name?: string;
    bbox?: number[];
    properties?: Record<string, unknown>;
  };
  limit?: number;
  dry_run?: boolean;
}

export interface BatchOperationResponse {
  success_count: number;
  failed_count: number;
  total_count: number;
  errors: string[];
  warnings: string[];
  status: string;
  duration_seconds?: number;
}

// ============================
// チーム型定義 (Step 3.3-A)
// ============================

export type TeamRole = 'owner' | 'administrator' | 'member' | 'guest';
export type InvitationStatus = 'pending' | 'accepted' | 'declined' | 'expired' | 'cancelled';

export interface Team {
  id: string;
  name: string;
  slug: string;
  description?: string;
  owner_id: string;
  settings: Record<string, unknown>;
  member_count?: number;
  tileset_count?: number;
  created_at: string;
  updated_at: string;
}

export interface TeamCreate {
  name: string;
  slug?: string;
  description?: string;
  settings?: Record<string, unknown>;
}

export interface TeamUpdate {
  name?: string;
  description?: string;
  settings?: Record<string, unknown>;
}

export interface TeamMember {
  id: string;
  team_id: string;
  user_id: string;
  role: TeamRole;
  notification_enabled: boolean;
  joined_at: string;
  updated_at: string;
  user_email?: string;
  user_name?: string;
}

export interface TeamMemberAdd {
  user_id: string;
  role?: TeamRole;
  notification_enabled?: boolean;
}

export interface TeamMemberUpdate {
  role?: TeamRole;
  notification_enabled?: boolean;
}

export interface TeamInvitation {
  id: string;
  team_id: string;
  email: string;
  role: TeamRole;
  invited_by: string;
  message?: string;
  token: string;
  status: InvitationStatus;
  expires_at: string;
  accepted_at?: string;
  created_at: string;
  team_name?: string;
}

export interface TeamInvitationCreate {
  email: string;
  role?: TeamRole;
  message?: string;
  expires_in_days?: number;
}

export interface TeamTileset {
  id: string;
  team_id: string;
  tileset_id: string;
  added_by: string;
  permission_level?: string;
  created_at: string;
  tileset_name?: string;
  tileset_type?: string;
}

export interface TeamTilesetAdd {
  tileset_id: string;
  permission_level?: string;
}

export interface TeamListResponse {
  teams: Team[];
  total: number;
  page: number;
  page_size: number;
}

export interface TeamMemberListResponse {
  members: TeamMember[];
  total: number;
  team_id: string;
}

export interface TeamInvitationListResponse {
  invitations: TeamInvitation[];
  total: number;
  team_id: string;
}

export interface TeamTilesetListResponse {
  tilesets: TeamTileset[];
  total: number;
  team_id: string;
}

// ============================
// APIキー型定義 (Step 3.3-B)
// ============================

export type ApiKeyScope = 'read' | 'write' | 'delete' | 'admin';
export type ApiKeyEnvironment = 'live' | 'test';

export interface ApiKey {
  id: string;
  name: string;
  description?: string;
  prefix: string;
  user_id: string;
  team_id?: string;
  team_name?: string;
  scopes: ApiKeyScope[];
  rate_limit_per_minute: number;
  rate_limit_per_day: number;
  is_active: boolean;
  last_used_at?: string;
  expires_at?: string;
  revoked_at?: string;
  created_at: string;
  updated_at: string;
  is_expired?: boolean;
  is_revoked?: boolean;
  masked_key?: string;
}

export interface ApiKeyCreated extends ApiKey {
  key: string; // Full key - only shown once!
}

export interface ApiKeyCreate {
  name: string;
  description?: string;
  team_id?: string;
  scopes?: ApiKeyScope[];
  rate_limit_per_minute?: number;
  rate_limit_per_day?: number;
  expires_in_days?: number;
  environment?: ApiKeyEnvironment;
  metadata?: Record<string, unknown>;
}

export interface ApiKeyUpdate {
  name?: string;
  description?: string;
  scopes?: ApiKeyScope[];
  rate_limit_per_minute?: number;
  rate_limit_per_day?: number;
  is_active?: boolean;
  metadata?: Record<string, unknown>;
}

export interface ApiKeyListResponse {
  keys: ApiKey[];
  total: number;
  page: number;
  page_size: number;
}

export interface ApiKeyUsageStats {
  key_id: string;
  total_requests: number;
  avg_response_time_ms: number;
  error_count: number;
  success_rate: number;
  requests_by_day: Array<{
    date: string;
    requests: number;
    errors: number;
    avg_response_time: number;
  }>;
}

export interface RateLimitStatus {
  key_id: string;
  minute_limit: number;
  minute_used: number;
  minute_remaining: number;
  day_limit: number;
  day_used: number;
  day_remaining: number;
  is_limited: boolean;
}

// ============================
// API クライアント
// ============================

class ApiClient {
  private baseUrl: string;
  private token: string | null = null;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  setToken(token: string | null) {
    this.token = token;
  }

  private getHeaders(): HeadersInit {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    return headers;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        ...this.getHeaders(),
        ...options.headers,
      },
    });

    if (!response.ok) {
      let errorDetail = `HTTP ${response.status}: ${response.statusText}`;
      try {
        const error: ApiError = await response.json();
        errorDetail = error.detail || errorDetail;
      } catch {
        // JSONパースに失敗した場合はデフォルトのエラーメッセージを使用
      }
      throw new Error(errorDetail);
    }

    const contentLength = response.headers.get('content-length');
    if (response.status === 204 || contentLength === '0') {
      return null as T;
    }

    const text = await response.text();
    if (!text) {
      return null as T;
    }

    try {
      return JSON.parse(text) as T;
    } catch {
      return null as T;
    }
  }

  private async requestBlob(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<Blob> {
    const url = `${this.baseUrl}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        ...this.getHeaders(),
        ...options.headers,
      },
    });

    if (!response.ok) {
      let errorDetail = `HTTP ${response.status}: ${response.statusText}`;
      try {
        const error: ApiError = await response.json();
        errorDetail = error.detail || errorDetail;
      } catch {
        // ignore
      }
      throw new Error(errorDetail);
    }

    return response.blob();
  }

  // ============================
  // ヘルスチェック
  // ============================

  async getHealth(): Promise<HealthStatus> {
    return this.request<HealthStatus>('/api/health');
  }

  async getHealthDb(): Promise<HealthStatus> {
    return this.request<HealthStatus>('/api/health/db');
  }

  // ============================
  // 統計 API
  // ============================

  async getSystemStats(): Promise<SystemStats> {
    return this.request<SystemStats>('/api/stats');
  }

  async getTilesetStats(id: string): Promise<TilesetStats> {
    return this.request<TilesetStats>(`/api/tilesets/${id}/stats`);
  }

  // ============================
  // タイルセット API
  // ============================

  async listTilesets(params?: {
    type?: 'vector' | 'raster' | 'pmtiles';
    is_public?: boolean;
  }): Promise<Tileset[] | { tilesets: Tileset[]; count: number }> {
    const searchParams = new URLSearchParams();
    if (params?.type) searchParams.append('type', params.type);
    if (params?.is_public !== undefined) {
      searchParams.append('is_public', String(params.is_public));
    }
    const query = searchParams.toString();
    return this.request<Tileset[] | { tilesets: Tileset[]; count: number }>(`/api/tilesets${query ? `?${query}` : ''}`);
  }

  async getTileset(id: string): Promise<Tileset> {
    return this.request<Tileset>(`/api/tilesets/${id}`);
  }

  async createTileset(data: TilesetCreate): Promise<Tileset> {
    return this.request<Tileset>('/api/tilesets', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateTileset(id: string, data: TilesetUpdate): Promise<Tileset> {
    return this.request<Tileset>(`/api/tilesets/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async deleteTileset(id: string): Promise<void> {
    await this.request<null>(`/api/tilesets/${id}`, {
      method: 'DELETE',
    });
  }

  async getTilesetTileJSON(id: string): Promise<TileJSON> {
    return this.request<TileJSON>(`/api/tilesets/${id}/tilejson.json`);
  }

  async calculateTilesetBounds(id: string): Promise<CalculateBoundsResult> {
    return this.request<CalculateBoundsResult>(`/api/tilesets/${id}/calculate-bounds`, {
      method: 'POST',
    });
  }

  // ============================
  // フィーチャー API
  // ============================

  async listFeatures(params?: {
    bbox?: string;
    layer?: string;
    filter?: string;
    limit?: number;
    tileset_id?: string;
  }): Promise<Feature[]> {
    const searchParams = new URLSearchParams();
    if (params?.bbox) searchParams.append('bbox', params.bbox);
    if (params?.layer) searchParams.append('layer', params.layer);
    if (params?.filter) searchParams.append('filter', params.filter);
    if (params?.limit) searchParams.append('limit', String(params.limit));
    if (params?.tileset_id) searchParams.append('tileset_id', params.tileset_id);
    const query = searchParams.toString();
    return this.request<Feature[]>(`/api/features${query ? `?${query}` : ''}`);
  }

  async getFeature(id: string): Promise<Feature> {
    return this.request<Feature>(`/api/features/${id}`);
  }

  async createFeature(data: FeatureCreate): Promise<Feature> {
    return this.request<Feature>('/api/features', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async createFeaturesBulk(data: BulkFeatureCreate): Promise<BulkFeatureResponse> {
    return this.request<BulkFeatureResponse>('/api/features/bulk', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateFeature(id: string, data: FeatureUpdate): Promise<Feature> {
    return this.request<Feature>(`/api/features/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async deleteFeature(id: string): Promise<void> {
    await this.request<null>(`/api/features/${id}`, {
      method: 'DELETE',
    });
  }

  // ============================
  // バッチ操作 API
  // ============================

  async exportFeatures(data: ExportRequest): Promise<ExportResult> {
    return this.request<ExportResult>('/api/features/export', {
      method: 'POST',
      body: JSON.stringify({ ...data, format: 'geojson' }),
    });
  }

  async exportFeaturesCsv(data: ExportRequest): Promise<Blob> {
    return this.requestBlob('/api/features/export', {
      method: 'POST',
      body: JSON.stringify({ ...data, format: 'csv' }),
    });
  }

  async batchUpdateFeatures(data: BatchUpdateRequest): Promise<BatchOperationResponse> {
    return this.request<BatchOperationResponse>('/api/features/bulk/update', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async batchDeleteFeatures(data: BatchDeleteRequest): Promise<BatchOperationResponse> {
    return this.request<BatchOperationResponse>('/api/features/bulk/delete', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // ============================
  // データソース API
  // ============================

  async listDatasources(params?: {
    type?: DatasourceType;
    include_private?: boolean;
  }): Promise<{ datasources: Datasource[]; count: number }> {
    const searchParams = new URLSearchParams();
    if (params?.type) searchParams.append('type', params.type);
    if (params?.include_private !== undefined) {
      searchParams.append('include_private', String(params.include_private));
    }
    const query = searchParams.toString();
    return this.request<{ datasources: Datasource[]; count: number }>(
      `/api/datasources${query ? `?${query}` : ''}`
    );
  }

  async getDatasource(id: string): Promise<Datasource> {
    return this.request<Datasource>(`/api/datasources/${id}`);
  }

  async createDatasource(data: DatasourceCreate): Promise<Datasource> {
    return this.request<Datasource>('/api/datasources', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async deleteDatasource(id: string): Promise<void> {
    await this.request<null>(`/api/datasources/${id}`, {
      method: 'DELETE',
    });
  }

  async testDatasource(id: string): Promise<DatasourceTestResult> {
    return this.request<DatasourceTestResult>(`/api/datasources/${id}/test`, {
      method: 'POST',
    });
  }

  // ============================
  // 認証 API
  // ============================

  async getAuthMe(): Promise<{ user_id: string; email?: string }> {
    return this.request('/api/auth/me');
  }

  async getAuthStatus(): Promise<{ authenticated: boolean; user_id?: string }> {
    return this.request('/api/auth/status');
  }

  // ============================
  // チーム API (Step 3.3-A)
  // ============================

  async listTeams(params?: { page?: number; page_size?: number }): Promise<TeamListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.append('page', String(params.page));
    if (params?.page_size) searchParams.append('page_size', String(params.page_size));
    const query = searchParams.toString();
    return this.request<TeamListResponse>(`/api/teams${query ? `?${query}` : ''}`);
  }

  async getTeam(id: string): Promise<Team> {
    return this.request<Team>(`/api/teams/${id}`);
  }

  async createTeam(data: TeamCreate): Promise<Team> {
    return this.request<Team>('/api/teams', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateTeam(id: string, data: TeamUpdate): Promise<Team> {
    return this.request<Team>(`/api/teams/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteTeam(id: string): Promise<void> {
    await this.request<null>(`/api/teams/${id}`, {
      method: 'DELETE',
    });
  }

  // Team Members
  async listTeamMembers(teamId: string): Promise<TeamMemberListResponse> {
    return this.request<TeamMemberListResponse>(`/api/teams/${teamId}/members`);
  }

  async addTeamMember(teamId: string, data: TeamMemberAdd): Promise<TeamMember> {
    return this.request<TeamMember>(`/api/teams/${teamId}/members`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateTeamMember(teamId: string, userId: string, data: TeamMemberUpdate): Promise<TeamMember> {
    return this.request<TeamMember>(`/api/teams/${teamId}/members/${userId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async removeTeamMember(teamId: string, userId: string): Promise<void> {
    await this.request<null>(`/api/teams/${teamId}/members/${userId}`, {
      method: 'DELETE',
    });
  }

  // Team Invitations
  async listTeamInvitations(teamId: string, status?: InvitationStatus): Promise<TeamInvitationListResponse> {
    const searchParams = new URLSearchParams();
    if (status) searchParams.append('status', status);
    const query = searchParams.toString();
    return this.request<TeamInvitationListResponse>(`/api/teams/${teamId}/invitations${query ? `?${query}` : ''}`);
  }

  async createTeamInvitation(teamId: string, data: TeamInvitationCreate): Promise<TeamInvitation> {
    return this.request<TeamInvitation>(`/api/teams/${teamId}/invitations`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async acceptTeamInvitation(token: string): Promise<TeamMember> {
    return this.request<TeamMember>('/api/teams/invitations/accept', {
      method: 'POST',
      body: JSON.stringify({ token }),
    });
  }

  async cancelTeamInvitation(teamId: string, invitationId: string): Promise<void> {
    await this.request<null>(`/api/teams/${teamId}/invitations/${invitationId}`, {
      method: 'DELETE',
    });
  }

  // Team Tilesets
  async listTeamTilesets(teamId: string): Promise<TeamTilesetListResponse> {
    return this.request<TeamTilesetListResponse>(`/api/teams/${teamId}/tilesets`);
  }

  async addTeamTileset(teamId: string, data: TeamTilesetAdd): Promise<TeamTileset> {
    return this.request<TeamTileset>(`/api/teams/${teamId}/tilesets`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async removeTeamTileset(teamId: string, tilesetId: string): Promise<void> {
    await this.request<null>(`/api/teams/${teamId}/tilesets/${tilesetId}`, {
      method: 'DELETE',
    });
  }

  // Team Ownership Transfer
  async transferTeamOwnership(teamId: string, newOwnerId: string): Promise<Team> {
    return this.request<Team>(`/api/teams/${teamId}/transfer-ownership`, {
      method: 'POST',
      body: JSON.stringify({ new_owner_id: newOwnerId }),
    });
  }

  // ============================
  // APIキー API (Step 3.3-B)
  // ============================

  async listApiKeys(params?: {
    team_id?: string;
    include_revoked?: boolean;
    page?: number;
    page_size?: number;
  }): Promise<ApiKeyListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.team_id) searchParams.append('team_id', params.team_id);
    if (params?.include_revoked) searchParams.append('include_revoked', 'true');
    if (params?.page) searchParams.append('page', String(params.page));
    if (params?.page_size) searchParams.append('page_size', String(params.page_size));
    const query = searchParams.toString();
    return this.request<ApiKeyListResponse>(`/api/api-keys${query ? `?${query}` : ''}`);
  }

  async getApiKey(id: string): Promise<ApiKey> {
    return this.request<ApiKey>(`/api/api-keys/${id}`);
  }

  async createApiKey(data: ApiKeyCreate): Promise<ApiKeyCreated> {
    return this.request<ApiKeyCreated>('/api/api-keys', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateApiKey(id: string, data: ApiKeyUpdate): Promise<ApiKey> {
    return this.request<ApiKey>(`/api/api-keys/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async revokeApiKey(id: string, reason?: string): Promise<ApiKey> {
    return this.request<ApiKey>(`/api/api-keys/${id}/revoke`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    });
  }

  async deleteApiKey(id: string): Promise<void> {
    await this.request<null>(`/api/api-keys/${id}`, {
      method: 'DELETE',
    });
  }

  async getApiKeyUsage(id: string, days?: number): Promise<ApiKeyUsageStats> {
    const searchParams = new URLSearchParams();
    if (days) searchParams.append('days', String(days));
    const query = searchParams.toString();
    return this.request<ApiKeyUsageStats>(`/api/api-keys/${id}/usage${query ? `?${query}` : ''}`);
  }

  async getApiKeyRateLimit(id: string): Promise<RateLimitStatus> {
    return this.request<RateLimitStatus>(`/api/api-keys/${id}/rate-limit`);
  }

  // ============================
  // タイル URL 生成
  // ============================

  getTileUrl(
    tilesetId: string,
    z: number,
    x: number,
    y: number,
    format: string = 'pbf'
  ): string {
    return `${this.baseUrl}/api/tiles/pmtiles/${tilesetId}/{z}/{x}/{y}.${format}`;
  }

  getTileUrlTemplate(tilesetId: string, format: string = 'pbf'): string {
    return `${this.baseUrl}/api/tiles/pmtiles/${tilesetId}/{z}/{x}/{y}.${format}`;
  }

  getFeaturesTileUrl(): string {
    return `${this.baseUrl}/api/tiles/features/{z}/{x}/{y}.pbf`;
  }
}

// デフォルトのAPIクライアントインスタンス
export const api = new ApiClient();

// APIクライアントクラスもエクスポート
export { ApiClient };
