"use client";

import { useEffect, useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import { AdminLayout } from "@/components/layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useApi } from "@/hooks/use-api";
import type { Tileset, HealthStatus, SystemStats } from "@/lib/api";
import { 
  Layers, 
  Map, 
  Database, 
  Activity, 
  RefreshCw,
  Plus,
  ExternalLink,
  MapPin,
  TrendingUp,
  AlertCircle,
  BarChart3,
} from "lucide-react";
import Link from "next/link";

export default function DashboardPage() {
  const { api, isReady } = useApi();
  const t = useTranslations("dashboard");
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [tilesets, setTilesets] = useState<Tileset[]>([]);
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statsError, setStatsError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setStatsError(null);
    
    try {
      const results = await Promise.allSettled([
        api.getHealthDb(),
        api.listTilesets({ include_private: true }),
        api.getSystemStats(),
      ]);
      
      // ヘルスチェック結果の処理
      if (results[0].status === "fulfilled") {
        setHealth(results[0].value);
      } else {
        console.error("Health check failed:", results[0].reason);
      }
      
      // タイルセット結果の処理
      if (results[1].status === "fulfilled") {
        const data = results[1].value;
        if (Array.isArray(data)) {
          setTilesets(data);
        } else if (data && Array.isArray(data.tilesets)) {
          setTilesets(data.tilesets);
        } else {
          setTilesets([]);
        }
      } else {
        console.error("Tilesets fetch failed:", results[1].reason);
        setTilesets([]);
        setError(t("tilesets_fetch_error"));
      }
      
      // 統計結果の処理
      if (results[2].status === "fulfilled") {
        setStats(results[2].value);
      } else {
        console.error("Stats fetch failed:", results[2].reason);
        setStatsError(t("stats_fetch_error"));
      }
      
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : t("data_fetch_error");
      setError(errorMessage);
      setTilesets([]);
    } finally {
      setIsLoading(false);
    }
  }, [api, t]);

  useEffect(() => {
    if (isReady) {
      fetchData();
    }
  }, [isReady, fetchData]);

  // 安全にフィルタリング
  const safeFilterTilesets = Array.isArray(tilesets) ? tilesets : [];
  const vectorTilesets = safeFilterTilesets.filter((t) => t.type === "vector");
  const rasterTilesets = safeFilterTilesets.filter((t) => t.type === "raster");
  const pmtilesTilesets = safeFilterTilesets.filter((t) => t.type === "pmtiles");

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* ヘッダー */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">{t("title")}</h1>
            <p className="text-muted-foreground">{t("subtitle")}</p>
          </div>
          <Button
            onClick={fetchData}
            variant="outline"
            size="sm"
            disabled={!isReady || isLoading}
            data-testid="dashboard-refresh"
          >
            <RefreshCw className={`mr-2 h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
            {t("refresh")}
          </Button>
        </div>

        {/* エラー表示 */}
        {error && (
          <Card className="border-destructive bg-destructive/10">
            <CardContent className="pt-6 flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-destructive" />
              <p className="text-destructive">{error}</p>
            </CardContent>
          </Card>
        )}

        {/* ステータスカード */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {/* サーバー状態 */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{t("server_status")}</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                <Badge variant={health?.status === "healthy" || health?.status === "ok" ? "default" : "destructive"}>
                  {health?.status || t("checking")}
                </Badge>
              </div>
              <p className="mt-2 text-xs text-muted-foreground">
                {health?.environment || "-"}
              </p>
            </CardContent>
          </Card>

          {/* データベース */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{t("database")}</CardTitle>
              <Database className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                <Badge variant={health?.database === "connected" ? "default" : "destructive"}>
                  {health?.database || t("checking")}
                </Badge>
              </div>
              <p className="mt-2 text-xs text-muted-foreground">
                {t("postgis_prefix")} {health?.postgis || "-"}
              </p>
            </CardContent>
          </Card>

          {/* タイルセット数 */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{t("tilesets")}</CardTitle>
              <Layers className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold" data-testid="dashboard-tilesets-count">
                {!isReady || isLoading ? "-" : stats?.tilesets?.total ?? safeFilterTilesets.length}
              </div>
              <p className="text-xs text-muted-foreground">
                {t("tilesets_breakdown", {
                  vector: !isReady || isLoading ? "-" : stats?.tilesets?.by_type?.vector ?? vectorTilesets.length,
                  pmtiles: !isReady || isLoading ? "-" : stats?.tilesets?.by_type?.pmtiles ?? pmtilesTilesets.length,
                  raster: !isReady || isLoading ? "-" : stats?.tilesets?.by_type?.raster ?? rasterTilesets.length,
                })}
              </p>
            </CardContent>
          </Card>

          {/* フィーチャー数（新規追加） */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{t("features")}</CardTitle>
              <MapPin className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold" data-testid="dashboard-features-count">
                {!isReady || isLoading ? "-" : stats?.features?.total?.toLocaleString() ?? "-"}
              </div>
              {stats?.features && (
                <p className="text-xs text-muted-foreground">
                  {t("features_breakdown", {
                    point: stats.features.by_geometry_type?.Point ?? 0,
                    line: stats.features.by_geometry_type?.LineString ?? 0,
                    polygon: stats.features.by_geometry_type?.Polygon ?? 0,
                  })}
                </p>
              )}
              {statsError && (
                <p className="text-xs text-muted-foreground">{statsError}</p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* 統計サマリー（新規追加） */}
        {stats && (
          <div className="grid gap-4 md:grid-cols-3">
            {/* 公開状態 */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">{t("public_status")}</CardTitle>
                <Map className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-2xl font-bold">{stats.tilesets.public}</div>
                    <p className="text-xs text-muted-foreground">{t("public_tilesets")}</p>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-bold text-muted-foreground">{stats.tilesets.private}</div>
                    <p className="text-xs text-muted-foreground">{t("private_tilesets")}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* データソース */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">{t("datasources")}</CardTitle>
                <Database className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-2xl font-bold" data-testid="dashboard-datasources-count">
                      {stats.datasources.total}
                    </div>
                    <p className="text-xs text-muted-foreground">{t("registered")}</p>
                  </div>
                  <div className="text-right text-xs text-muted-foreground">
                    <p>PMTiles: {stats.datasources.pmtiles}</p>
                    <p>COG: {stats.datasources.raster}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* フィーチャートップ */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">{t("top_features")}</CardTitle>
                <TrendingUp className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                {stats.top_tilesets_by_features.length > 0 ? (
                  <div className="space-y-1">
                    {stats.top_tilesets_by_features.slice(0, 3).map((item, index) => (
                      <div key={item.id} className="flex items-center justify-between text-sm">
                        <span className="truncate max-w-[150px]">
                          {index + 1}. {item.name}
                        </span>
                        <Badge variant="secondary">{item.feature_count.toLocaleString()}</Badge>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">{t("no_features")}</p>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {/* クイックアクション */}
        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>{t("quick_actions")}</CardTitle>
              <CardDescription>{t("quick_actions_desc")}</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              <Link href="/tilesets/new">
                <Button>
                  <Plus className="mr-2 h-4 w-4" />
                  {t("create_tileset")}
                </Button>
              </Link>
              <Link href="/features">
                <Button variant="outline">
                  <Map className="mr-2 h-4 w-4" />
                  {t("manage_features")}
                </Button>
              </Link>
              <Link href="/features/import">
                <Button variant="outline">
                  <BarChart3 className="mr-2 h-4 w-4" />
                  {t("import_geojson")}
                </Button>
              </Link>
              <a
                href="https://geo-base-api.fly.dev/api/health"
                target="_blank"
                rel="noopener noreferrer"
              >
                <Button variant="outline">
                  <ExternalLink className="mr-2 h-4 w-4" />
                  {t("check_api")}
                </Button>
              </a>
            </CardContent>
          </Card>

          {/* 最近のタイルセット */}
          <Card>
            <CardHeader>
              <CardTitle>{t("recent_tilesets")}</CardTitle>
              <CardDescription>{t("showing_latest_five")}</CardDescription>
            </CardHeader>
            <CardContent>
              {!isReady || isLoading ? (
                <p className="text-sm text-muted-foreground">{t("loading")}</p>
              ) : safeFilterTilesets.length === 0 ? (
                <p className="text-sm text-muted-foreground">{t("no_tilesets")}</p>
              ) : (
                <div className="space-y-2">
                  {safeFilterTilesets.slice(0, 5).map((tileset) => (
                    <Link
                      key={tileset.id}
                      href={`/tilesets/${tileset.id}`}
                      className="flex items-center justify-between rounded-md border p-2 transition-colors hover:bg-accent"
                    >
                      <div className="flex items-center gap-2">
                        <Layers className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm font-medium">{tileset.name}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="text-xs">
                          {tileset.type}
                        </Badge>
                        {tileset.is_public && (
                          <Badge variant="secondary" className="text-xs">
                          {t("public_badge")}
                          </Badge>
                        )}
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* API情報 */}
        <Card>
          <CardHeader>
            <CardTitle>{t("api_info")}</CardTitle>
            <CardDescription>{t("api_endpoint")}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2">
                <span className="font-medium">{t("production_url")}</span>
                <code className="rounded bg-muted px-2 py-1">
                  https://geo-base-api.fly.dev
                </code>
              </div>
              <div className="flex items-center gap-2">
                <span className="font-medium">{t("mcp_server")}</span>
                <code className="rounded bg-muted px-2 py-1">
                  https://geo-base-mcp.fly.dev
                </code>
              </div>
              <div className="flex items-center gap-2">
                <span className="font-medium">{t("admin_ui")}</span>
                <code className="rounded bg-muted px-2 py-1">
                  https://geo-base-app.vercel.app
                </code>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </AdminLayout>
  );
}
