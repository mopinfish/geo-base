"use client";

import { useEffect, useState } from "react";
import { AdminLayout } from "@/components/layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, type Tileset, type HealthStatus } from "@/lib/api";
import { 
  Layers, 
  Map, 
  Database, 
  Activity, 
  RefreshCw,
  Plus,
  ExternalLink,
} from "lucide-react";
import Link from "next/link";

export default function DashboardPage() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [tilesets, setTilesets] = useState<Tileset[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [healthData, tilesetsData] = await Promise.allSettled([
        api.getHealthDb(),
        api.listTilesets(),
      ]);
      
      // ヘルスチェック結果の処理
      if (healthData.status === "fulfilled") {
        setHealth(healthData.value);
      }
      
      // タイルセット結果の処理（配列であることを確認）
      if (tilesetsData.status === "fulfilled" && Array.isArray(tilesetsData.value)) {
        setTilesets(tilesetsData.value);
      } else {
        setTilesets([]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "データの取得に失敗しました");
      setTilesets([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // 安全にフィルタリング（tilesetsが配列でない場合に備える）
  const safeFilterTilesets = Array.isArray(tilesets) ? tilesets : [];
  const vectorTilesets = safeFilterTilesets.filter((t) => t.type === "vector");
  const rasterTilesets = safeFilterTilesets.filter((t) => t.type === "raster");

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* ヘッダー */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">ダッシュボード</h1>
            <p className="text-muted-foreground">
              geo-base タイルサーバーの管理画面へようこそ
            </p>
          </div>
          <Button onClick={fetchData} variant="outline" size="sm">
            <RefreshCw className={`mr-2 h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
            更新
          </Button>
        </div>

        {/* エラー表示 */}
        {error && (
          <Card className="border-destructive">
            <CardContent className="pt-6">
              <p className="text-destructive">{error}</p>
            </CardContent>
          </Card>
        )}

        {/* ステータスカード */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {/* サーバー状態 */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">サーバー状態</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                <Badge variant={health?.status === "healthy" ? "default" : "destructive"}>
                  {health?.status || "確認中..."}
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
              <CardTitle className="text-sm font-medium">データベース</CardTitle>
              <Database className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                <Badge variant={health?.database === "connected" ? "default" : "destructive"}>
                  {health?.database || "確認中..."}
                </Badge>
              </div>
              <p className="mt-2 text-xs text-muted-foreground">
                PostGIS: {health?.postgis || "-"}
              </p>
            </CardContent>
          </Card>

          {/* タイルセット数 */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">タイルセット</CardTitle>
              <Layers className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{safeFilterTilesets.length}</div>
              <p className="text-xs text-muted-foreground">
                ベクタ: {vectorTilesets.length} / ラスタ: {rasterTilesets.length}
              </p>
            </CardContent>
          </Card>

          {/* 公開状態 */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">公開タイルセット</CardTitle>
              <Map className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {safeFilterTilesets.filter((t) => t.is_public).length}
              </div>
              <p className="text-xs text-muted-foreground">
                非公開: {safeFilterTilesets.filter((t) => !t.is_public).length}
              </p>
            </CardContent>
          </Card>
        </div>

        {/* クイックアクション */}
        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>クイックアクション</CardTitle>
              <CardDescription>よく使う操作へのショートカット</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              <Link href="/tilesets/new">
                <Button>
                  <Plus className="mr-2 h-4 w-4" />
                  タイルセット作成
                </Button>
              </Link>
              <Link href="/features">
                <Button variant="outline">
                  <Map className="mr-2 h-4 w-4" />
                  フィーチャー管理
                </Button>
              </Link>
              <a
                href="https://geo-base-puce.vercel.app/api/health"
                target="_blank"
                rel="noopener noreferrer"
              >
                <Button variant="outline">
                  <ExternalLink className="mr-2 h-4 w-4" />
                  API確認
                </Button>
              </a>
            </CardContent>
          </Card>

          {/* 最近のタイルセット */}
          <Card>
            <CardHeader>
              <CardTitle>最近のタイルセット</CardTitle>
              <CardDescription>最新の5件を表示</CardDescription>
            </CardHeader>
            <CardContent>
              {safeFilterTilesets.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  タイルセットがありません
                </p>
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
                            公開
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
            <CardTitle>API情報</CardTitle>
            <CardDescription>タイルサーバーAPIのエンドポイント</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2">
                <span className="font-medium">本番URL:</span>
                <code className="rounded bg-muted px-2 py-1">
                  https://geo-base-puce.vercel.app
                </code>
              </div>
              <div className="flex items-center gap-2">
                <span className="font-medium">MCP サーバー:</span>
                <code className="rounded bg-muted px-2 py-1">
                  https://geo-base-mcp.fly.dev
                </code>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </AdminLayout>
  );
}
