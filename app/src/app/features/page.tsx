"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useTranslations, useLocale } from "next-intl";
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
  const t = useTranslations("features.list");
  const locale = useLocale();
  const dateLocale = locale === "ja" ? "ja-JP" : "en-US";
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

  const fetchData = useCallback(async () => {
    if (!isReady) return;
    
    setIsLoading(true);
    setError(null);
    try {
      const [featuresResult, tilesetsResult] = await Promise.allSettled([
        api.listFeatures({
          limit,
          tileset_id: selectedTileset !== "all" ? selectedTileset : undefined,
        }),
        api.listTilesets({ include_private: true }),
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
      setError(err instanceof Error ? err.message : t("error_fetch"));
      setFeatures([]);
      setTilesets([]);
    } finally {
      setIsLoading(false);
    }
  }, [api, isReady, selectedTileset, limit, t]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

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
    return new Date(dateString).toLocaleDateString(dateLocale, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  const getGeometryType = (geometry: GeoJSON.Geometry): string => {
    return geometry.type;
  };

  const getTilesetName = (tilesetId: string | undefined | null): string => {
    if (!tilesetId) return t("unset");
    const tileset = safeTilesets.find((ts) => ts.id === tilesetId);
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
      setError(err instanceof Error ? err.message : t("error_preview"));
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
        setError(t("partial_error_delete", { count: result.failed_count }) + ": " + result.errors.join(', '));
      } else {
        setSuccessMessage(t("success_delete", { count: result.success_count }));
      }

      // データを再取得
      await fetchData();
      setBulkDeleteDialogOpen(false);
      setDeletePreview(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("error_delete"));
    } finally {
      setIsDeleting(false);
    }
  };

  // エクスポートの実行
  const handleExport = async () => {
    if (selectedTileset === "all") {
      setError(t("error_export_no_tileset"));
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
        
        setSuccessMessage(t("success_export", { count: result.features.length }));
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

        setSuccessMessage(t("success_csv_export"));
      }

      setExportDialogOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("error_export"));
    } finally {
      setIsExporting(false);
    }
  };

  // 選択フィーチャーのエクスポート
  const handleExportSelected = async () => {
    if (selectedIds.size === 0) {
      setError(t("error_export_no_selection"));
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
        
        setSuccessMessage(t("success_export", { count: result.features.length }));
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

        setSuccessMessage(t("success_csv_export"));
      }

      setExportSelectedDialogOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("error_export"));
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
          setError(t("error_invalid_properties_json"));
          setIsUpdating(false);
          return;
        }
      }

      if (Object.keys(updates).length === 0) {
        setError(t("error_no_update_content"));
        setIsUpdating(false);
        return;
      }

      const result = await api.batchUpdateFeatures({
        feature_ids: Array.from(selectedIds),
        updates,
        merge_properties: mergeProperties,
      });

      if (result.failed_count > 0) {
        setError(t("partial_error_update", { count: result.failed_count }) + ": " + result.errors.join(', '));
      } else {
        setSuccessMessage(t("success_update", { count: result.success_count }));
      }

      // データを再取得
      await fetchData();
      setBatchUpdateDialogOpen(false);
      setUpdateLayerName("");
      setUpdateProperties("");
    } catch (err) {
      setError(err instanceof Error ? err.message : t("error_update"));
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
            <h1 className="text-3xl font-bold">{t("title")}</h1>
            <p className="text-muted-foreground">
              {t("subtitle")}
            </p>
          </div>
          <div className="flex gap-2">
            <Button onClick={fetchData} variant="outline" size="sm">
              <RefreshCw className={`mr-2 h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
              {t("refresh")}
            </Button>
            <Button
              data-testid="feature-export-open"
              variant="outline"
              size="sm"
              onClick={() => setExportDialogOpen(true)}
              disabled={selectedTileset === "all"}
              title={selectedTileset === "all" ? t("export_disabled_tooltip") : t("export")}
            >
              <Download className="mr-2 h-4 w-4" />
              {t("export")}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => router.push("/features/import")}
            >
              <FileJson className="mr-2 h-4 w-4" />
              {t("import")}
            </Button>
            <Button size="sm" onClick={() => router.push("/features/new")}>
              <Plus className="mr-2 h-4 w-4" />
              {t("new")}
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
                  data-testid="feature-search-input"
                  placeholder={t("search_placeholder")}
                  className="pl-9"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
              {/* ネイティブselectを使用（Radix UIのポータル問題を回避） */}
              <div className="relative">
                <select
                  data-testid="feature-filter-tileset"
                  aria-label={t("filter_tileset_aria")}
                  value={selectedTileset}
                  onChange={(e) => setSelectedTileset(e.target.value)}
                  className="h-9 w-[200px] appearance-none rounded-md border border-input bg-transparent px-3 py-2 pr-8 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
                >
                  <option value="all">{t("filter_tileset_placeholder")}</option>
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
                  data-testid="feature-limit-select"
                  aria-label={t("limit_aria")}
                  value={String(limit)}
                  onChange={(e) => setLimit(Number(e.target.value))}
                  className="h-9 w-[120px] appearance-none rounded-md border border-input bg-transparent px-3 py-2 pr-8 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
                >
                  <option value="10">{t("limit_10")}</option>
                  <option value="50">{t("limit_50")}</option>
                  <option value="100">{t("limit_100")}</option>
                </select>
                <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-4 w-4 -translate-y-1/2 opacity-50" />
              </div>
            </div>
            {selectedTileset === "all" && (
              <p className="mt-2 text-xs text-muted-foreground">
                {t("export_hint")}
              </p>
            )}
          </CardContent>
        </Card>

        {/* 成功メッセージ */}
        {successMessage && (
          <Card
            className="border-green-500 bg-green-50 dark:bg-green-950"
            data-testid="feature-success-message"
          >
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
                  {t("selected_count", { count: selectedIds.size })}
                </span>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setSelectedIds(new Set())}
                  >
                    {t("clear_selection")}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setExportSelectedDialogOpen(true)}
                  >
                    <Download className="mr-2 h-4 w-4" />
                    {t("export_selected")}
                  </Button>
                  <Button
                    data-testid="feature-bulk-update"
                    variant="outline"
                    size="sm"
                    onClick={() => setBatchUpdateDialogOpen(true)}
                  >
                    <Edit className="mr-2 h-4 w-4" />
                    {t("bulk_update")}
                  </Button>
                  <Button
                    data-testid="feature-bulk-delete"
                    variant="destructive"
                    size="sm"
                    onClick={handleBulkDeletePreview}
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    {t("bulk_delete")}
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
              {t("section_title")}
              <Badge variant="secondary" className="ml-2">
                {t("count_badge", { count: filteredFeatures.length })}
              </Badge>
            </CardTitle>
            {filteredFeatures.length > 0 && selectedIds.size === 0 && (
              <p className="text-xs text-muted-foreground">
                {t("select_hint")}
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
                <p>{t("empty_no_features")}</p>
                <div className="mt-2 flex gap-2">
                  <button
                    onClick={() => router.push("/features/new")}
                    className="text-primary hover:underline"
                  >
                    {t("empty_new")}
                  </button>
                  <span>{t("empty_or")}</span>
                  <button
                    onClick={() => router.push("/features/import")}
                    className="text-primary hover:underline"
                  >
                    {t("empty_import")}
                  </button>
                </div>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-12">
                      <input
                        data-testid="feature-select-all"
                        type="checkbox"
                        aria-label={t("select_all_aria")}
                        checked={selectedIds.size === filteredFeatures.length && filteredFeatures.length > 0}
                        onChange={toggleAllSelection}
                        className="h-4 w-4 rounded border-gray-300"
                      />
                    </TableHead>
                    <TableHead>{t("column_id")}</TableHead>
                    <TableHead>{t("column_tileset")}</TableHead>
                    <TableHead>{t("column_layer")}</TableHead>
                    <TableHead>{t("column_geometry")}</TableHead>
                    <TableHead>{t("column_properties")}</TableHead>
                    <TableHead>{t("column_updated")}</TableHead>
                    <TableHead className="text-right">{t("column_actions")}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredFeatures.map((feature) => (
                    <TableRow
                      key={feature.id}
                      data-testid="feature-list-row"
                      className={selectedIds.has(feature.id) ? "bg-muted/50" : ""}
                    >
                      <TableCell>
                        <input
                          data-testid="feature-row-checkbox"
                          type="checkbox"
                          aria-label={t("select_row_aria")}
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
                          {t("property_count", { count: Object.keys(feature.properties).length })}
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
                            aria-label={t("detail_aria")}
                            onClick={() => router.push(`/features/${feature.id}`)}
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            aria-label={t("edit_aria")}
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
            <AlertDialogTitle>{t("bulk_delete_title")}</AlertDialogTitle>
            <AlertDialogDescription>
              {deletePreview ? (
                <span>
                  {t("bulk_delete_description_preview", { count: deletePreview.total_count })}
                </span>
              ) : (
                <span>
                  {t("bulk_delete_description_no_preview", { count: selectedIds.size })}
                </span>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>{t("cancel")}</AlertDialogCancel>
            <AlertDialogAction
              data-testid="feature-bulk-delete-confirm"
              onClick={handleBulkDelete}
              disabled={isDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isDeleting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {t("deleting")}
                </>
              ) : (
                <>
                  <Trash2 className="mr-2 h-4 w-4" />
                  {t("bulk_delete_button", { count: selectedIds.size })}
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
            <DialogTitle>{t("export_dialog_title")}</DialogTitle>
            <DialogDescription>
              {t("export_dialog_description")}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>{t("export_dialog_tileset_label")}</Label>
              <p className="text-sm text-muted-foreground">
                {getTilesetName(selectedTileset)}
              </p>
            </div>

            <div className="space-y-2">
              <Label>{t("export_dialog_format_label")}</Label>
              <div className="flex gap-4">
                <label className="flex items-center gap-2">
                  <input
                    data-testid="feature-export-format-geojson"
                    type="radio"
                    checked={exportFormat === 'geojson'}
                    onChange={() => setExportFormat('geojson')}
                  />
                  <FileJson className="h-4 w-4" />
                  GeoJSON
                </label>
                <label className="flex items-center gap-2">
                  <input
                    data-testid="feature-export-format-csv"
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
              {t("cancel")}
            </Button>
            <Button
              data-testid="feature-export-submit"
              onClick={handleExport}
              disabled={isExporting}
            >
              {isExporting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {t("exporting")}
                </>
              ) : (
                <>
                  <Download className="mr-2 h-4 w-4" />
                  {t("export_button")}
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
            <DialogTitle>{t("batch_update_title")}</DialogTitle>
            <DialogDescription>
              {t("batch_update_description", { count: selectedIds.size })}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="layer-name">{t("batch_update_layer_label")}</Label>
              <Input
                id="layer-name"
                placeholder={t("batch_update_layer_placeholder")}
                value={updateLayerName}
                onChange={(e) => setUpdateLayerName(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="properties">{t("batch_update_properties_label")}</Label>
              <textarea
                data-testid="feature-bulk-update-properties"
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
                {t("batch_update_merge_checkbox")}
              </Label>
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setBatchUpdateDialogOpen(false)}>
              {t("cancel")}
            </Button>
            <Button
              data-testid="feature-bulk-update-submit"
              onClick={handleBatchUpdate}
              disabled={isUpdating}
            >
              {isUpdating ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {t("updating")}
                </>
              ) : (
                <>
                  <Edit className="mr-2 h-4 w-4" />
                  {t("batch_update_button", { count: selectedIds.size })}
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
            <DialogTitle>{t("export_selected_title")}</DialogTitle>
            <DialogDescription>
              {t("export_selected_description", { count: selectedIds.size })}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>{t("export_selected_format_label")}</Label>
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
              {t("cancel")}
            </Button>
            <Button onClick={handleExportSelected} disabled={isExportingSelected}>
              {isExportingSelected ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {t("exporting")}
                </>
              ) : (
                <>
                  <Download className="mr-2 h-4 w-4" />
                  {t("export_selected_button", { count: selectedIds.size })}
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AdminLayout>
  );
}
