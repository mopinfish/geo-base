"use client";

import { use, useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { AdminLayout } from "@/components/layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { DeleteTilesetDialog } from "@/components/tilesets/delete-tileset-dialog";
import { TilesetMapPreview } from "@/components/map";
import { ExportFeaturesButton } from "@/components/features";
import { useApi } from "@/hooks/use-api";
import type { Tileset, TileJSON, TilesetStats } from "@/lib/api";
import {
  ArrowLeft,
  Pencil,
  RefreshCw,
  Layers,
  Globe,
  Lock,
  Copy,
  Check,
  ExternalLink,
  MapPin,
  ZoomIn,
  Calendar,
  Map,
  Eye,
  EyeOff,
  BarChart3,
  Database,
} from "lucide-react";

// TileJSON with vector_layers の型定義
interface VectorLayer {
  id: string;
  fields?: Record<string, string>;
  minzoom?: number;
  maxzoom?: number;
  description?: string;
}

interface TileJSONWithLayers extends TileJSON {
  vector_layers?: VectorLayer[];
}

interface TilesetDetailPageProps {
  params: Promise<{ id: string }>;
}

export default function TilesetDetailPage({ params }: TilesetDetailPageProps) {
  const { id } = use(params);
  const router = useRouter();
  const { api, isReady } = useApi();

  const [tileset, setTileset] = useState<Tileset | null>(null);
  const [tileJSON, setTileJSON] = useState<TileJSONWithLayers | null>(null);
  const [tilesetStats, setTilesetStats] = useState<TilesetStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copiedUrl, setCopiedUrl] = useState<string | null>(null);
  const [showMapPreview, setShowMapPreview] = useState(true);
  // マップリフレッシュ用のキー（更新ボタン押下時にインクリメント）
  const [mapRefreshKey, setMapRefreshKey] = useState<number>(Date.now());
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchTileset = async (refreshMap = false) => {
    if (!isReady) return;

    setIsLoading(true);
    setError(null);
    if (refreshMap) {
      setIsRefreshing(true);
    }

    try {
      const data = await api.getTileset(id);
      console.log("Tileset data:", data);
      setTileset(data);

      // TileJSONも取得
      try {
        const tjData = await api.getTilesetTileJSON(id);
        setTileJSON(tjData as TileJSONWithLayers);
      } catch {
        // TileJSONの取得に失敗しても詳細は表示
        console.warn("TileJSON fetch failed, but continuing without it");
      }

      // フィーチャー統計を取得（vectorタイプの場合）
      if (data.type === "vector") {
        try {
          const statsData = await api.getTilesetStats(id);
          setTilesetStats(statsData);
        } catch {
          console.warn("Tileset stats fetch failed");
        }
      }

      // マップをリフレッシュ（キャッシュバスティング）
      if (refreshMap) {
        setMapRefreshKey(Date.now());
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "タイルセットの取得に失敗しました"
      );
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    if (isReady) {
      fetchTileset(false);
    }
  }, [id, isReady]);

  const handleRefresh = () => {
    fetchTileset(true);
  };

  const handleDelete = async () => {
    await api.deleteTileset(id);
    router.push("/tilesets");
  };

  const copyToClipboard = async (text: string, label: string) => {
    await navigator.clipboard.writeText(text);
    setCopiedUrl(label);
    setTimeout(() => setCopiedUrl(null), 2000);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString("ja-JP", {
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  /**
   * bounds/centerを安全にパースして配列に変換
   */
  const parseCoordinates = (value: unknown): number[] | null => {
    if (!value) return null;

    // すでに配列の場合
    if (Array.isArray(value)) {
      const nums = value.map(Number);
      if (nums.some(isNaN)) return null;
      return nums;
    }

    // 文字列の場合（カンマ区切り）
    if (typeof value === "string") {
      const parts = value.split(",").map((s) => Number(s.trim()));
      if (parts.some(isNaN)) return null;
      return parts;
    }

    return null;
  };

  const formatBounds = (bounds: unknown) => {
    const nums = parseCoordinates(bounds);
    if (!nums || nums.length !== 4) return "-";
    return `${nums[0].toFixed(4)}, ${nums[1].toFixed(4)}, ${nums[2].toFixed(
      4
    )}, ${nums[3].toFixed(4)}`;
  };

  const formatCenter = (center: unknown) => {
    const nums = parseCoordinates(center);
    if (!nums || nums.length < 2) return "-";
    const zoomPart = nums[2] !== undefined ? ` (zoom: ${nums[2]})` : "";
    return `${nums[0].toFixed(4)}, ${nums[1].toFixed(4)}${zoomPart}`;
  };

  /**
   * タイルセットのタイプに応じたタイルURLを生成
   */
  const getTileUrl = (tileset: Tileset, baseUrl: string): string => {
    switch (tileset.type) {
      case "pmtiles":
        return `${baseUrl}/api/tiles/pmtiles/${tileset.id}/{z}/{x}/{y}.pbf`;
      case "raster":
        // ラスタータイルのフォーマット（デフォルトはpng）
        const rasterFormat = tileset.format || "png";
        return `${baseUrl}/api/tiles/raster/${tileset.id}/{z}/{x}/{y}.${rasterFormat}`;
      case "vector":
      default:
        return `${baseUrl}/api/tiles/features/{z}/{x}/{y}.pbf?tileset_id=${tileset.id}`;
    }
  };

  /**
   * タイルセットのタイプに応じたラベルを取得
   */
  const getTileUrlLabel = (type: string): string => {
    switch (type) {
      case "pmtiles":
        return "タイルURL（PMTiles）";
      case "raster":
        return "タイルURL（ラスター）";
      case "vector":
      default:
        return "タイルURL（ベクター）";
    }
  };

  /**
   * vector_layersからレイヤー一覧を取得
   */
  const getVectorLayers = (): VectorLayer[] => {
    if (!tileJSON?.vector_layers) return [];
    return tileJSON.vector_layers;
  };

  if (!isReady || isLoading) {
    return (
      <AdminLayout>
        <div className="flex h-64 items-center justify-center">
          <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </AdminLayout>
    );
  }

  if (error || !tileset) {
    return (
      <AdminLayout>
        <div className="space-y-4">
          <Link href="/tilesets">
            <Button variant="outline">
              <ArrowLeft className="mr-2 h-4 w-4" />
              戻る
            </Button>
          </Link>
          <Card className="border-destructive">
            <CardContent className="pt-6">
              <p className="text-destructive">
                {error || "タイルセットが見つかりません"}
              </p>
            </CardContent>
          </Card>
        </div>
      </AdminLayout>
    );
  }

  const apiBaseUrl =
    process.env.NEXT_PUBLIC_API_URL || "https://geo-base-api.fly.dev";
  const tileUrl = getTileUrl(tileset, apiBaseUrl);
  const tileJsonUrl = `${apiBaseUrl}/api/tilesets/${id}/tilejson.json`;
  const tileUrlLabel = getTileUrlLabel(tileset.type);
  const vectorLayers = getVectorLayers();

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* ヘッダー */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/tilesets">
              <Button variant="outline" size="icon">
                <ArrowLeft className="h-4 w-4" />
              </Button>
            </Link>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-3xl font-bold">{tileset.name}</h1>
                <Badge variant={tileset.is_public ? "default" : "secondary"}>
                  {tileset.is_public ? (
                    <>
                      <Globe className="mr-1 h-3 w-3" />
                      公開
                    </>
                  ) : (
                    <>
                      <Lock className="mr-1 h-3 w-3" />
                      非公開
                    </>
                  )}
                </Badge>
              </div>
              {tileset.description && (
                <p className="mt-1 text-muted-foreground">
                  {tileset.description}
                </p>
              )}
            </div>
          </div>
          <div className="flex gap-2">
            <Button
              onClick={handleRefresh}
              variant="outline"
              size="sm"
              disabled={isRefreshing}
            >
              <RefreshCw
                className={`mr-2 h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`}
              />
              更新
            </Button>
            <Link href={`/tilesets/${id}/edit`}>
              <Button variant="outline" size="sm">
                <Pencil className="mr-2 h-4 w-4" />
                編集
              </Button>
            </Link>
            <DeleteTilesetDialog
              tilesetName={tileset.name}
              onConfirm={handleDelete}
            />
            {tileset.type === "vector" && (
              <ExportFeaturesButton tilesetId={id} tilesetName={tileset.name} />
            )}
          </div>
        </div>

        {/* マッププレビュー */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Map className="h-5 w-5" />
                マッププレビュー
              </CardTitle>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowMapPreview(!showMapPreview)}
              >
                {showMapPreview ? (
                  <>
                    <EyeOff className="mr-2 h-4 w-4" />
                    非表示
                  </>
                ) : (
                  <>
                    <Eye className="mr-2 h-4 w-4" />
                    表示
                  </>
                )}
              </Button>
            </div>
          </CardHeader>
          {showMapPreview && (
            <CardContent>
              <TilesetMapPreview
                tileset={tileset}
                tileJSON={tileJSON}
                height="400px"
                refreshKey={mapRefreshKey}
              />
              <p className="mt-2 text-xs text-muted-foreground">
                ※ データソースが登録されていない場合、タイルは表示されません。
                フィーチャーを編集した場合は「更新」ボタンを押してください。
              </p>
            </CardContent>
          )}
        </Card>

        {/* フィーチャー統計（vectorタイプのみ） */}
        {tileset.type === "vector" && tilesetStats && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                フィーチャー統計
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center p-4 bg-muted/50 rounded-lg">
                  <div className="text-2xl font-bold">
                    {tilesetStats.feature_count.toLocaleString()}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    総フィーチャー数
                  </div>
                </div>
                <div className="text-center p-4 bg-muted/50 rounded-lg">
                  <div className="text-2xl font-bold">
                    {tilesetStats.geometry_types?.Point?.toLocaleString() ?? 0}
                  </div>
                  <div className="text-sm text-muted-foreground">ポイント</div>
                </div>
                <div className="text-center p-4 bg-muted/50 rounded-lg">
                  <div className="text-2xl font-bold">
                    {tilesetStats.geometry_types?.LineString?.toLocaleString() ??
                      0}
                  </div>
                  <div className="text-sm text-muted-foreground">ライン</div>
                </div>
                <div className="text-center p-4 bg-muted/50 rounded-lg">
                  <div className="text-2xl font-bold">
                    {tilesetStats.geometry_types?.Polygon?.toLocaleString() ??
                      0}
                  </div>
                  <div className="text-sm text-muted-foreground">ポリゴン</div>
                </div>
              </div>
              {tilesetStats.latest_update && (
                <div className="mt-4 text-sm text-muted-foreground">
                  最終更新:{" "}
                  {new Date(tilesetStats.latest_update).toLocaleString("ja-JP")}
                </div>
              )}
            </CardContent>
          </Card>
        )}

        <div className="grid gap-6 lg:grid-cols-2">
          {/* 基本情報 */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Layers className="h-5 w-5" />
                タイル情報
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">
                    タイプ
                  </p>
                  <Badge variant="outline" className="mt-1">
                    {tileset.type}
                  </Badge>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">
                    フォーマット
                  </p>
                  <code className="mt-1 inline-block rounded bg-muted px-2 py-1 text-sm">
                    {tileset.format}
                  </code>
                </div>
                <div className="col-span-2">
                  <p className="text-sm font-medium text-muted-foreground">
                    ID
                  </p>
                  <code className="mt-1 inline-block rounded bg-muted px-2 py-1 text-xs break-all">
                    {tileset.id}
                  </code>
                </div>
              </div>

              {tileset.attribution && (
                <>
                  <Separator />
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">
                      帰属表示
                    </p>
                    <p className="mt-1 text-sm">{tileset.attribution}</p>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          {/* ズーム・範囲 */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ZoomIn className="h-5 w-5" />
                ズーム・範囲
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">
                    最小ズーム
                  </p>
                  <p className="mt-1 text-lg font-semibold">
                    {tileset.min_zoom ?? 0}
                  </p>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">
                    最大ズーム
                  </p>
                  <p className="mt-1 text-lg font-semibold">
                    {tileset.max_zoom ?? 22}
                  </p>
                </div>
              </div>

              <Separator />

              <div>
                <p className="text-sm font-medium text-muted-foreground flex items-center gap-1">
                  <MapPin className="h-3 w-3" />
                  バウンディングボックス
                </p>
                <code className="mt-1 inline-block rounded bg-muted px-2 py-1 text-xs">
                  {formatBounds(tileset.bounds)}
                </code>
              </div>

              <div>
                <p className="text-sm font-medium text-muted-foreground flex items-center gap-1">
                  <MapPin className="h-3 w-3" />
                  中心座標
                </p>
                <code className="mt-1 inline-block rounded bg-muted px-2 py-1 text-xs">
                  {formatCenter(tileset.center)}
                </code>
              </div>
            </CardContent>
          </Card>

          {/* URLエンドポイント */}
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ExternalLink className="h-5 w-5" />
                APIエンドポイント
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-muted-foreground">
                    {tileUrlLabel}
                  </p>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => copyToClipboard(tileUrl, "tile")}
                  >
                    {copiedUrl === "tile" ? (
                      <Check className="h-4 w-4 text-green-500" />
                    ) : (
                      <Copy className="h-4 w-4" />
                    )}
                  </Button>
                </div>
                <code className="mt-1 block rounded bg-muted px-3 py-2 text-xs break-all">
                  {tileUrl}
                </code>
              </div>

              <Separator />

              <div>
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-muted-foreground">
                    TileJSON URL（全レイヤー）
                  </p>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => copyToClipboard(tileJsonUrl, "tilejson")}
                  >
                    {copiedUrl === "tilejson" ? (
                      <Check className="h-4 w-4 text-green-500" />
                    ) : (
                      <Copy className="h-4 w-4" />
                    )}
                  </Button>
                </div>
                <code className="mt-1 block rounded bg-muted px-3 py-2 text-xs break-all">
                  {tileJsonUrl}
                </code>
              </div>

              {/* レイヤー別TileJSON URL（vectorタイプのみ） */}
              {tileset.type === "vector" && vectorLayers.length > 0 && (
                <>
                  <Separator />
                  <div>
                    <div className="flex items-center gap-2 mb-3">
                      <Database className="h-4 w-4" />
                      <p className="text-sm font-medium text-muted-foreground">
                        レイヤー別TileJSON URL（QGIS用）
                      </p>
                    </div>
                    <p className="text-xs text-muted-foreground mb-3">
                      QGISで使用する場合は、各レイヤーごとのTileJSON
                      URLを使用してください。
                    </p>
                    <div className="space-y-2">
                      {vectorLayers.map((layer) => {
                        const layerTileJsonUrl = `${apiBaseUrl}/api/tilesets/${id}/tilejson.json?layer=${encodeURIComponent(
                          layer.id
                        )}`;
                        const copyKey = `layer-${layer.id}`;
                        return (
                          <div
                            key={layer.id}
                            className="flex items-center justify-between bg-muted/50 rounded-lg px-3 py-2"
                          >
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2">
                                <Badge variant="outline" className="text-xs">
                                  {layer.id}
                                </Badge>
                                {layer.fields && (
                                  <span className="text-xs text-muted-foreground">
                                    {Object.keys(layer.fields).length} fields
                                  </span>
                                )}
                              </div>
                              <code className="mt-1 block text-xs break-all text-muted-foreground">
                                {layerTileJsonUrl}
                              </code>
                            </div>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="ml-2 shrink-0"
                              onClick={() =>
                                copyToClipboard(layerTileJsonUrl, copyKey)
                              }
                            >
                              {copiedUrl === copyKey ? (
                                <Check className="h-4 w-4 text-green-500" />
                              ) : (
                                <Copy className="h-4 w-4" />
                              )}
                            </Button>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </>
              )}

              {tileJSON && (
                <>
                  <Separator />
                  <div>
                    <p className="text-sm font-medium text-muted-foreground mb-2">
                      TileJSON
                    </p>
                    <pre className="rounded bg-muted px-3 py-2 text-xs overflow-auto max-h-48">
                      {JSON.stringify(tileJSON, null, 2)}
                    </pre>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          {/* メタデータ */}
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calendar className="h-5 w-5" />
                メタデータ
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">
                    作成日時
                  </p>
                  <p className="mt-1">{formatDate(tileset.created_at)}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">
                    更新日時
                  </p>
                  <p className="mt-1">{formatDate(tileset.updated_at)}</p>
                </div>
                {tileset.owner_id && (
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">
                      オーナーID
                    </p>
                    <code className="mt-1 inline-block rounded bg-muted px-2 py-1 text-xs">
                      {tileset.owner_id}
                    </code>
                  </div>
                )}
              </div>

              {tileset.metadata && Object.keys(tileset.metadata).length > 0 && (
                <>
                  <Separator className="my-4" />
                  <div>
                    <p className="text-sm font-medium text-muted-foreground mb-2">
                      カスタムメタデータ
                    </p>
                    <pre className="rounded bg-muted px-3 py-2 text-xs overflow-auto">
                      {JSON.stringify(tileset.metadata, null, 2)}
                    </pre>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </AdminLayout>
  );
}
