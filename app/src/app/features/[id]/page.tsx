"use client";

import { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { AdminLayout } from "@/components/layout";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { useApi } from "@/hooks/use-api";
import { MapView } from "@/components/map";
import { DeleteFeatureDialog } from "@/components/features";
import type { Feature, Tileset } from "@/lib/api";
import { 
  ArrowLeft, 
  Pencil, 
  RefreshCw, 
  MapPin,
  Layers,
  Calendar,
  Hash,
  FileJson,
  Copy,
  Check,
} from "lucide-react";

interface FeatureDetailPageProps {
  params: Promise<{ id: string }>;
}

export default function FeatureDetailPage({ params }: FeatureDetailPageProps) {
  const { id } = use(params);
  const router = useRouter();
  const { api, isReady } = useApi();
  const [feature, setFeature] = useState<Feature | null>(null);
  const [tileset, setTileset] = useState<Tileset | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copiedField, setCopiedField] = useState<string | null>(null);

  // GeoJSON Feature を Admin UI の Feature 型に変換
  const convertGeoJsonFeature = (geoJsonFeature: {
    type: string;
    id: string;
    geometry: GeoJSON.Geometry;
    properties: Record<string, unknown>;
  }): Feature => {
    const props = geoJsonFeature.properties || {};
    return {
      id: geoJsonFeature.id,
      tileset_id: (props.tileset_id as string) || "",
      layer_name: (props.layer_name as string) || "default",
      geometry: geoJsonFeature.geometry,
      properties: Object.fromEntries(
        Object.entries(props).filter(
          ([key]) => !["tileset_id", "layer_name", "created_at", "updated_at"].includes(key)
        )
      ),
      created_at: (props.created_at as string) || new Date().toISOString(),
      updated_at: (props.updated_at as string) || new Date().toISOString(),
    };
  };

  const fetchData = async () => {
    if (!isReady) return;
    
    setIsLoading(true);
    setError(null);
    try {
      const featureData = await api.getFeature(id);
      
      // GeoJSON Feature形式を変換
      const rawFeature = featureData as unknown as {
        type: string;
        id: string;
        geometry: GeoJSON.Geometry;
        properties: Record<string, unknown>;
      };
      
      let convertedFeature: Feature;
      if (rawFeature.type === "Feature") {
        convertedFeature = convertGeoJsonFeature(rawFeature);
      } else {
        convertedFeature = featureData;
      }
      
      setFeature(convertedFeature);
      
      // タイルセット情報も取得
      if (convertedFeature.tileset_id) {
        try {
          const tilesetData = await api.getTileset(convertedFeature.tileset_id);
          setTileset(tilesetData);
        } catch {
          // タイルセット取得に失敗しても続行
          console.warn("Failed to fetch tileset info");
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "フィーチャーの取得に失敗しました");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [id, isReady]);

  const handleDelete = async () => {
    await api.deleteFeature(id);
    router.push("/features");
  };

  const copyToClipboard = async (text: string, field: string) => {
    await navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 2000);
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

  const getGeometryDescription = (geometry: GeoJSON.Geometry): string => {
    switch (geometry.type) {
      case "Point":
        const [lng, lat] = geometry.coordinates as [number, number];
        return `経度: ${lng.toFixed(6)}, 緯度: ${lat.toFixed(6)}`;
      case "LineString":
        return `${(geometry.coordinates as [number, number][]).length}点`;
      case "Polygon":
        return `${(geometry.coordinates[0] as [number, number][]).length - 1}点`;
      case "MultiPoint":
        return `${geometry.coordinates.length}点`;
      case "MultiLineString":
        return `${geometry.coordinates.length}本の線`;
      case "MultiPolygon":
        return `${geometry.coordinates.length}個のポリゴン`;
      default:
        return geometry.type;
    }
  };

  // GeoJSONフィーチャーを作成（地図表示用）
  const geoJsonFeature: GeoJSON.Feature | null = feature
    ? {
        type: "Feature",
        properties: feature.properties,
        geometry: feature.geometry,
      }
    : null;

  if (isLoading) {
    return (
      <AdminLayout>
        <div className="flex h-64 items-center justify-center">
          <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </AdminLayout>
    );
  }

  if (error) {
    return (
      <AdminLayout>
        <div className="space-y-6">
          <Button variant="ghost" asChild>
            <Link href="/features">
              <ArrowLeft className="mr-2 h-4 w-4" />
              フィーチャー一覧に戻る
            </Link>
          </Button>
          <Card className="border-destructive">
            <CardContent className="pt-6">
              <p className="text-destructive">{error}</p>
            </CardContent>
          </Card>
        </div>
      </AdminLayout>
    );
  }

  if (!feature) {
    return (
      <AdminLayout>
        <div className="space-y-6">
          <Button variant="ghost" asChild>
            <Link href="/features">
              <ArrowLeft className="mr-2 h-4 w-4" />
              フィーチャー一覧に戻る
            </Link>
          </Button>
          <Card>
            <CardContent className="flex h-32 items-center justify-center pt-6">
              <p className="text-muted-foreground">フィーチャーが見つかりません</p>
            </CardContent>
          </Card>
        </div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* ヘッダー */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="sm" asChild>
              <Link href="/features">
                <ArrowLeft className="mr-2 h-4 w-4" />
                戻る
              </Link>
            </Button>
            <div>
              <h1 className="text-2xl font-bold flex items-center gap-2">
                <MapPin className="h-6 w-6" />
                フィーチャー詳細
              </h1>
              <p className="text-sm text-muted-foreground">
                ID: {feature.id}
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" asChild>
              <Link href={`/features/${id}/edit`}>
                <Pencil className="mr-2 h-4 w-4" />
                編集
              </Link>
            </Button>
            <DeleteFeatureDialog
              featureId={feature.id}
              displayName={`${feature.id.slice(0, 8)}...`}
              onDelete={handleDelete}
            />
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          {/* 基本情報 */}
          <Card>
            <CardHeader>
              <CardTitle>基本情報</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* ID */}
              <div className="flex items-start justify-between">
                <div className="space-y-1">
                  <p className="text-sm font-medium flex items-center gap-2">
                    <Hash className="h-4 w-4" />
                    フィーチャーID
                  </p>
                  <code className="text-sm text-muted-foreground break-all">
                    {feature.id}
                  </code>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => copyToClipboard(feature.id, "id")}
                >
                  {copiedField === "id" ? (
                    <Check className="h-4 w-4 text-green-500" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                </Button>
              </div>

              <Separator />

              {/* タイルセット */}
              <div className="space-y-1">
                <p className="text-sm font-medium flex items-center gap-2">
                  <Layers className="h-4 w-4" />
                  タイルセット
                </p>
                <div className="flex items-center gap-2">
                  <Link
                    href={`/tilesets/${feature.tileset_id}`}
                    className="text-sm text-primary hover:underline"
                  >
                    {tileset?.name || feature.tileset_id}
                  </Link>
                  {tileset && (
                    <Badge variant="outline">{tileset.type}</Badge>
                  )}
                </div>
              </div>

              <Separator />

              {/* レイヤー */}
              <div className="space-y-1">
                <p className="text-sm font-medium">レイヤー名</p>
                <Badge variant="secondary">{feature.layer_name}</Badge>
              </div>

              <Separator />

              {/* ジオメトリタイプ */}
              <div className="space-y-1">
                <p className="text-sm font-medium flex items-center gap-2">
                  <MapPin className="h-4 w-4" />
                  ジオメトリ
                </p>
                <div className="flex items-center gap-2">
                  <Badge>{feature.geometry.type}</Badge>
                  <span className="text-sm text-muted-foreground">
                    {getGeometryDescription(feature.geometry)}
                  </span>
                </div>
              </div>

              <Separator />

              {/* 日時 */}
              <div className="space-y-1">
                <p className="text-sm font-medium flex items-center gap-2">
                  <Calendar className="h-4 w-4" />
                  作成日時
                </p>
                <p className="text-sm text-muted-foreground">
                  {formatDate(feature.created_at)}
                </p>
              </div>

              <div className="space-y-1">
                <p className="text-sm font-medium">更新日時</p>
                <p className="text-sm text-muted-foreground">
                  {formatDate(feature.updated_at)}
                </p>
              </div>
            </CardContent>
          </Card>

          {/* 地図プレビュー */}
          <Card>
            <CardHeader>
              <CardTitle>地図プレビュー</CardTitle>
              <CardDescription>
                フィーチャーのジオメトリを地図上に表示
              </CardDescription>
            </CardHeader>
            <CardContent>
              {geoJsonFeature && (
                <MapView
                  geoJson={geoJsonFeature}
                  height="350px"
                  interactive={true}
                />
              )}
            </CardContent>
          </Card>
        </div>

        {/* プロパティ */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileJson className="h-5 w-5" />
              プロパティ（属性）
            </CardTitle>
            <CardDescription>
              フィーチャーに付加された属性情報
            </CardDescription>
          </CardHeader>
          <CardContent>
            {Object.keys(feature.properties).length === 0 ? (
              <p className="text-sm text-muted-foreground">プロパティはありません</p>
            ) : (
              <div className="space-y-3">
                {Object.entries(feature.properties).map(([key, value]) => (
                  <div
                    key={key}
                    className="flex items-start justify-between rounded-md border p-3"
                  >
                    <div className="space-y-1">
                      <p className="text-sm font-medium">{key}</p>
                      <p className="text-sm text-muted-foreground break-all">
                        {typeof value === "object"
                          ? JSON.stringify(value, null, 2)
                          : String(value)}
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() =>
                        copyToClipboard(
                          typeof value === "object" ? JSON.stringify(value) : String(value),
                          key
                        )
                      }
                    >
                      {copiedField === key ? (
                        <Check className="h-4 w-4 text-green-500" />
                      ) : (
                        <Copy className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* GeoJSON */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span className="flex items-center gap-2">
                <FileJson className="h-5 w-5" />
                GeoJSON
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() =>
                  copyToClipboard(JSON.stringify(geoJsonFeature, null, 2), "geojson")
                }
              >
                {copiedField === "geojson" ? (
                  <>
                    <Check className="mr-2 h-4 w-4 text-green-500" />
                    コピーしました
                  </>
                ) : (
                  <>
                    <Copy className="mr-2 h-4 w-4" />
                    コピー
                  </>
                )}
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="max-h-96 overflow-auto rounded-md bg-muted p-4 text-sm">
              {JSON.stringify(geoJsonFeature, null, 2)}
            </pre>
          </CardContent>
        </Card>
      </div>
    </AdminLayout>
  );
}
