"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AdminLayout } from "@/components/layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useApi } from "@/hooks/use-api";
import type { Feature, Tileset } from "@/lib/api";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { 
  Plus, 
  RefreshCw, 
  Search, 
  Map,
  Eye,
  Pencil,
  MapPin,
} from "lucide-react";

export default function FeaturesPage() {
  const { api, isReady } = useApi();
  const [features, setFeatures] = useState<Feature[]>([]);
  const [tilesets, setTilesets] = useState<Tileset[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTileset, setSelectedTileset] = useState<string>("all");
  const [limit, setLimit] = useState(50);

  const fetchData = async () => {
    if (!isReady) return;
    
    setIsLoading(true);
    setError(null);
    try {
      const [featuresResult, tilesetsResult] = await Promise.allSettled([
        api.listFeatures({
          limit,
          tileset_id: selectedTileset !== "all" ? selectedTileset : undefined,
        }),
        api.listTilesets(),
      ]);
      
      // フィーチャー結果の処理（配列であることを確認）
      if (featuresResult.status === "fulfilled" && Array.isArray(featuresResult.value)) {
        setFeatures(featuresResult.value);
      } else {
        setFeatures([]);
      }
      
      // タイルセット結果の処理（配列であることを確認）
      if (tilesetsResult.status === "fulfilled") {
        const result = tilesetsResult.value;
        if (Array.isArray(result)) {
          setTilesets(result);
        } else if (result && typeof result === 'object' && 'tilesets' in result) {
          setTilesets((result as { tilesets: Tileset[] }).tilesets);
        } else {
          setTilesets([]);
        }
      } else {
        setTilesets([]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "データの取得に失敗しました");
      setFeatures([]);
      setTilesets([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [selectedTileset, limit, isReady]);

  // 安全にフィルタリング（配列でない場合に備える）
  const safeFeatures = Array.isArray(features) ? features : [];
  const filteredFeatures = safeFeatures.filter((feature) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    const propsString = JSON.stringify(feature.properties).toLowerCase();
    return (
      feature.layer_name.toLowerCase().includes(query) ||
      propsString.includes(query)
    );
  });
  
  // 安全なタイルセット配列
  const safeTilesets = Array.isArray(tilesets) ? tilesets : [];

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("ja-JP", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  const getGeometryType = (geometry: GeoJSON.Geometry): string => {
    return geometry.type;
  };

  const getTilesetName = (tilesetId: string): string => {
    const tileset = safeTilesets.find((t) => t.id === tilesetId);
    return tileset?.name || tilesetId.slice(0, 8) + "...";
  };

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* ヘッダー */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">フィーチャー</h1>
            <p className="text-muted-foreground">
              地物データの一覧と管理
            </p>
          </div>
          <div className="flex gap-2">
            <Button onClick={fetchData} variant="outline" size="sm">
              <RefreshCw className={`mr-2 h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
              更新
            </Button>
            <Button asChild>
              <Link href="/features/new">
                <Plus className="mr-2 h-4 w-4" />
                新規作成
              </Link>
            </Button>
          </div>
        </div>

        {/* フィルター */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-col gap-4 md:flex-row md:items-center">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="フィーチャーを検索..."
                  className="pl-9"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
              <Select value={selectedTileset} onValueChange={setSelectedTileset}>
                <SelectTrigger className="w-[200px]">
                  <SelectValue placeholder="タイルセット" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">すべてのタイルセット</SelectItem>
                  {safeTilesets.map((tileset) => (
                    <SelectItem key={tileset.id} value={tileset.id}>
                      {tileset.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={String(limit)} onValueChange={(v) => setLimit(Number(v))}>
                <SelectTrigger className="w-[120px]">
                  <SelectValue placeholder="表示件数" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="10">10件</SelectItem>
                  <SelectItem value="50">50件</SelectItem>
                  <SelectItem value="100">100件</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* エラー表示 */}
        {error && (
          <Card className="border-destructive">
            <CardContent className="pt-6">
              <p className="text-destructive">{error}</p>
            </CardContent>
          </Card>
        )}

        {/* フィーチャー一覧 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Map className="h-5 w-5" />
              フィーチャー一覧
              <Badge variant="secondary" className="ml-2">
                {filteredFeatures.length} 件
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex h-32 items-center justify-center">
                <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : filteredFeatures.length === 0 ? (
              <div className="flex h-32 flex-col items-center justify-center text-muted-foreground">
                <MapPin className="mb-2 h-8 w-8" />
                <p>フィーチャーがありません</p>
                <Button asChild variant="link" className="mt-2">
                  <Link href="/features/new">新規フィーチャーを作成</Link>
                </Button>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>ID</TableHead>
                    <TableHead>タイルセット</TableHead>
                    <TableHead>レイヤー</TableHead>
                    <TableHead>ジオメトリ</TableHead>
                    <TableHead>プロパティ</TableHead>
                    <TableHead>更新日</TableHead>
                    <TableHead className="text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredFeatures.map((feature) => (
                    <TableRow key={feature.id}>
                      <TableCell>
                        <Link 
                          href={`/features/${feature.id}`}
                          className="hover:underline"
                        >
                          <code className="text-xs">{feature.id.slice(0, 8)}...</code>
                        </Link>
                      </TableCell>
                      <TableCell>
                        <Link 
                          href={`/tilesets/${feature.tileset_id}`}
                          className="text-sm hover:underline"
                        >
                          {getTilesetName(feature.tileset_id)}
                        </Link>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{feature.layer_name}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary">
                          {getGeometryType(feature.geometry)}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <code className="text-xs">
                          {Object.keys(feature.properties).length} 属性
                        </code>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {formatDate(feature.updated_at)}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button variant="ghost" size="icon" asChild>
                            <Link href={`/features/${feature.id}`}>
                              <Eye className="h-4 w-4" />
                            </Link>
                          </Button>
                          <Button variant="ghost" size="icon" asChild>
                            <Link href={`/features/${feature.id}/edit`}>
                              <Pencil className="h-4 w-4" />
                            </Link>
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </AdminLayout>
  );
}
