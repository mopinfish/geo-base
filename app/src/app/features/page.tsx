"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AdminLayout } from "@/components/layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useApi } from "@/hooks/use-api";
import type { Feature, Tileset, BatchOperationResponse } from "@/lib/api";
import { 
  Plus, 
  RefreshCw, 
  Search, 
  Map,
  Eye,
  Pencil,
  MapPin,
  ChevronDown,
  FileJson,
  Trash2,
  Loader2,
  Download,
  Edit,
  FileText,
} from "lucide-react";

export default function FeaturesPage() {
  const router = useRouter();
  const { api, isReady } = useApi();
  const [features, setFeatures] = useState<Feature[]>([]);
  const [tilesets, setTilesets] = useState<Tileset[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTileset, setSelectedTileset] = useState<string>("all");
  const [limit, setLimit] = useState(50);
  
  // 選択状態の管理
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  
  // 一括削除ダイアログの状態
  const [bulkDeleteDialogOpen, setBulkDeleteDialogOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deletePreview, setDeletePreview] = useState<BatchOperationResponse | null>(null);
  
  // エクスポートダイアログの状態（タイルセット単位）
  const [exportDialogOpen, setExportDialogOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [exportFormat, setExportFormat] = useState<'geojson' | 'csv'>('geojson');
  
  // 選択エクスポートダイアログの状態（選択フィーチャー単位）
  const [exportSelectedDialogOpen, setExportSelectedDialogOpen] = useState(false);
  const [isExportingSelected, setIsExportingSelected] = useState(false);
  const [exportSelectedFormat, setExportSelectedFormat] = useState<'geojson' | 'csv'>('geojson');
  
  // バッチ更新ダイアログの状態
  const [batchUpdateDialogOpen, setBatchUpdateDialogOpen] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const [updateLayerName, setUpdateLayerName] = useState("");
  const [updateProperties, setUpdateProperties] = useState("");
  const [mergeProperties, setMergeProperties] = useState(true);

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
      const [featuresResult, tilesetsResult] = await Promise.allSettled([
        api.listFeatures({
          limit,
          tileset_id: selectedTileset !== "all" ? selectedTileset : undefined,
        }),
        api.listTilesets(),
      ]);
      
      // フィーチャー結果の処理（GeoJSON FeatureCollection形式に対応）
      if (featuresResult.status === "fulfilled") {
        const result = featuresResult.value as unknown;
        
        if (Array.isArray(result)) {
          // 配列形式
          setFeatures(result);
        } else if (result && typeof result === 'object') {
          const obj = result as Record<string, unknown>;
          
          if (obj.type === "FeatureCollection" && Array.isArray(obj.features)) {
            // GeoJSON FeatureCollection形式 → 変換
            const converted = (obj.features as Array<{
              type: string;
              id: string;
              geometry: GeoJSON.Geometry;
              properties: Record<string, unknown>;
            }>).map(convertGeoJsonFeature);
            setFeatures(converted);
          } else if ('features' in obj && Array.isArray(obj.features)) {
            // {"features": [...], "count": N} 形式
            setFeatures(obj.features as Feature[]);
          } else {
            setFeatures([]);
          }
        } else {
          setFeatures([]);
        }
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
      
      // 選択状態をクリア
      setSelectedIds(new Set());
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

  // 成功メッセージの自動消去
  useEffect(() => {
    if (successMessage) {
      const timer = setTimeout(() => setSuccessMessage(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [successMessage]);

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

  const getTilesetName = (tilesetId: string | undefined | null): string => {
    if (!tilesetId) return "(未設定)";
    const tileset = safeTilesets.find((t) => t.id === tilesetId);
    return tileset?.name || tilesetId.slice(0, 8) + "...";
  };

  // 選択状態の切り替え
  const toggleSelection = (id: string) => {
    const newSelection = new Set(selectedIds);
    if (newSelection.has(id)) {
      newSelection.delete(id);
    } else {
      newSelection.add(id);
    }
    setSelectedIds(newSelection);
  };

  // 全選択/全解除
  const toggleAllSelection = () => {
    if (selectedIds.size === filteredFeatures.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(filteredFeatures.map(f => f.id)));
    }
  };

  // 一括削除のプレビュー取得
  const handleBulkDeletePreview = async () => {
    if (selectedIds.size === 0) return;
    
    try {
      const result = await api.batchDeleteFeatures({
        feature_ids: Array.from(selectedIds),
        dry_run: true,
      });
      setDeletePreview(result);
      setBulkDeleteDialogOpen(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "プレビュー取得に失敗しました");
    }
  };

  // 一括削除の実行
  const handleBulkDelete = async () => {
    if (selectedIds.size === 0) return;

    setIsDeleting(true);
    setError(null);
    
    try {
      const result = await api.batchDeleteFeatures({
        feature_ids: Array.from(selectedIds),
      });
      
      if (result.failed_count > 0) {
        setError(`${result.failed_count}件の削除に失敗しました: ${result.errors.join(', ')}`);
      } else {
        setSuccessMessage(`${result.success_count}件のフィーチャーを削除しました`);
      }
      
      // データを再取得
      await fetchData();
      setBulkDeleteDialogOpen(false);
      setDeletePreview(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "削除に失敗しました");
    } finally {
      setIsDeleting(false);
    }
  };

  // エクスポートの実行
  const handleExport = async () => {
    if (selectedTileset === "all") {
      setError("エクスポートにはタイルセットを選択してください");
      return;
    }

    setIsExporting(true);
    setError(null);

    try {
      if (exportFormat === 'geojson') {
        const result = await api.exportFeatures({
          tileset_id: selectedTileset,
        });
        
        // ダウンロード
        const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/geo+json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${selectedTileset}.geojson`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        setSuccessMessage(`${result.features.length}件のフィーチャーをエクスポートしました`);
      } else {
        const blob = await api.exportFeaturesCsv({
          tileset_id: selectedTileset,
        });
        
        // ダウンロード
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${selectedTileset}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        setSuccessMessage('CSVエクスポートが完了しました');
      }
      
      setExportDialogOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "エクスポートに失敗しました");
    } finally {
      setIsExporting(false);
    }
  };

  // 選択フィーチャーのエクスポート
  const handleExportSelected = async () => {
    if (selectedIds.size === 0) {
      setError("エクスポートするフィーチャーを選択してください");
      return;
    }

    setIsExportingSelected(true);
    setError(null);

    try {
      const featureIds = Array.from(selectedIds);
      
      if (exportSelectedFormat === 'geojson') {
        const result = await api.exportFeatures({
          feature_ids: featureIds,
        });
        
        // ダウンロード
        const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/geo+json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `selected_features_${featureIds.length}.geojson`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        setSuccessMessage(`${result.features.length}件のフィーチャーをエクスポートしました`);
      } else {
        const blob = await api.exportFeaturesCsv({
          feature_ids: featureIds,
        });
        
        // ダウンロード
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `selected_features_${featureIds.length}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        setSuccessMessage('CSVエクスポートが完了しました');
      }
      
      setExportSelectedDialogOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "エクスポートに失敗しました");
    } finally {
      setIsExportingSelected(false);
    }
  };

  // バッチ更新の実行
  const handleBatchUpdate = async () => {
    if (selectedIds.size === 0) return;

    setIsUpdating(true);
    setError(null);

    try {
      const updates: { layer_name?: string; properties?: Record<string, unknown> } = {};
      
      if (updateLayerName.trim()) {
        updates.layer_name = updateLayerName.trim();
      }
      
      if (updateProperties.trim()) {
        try {
          updates.properties = JSON.parse(updateProperties);
        } catch {
          setError("プロパティのJSON形式が不正です");
          setIsUpdating(false);
          return;
        }
      }

      if (Object.keys(updates).length === 0) {
        setError("更新内容を入力してください");
        setIsUpdating(false);
        return;
      }

      const result = await api.batchUpdateFeatures({
        feature_ids: Array.from(selectedIds),
        updates,
        merge_properties: mergeProperties,
      });

      if (result.failed_count > 0) {
        setError(`${result.failed_count}件の更新に失敗しました: ${result.errors.join(', ')}`);
      } else {
        setSuccessMessage(`${result.success_count}件のフィーチャーを更新しました`);
      }

      // データを再取得
      await fetchData();
      setBatchUpdateDialogOpen(false);
      setUpdateLayerName("");
      setUpdateProperties("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "更新に失敗しました");
    } finally {
      setIsUpdating(false);
    }
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
            <Button 
              variant="outline" 
              size="sm"
              onClick={() => setExportDialogOpen(true)}
              disabled={selectedTileset === "all"}
              title={selectedTileset === "all" ? "タイルセットを選択してください" : "フィーチャーをエクスポート"}
            >
              <Download className="mr-2 h-4 w-4" />
              エクスポート
            </Button>
            <Button 
              variant="outline" 
              size="sm"
              onClick={() => router.push("/features/import")}
            >
              <FileJson className="mr-2 h-4 w-4" />
              インポート
            </Button>
            <Button size="sm" onClick={() => router.push("/features/new")}>
              <Plus className="mr-2 h-4 w-4" />
              新規作成
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
              {/* ネイティブselectを使用（Radix UIのポータル問題を回避） */}
              <div className="relative">
                <select
                  value={selectedTileset}
                  onChange={(e) => setSelectedTileset(e.target.value)}
                  className="h-9 w-[200px] appearance-none rounded-md border border-input bg-transparent px-3 py-2 pr-8 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
                >
                  <option value="all">すべてのタイルセット</option>
                  {safeTilesets.map((tileset) => (
                    <option key={tileset.id} value={tileset.id}>
                      {tileset.name}
                    </option>
                  ))}
                </select>
                <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-4 w-4 -translate-y-1/2 opacity-50" />
              </div>
              <div className="relative">
                <select
                  value={String(limit)}
                  onChange={(e) => setLimit(Number(e.target.value))}
                  className="h-9 w-[120px] appearance-none rounded-md border border-input bg-transparent px-3 py-2 pr-8 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
                >
                  <option value="10">10件</option>
                  <option value="50">50件</option>
                  <option value="100">100件</option>
                </select>
                <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-4 w-4 -translate-y-1/2 opacity-50" />
              </div>
            </div>
            {selectedTileset === "all" && (
              <p className="mt-2 text-xs text-muted-foreground">
                ※ エクスポートするには、上のドロップダウンからタイルセットを選択してください
              </p>
            )}
          </CardContent>
        </Card>

        {/* 成功メッセージ */}
        {successMessage && (
          <Card className="border-green-500 bg-green-50 dark:bg-green-950">
            <CardContent className="py-3">
              <p className="text-green-700 dark:text-green-300">{successMessage}</p>
            </CardContent>
          </Card>
        )}

        {/* エラー表示 */}
        {error && (
          <Card className="border-destructive">
            <CardContent className="pt-6">
              <p className="text-destructive">{error}</p>
            </CardContent>
          </Card>
        )}

        {/* 一括操作バー */}
        {selectedIds.size > 0 && (
          <Card className="bg-muted/50">
            <CardContent className="py-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">
                  {selectedIds.size}件を選択中
                </span>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setSelectedIds(new Set())}
                  >
                    選択解除
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setExportSelectedDialogOpen(true)}
                  >
                    <Download className="mr-2 h-4 w-4" />
                    選択をエクスポート
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setBatchUpdateDialogOpen(true)}
                  >
                    <Edit className="mr-2 h-4 w-4" />
                    一括更新
                  </Button>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={handleBulkDeletePreview}
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    一括削除
                  </Button>
                </div>
              </div>
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
            {filteredFeatures.length > 0 && selectedIds.size === 0 && (
              <p className="text-xs text-muted-foreground">
                ※ チェックボックスでフィーチャーを選択すると、一括更新・一括削除ができます
              </p>
            )}
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
                <div className="mt-2 flex gap-2">
                  <button 
                    onClick={() => router.push("/features/new")}
                    className="text-primary hover:underline"
                  >
                    新規作成
                  </button>
                  <span>または</span>
                  <button 
                    onClick={() => router.push("/features/import")}
                    className="text-primary hover:underline"
                  >
                    GeoJSONインポート
                  </button>
                </div>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-12">
                      <input
                        type="checkbox"
                        checked={selectedIds.size === filteredFeatures.length && filteredFeatures.length > 0}
                        onChange={toggleAllSelection}
                        className="h-4 w-4 rounded border-gray-300"
                      />
                    </TableHead>
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
                    <TableRow 
                      key={feature.id}
                      className={selectedIds.has(feature.id) ? "bg-muted/50" : ""}
                    >
                      <TableCell>
                        <input
                          type="checkbox"
                          checked={selectedIds.has(feature.id)}
                          onChange={() => toggleSelection(feature.id)}
                          className="h-4 w-4 rounded border-gray-300"
                        />
                      </TableCell>
                      <TableCell>
                        <button 
                          onClick={() => router.push(`/features/${feature.id}`)}
                          className="hover:underline"
                        >
                          <code className="text-xs">{feature.id.slice(0, 8)}...</code>
                        </button>
                      </TableCell>
                      <TableCell>
                        {feature.tileset_id ? (
                          <button 
                            onClick={() => router.push(`/tilesets/${feature.tileset_id}`)}
                            className="text-sm hover:underline"
                          >
                            {getTilesetName(feature.tileset_id)}
                          </button>
                        ) : (
                          <span className="text-sm text-muted-foreground">
                            {getTilesetName(feature.tileset_id)}
                          </span>
                        )}
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
                          <Button 
                            variant="ghost" 
                            size="icon"
                            onClick={() => router.push(`/features/${feature.id}`)}
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                          <Button 
                            variant="ghost" 
                            size="icon"
                            onClick={() => router.push(`/features/${feature.id}/edit`)}
                          >
                            <Pencil className="h-4 w-4" />
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

      {/* 一括削除確認ダイアログ */}
      <AlertDialog open={bulkDeleteDialogOpen} onOpenChange={setBulkDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>フィーチャーを一括削除しますか？</AlertDialogTitle>
            <AlertDialogDescription>
              {deletePreview ? (
                <span>
                  {deletePreview.total_count}件のフィーチャーを削除します。
                  この操作は取り消せません。
                </span>
              ) : (
                <span>
                  選択した {selectedIds.size} 件のフィーチャーを削除します。
                  この操作は取り消せません。
                </span>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>キャンセル</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleBulkDelete}
              disabled={isDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isDeleting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  削除中...
                </>
              ) : (
                <>
                  <Trash2 className="mr-2 h-4 w-4" />
                  {selectedIds.size}件を削除
                </>
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* エクスポートダイアログ */}
      <Dialog open={exportDialogOpen} onOpenChange={setExportDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>フィーチャーをエクスポート</DialogTitle>
            <DialogDescription>
              選択したタイルセットのフィーチャーをエクスポートします。
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>タイルセット</Label>
              <p className="text-sm text-muted-foreground">
                {getTilesetName(selectedTileset)}
              </p>
            </div>
            
            <div className="space-y-2">
              <Label>フォーマット</Label>
              <div className="flex gap-4">
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    checked={exportFormat === 'geojson'}
                    onChange={() => setExportFormat('geojson')}
                  />
                  <FileJson className="h-4 w-4" />
                  GeoJSON
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    checked={exportFormat === 'csv'}
                    onChange={() => setExportFormat('csv')}
                  />
                  <FileText className="h-4 w-4" />
                  CSV
                </label>
              </div>
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setExportDialogOpen(false)}>
              キャンセル
            </Button>
            <Button onClick={handleExport} disabled={isExporting}>
              {isExporting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  エクスポート中...
                </>
              ) : (
                <>
                  <Download className="mr-2 h-4 w-4" />
                  エクスポート
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* バッチ更新ダイアログ */}
      <Dialog open={batchUpdateDialogOpen} onOpenChange={setBatchUpdateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>フィーチャーを一括更新</DialogTitle>
            <DialogDescription>
              選択した {selectedIds.size} 件のフィーチャーを更新します。
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="layer-name">レイヤー名（任意）</Label>
              <Input
                id="layer-name"
                placeholder="新しいレイヤー名"
                value={updateLayerName}
                onChange={(e) => setUpdateLayerName(e.target.value)}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="properties">プロパティ（JSON形式、任意）</Label>
              <textarea
                id="properties"
                className="min-h-[100px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
                placeholder='{"status": "reviewed", "category": "landmark"}'
                value={updateProperties}
                onChange={(e) => setUpdateProperties(e.target.value)}
              />
            </div>
            
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="merge-properties"
                checked={mergeProperties}
                onChange={(e) => setMergeProperties(e.target.checked)}
              />
              <Label htmlFor="merge-properties">
                既存のプロパティとマージする（オフの場合は置換）
              </Label>
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setBatchUpdateDialogOpen(false)}>
              キャンセル
            </Button>
            <Button onClick={handleBatchUpdate} disabled={isUpdating}>
              {isUpdating ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  更新中...
                </>
              ) : (
                <>
                  <Edit className="mr-2 h-4 w-4" />
                  {selectedIds.size}件を更新
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 選択エクスポートダイアログ */}
      <Dialog open={exportSelectedDialogOpen} onOpenChange={setExportSelectedDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>選択したフィーチャーをエクスポート</DialogTitle>
            <DialogDescription>
              選択した {selectedIds.size} 件のフィーチャーをエクスポートします。
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>フォーマット</Label>
              <div className="flex gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    checked={exportSelectedFormat === 'geojson'}
                    onChange={() => setExportSelectedFormat('geojson')}
                    className="h-4 w-4"
                  />
                  <FileJson className="h-4 w-4" />
                  GeoJSON
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    checked={exportSelectedFormat === 'csv'}
                    onChange={() => setExportSelectedFormat('csv')}
                    className="h-4 w-4"
                  />
                  <FileText className="h-4 w-4" />
                  CSV
                </label>
              </div>
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setExportSelectedDialogOpen(false)}>
              キャンセル
            </Button>
            <Button onClick={handleExportSelected} disabled={isExportingSelected}>
              {isExportingSelected ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  エクスポート中...
                </>
              ) : (
                <>
                  <Download className="mr-2 h-4 w-4" />
                  {selectedIds.size}件をエクスポート
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AdminLayout>
  );
}
