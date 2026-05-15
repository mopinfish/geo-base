"use client";

import { useEffect, useState, useCallback } from "react";
import { useTranslations, useLocale } from "next-intl";
import Link from "next/link";
import { AdminLayout } from "@/components/layout";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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
import { useApi } from "@/hooks/use-api";
import { isOpenableUrl, type Datasource, type DatasourceType } from "@/lib/api";
import {
  Plus,
  RefreshCw,
  Database,
  Map,
  Trash2,
  ExternalLink,
  FileJson,
  Image as ImageIcon,
  Eye,
  Loader2,
  CheckCircle2,
  XCircle,
  Play,
} from "lucide-react";

export default function DatasourcesPage() {
  const t = useTranslations("datasources.list");
  const locale = useLocale();
  const dateLocale = locale === "ja" ? "ja-JP" : "en-US";
  const { api, isReady } = useApi();
  const [datasources, setDatasources] = useState<Datasource[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<DatasourceType | "all">("all");
  const [includePrivate, setIncludePrivate] = useState(true);
  
  // 削除ダイアログの状態
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);
  
  // 接続テストの状態
  const [testingId, setTestingId] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, { status: 'success' | 'error'; message?: string }>>({});

  // 選択状態の管理
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  
  // 一括削除ダイアログの状態
  const [bulkDeleteDialogOpen, setBulkDeleteDialogOpen] = useState(false);
  const [isBulkDeleting, setIsBulkDeleting] = useState(false);

  const fetchDatasources = useCallback(async () => {
    if (!isReady || !api) return;

    setLoading(true);
    setError(null);
    try {
      const params: { type?: DatasourceType; include_private?: boolean } = {};
      if (filterType !== "all") {
        params.type = filterType;
      }
      params.include_private = includePrivate;
      
      const response = await api.listDatasources(params);
      if (response && response.datasources) {
        setDatasources(response.datasources);
      } else {
        setDatasources([]);
      }
      
      // 選択状態をクリア
      setSelectedIds(new Set());
    } catch (err) {
      setError(err instanceof Error ? err.message : t("error_fetch"));
      setDatasources([]);
    } finally {
      setLoading(false);
    }
  }, [api, isReady, filterType, includePrivate, t]);

  useEffect(() => {
    fetchDatasources();
  }, [fetchDatasources]);

  const handleDelete = async () => {
    if (!deletingId || !api) return;

    setDeleteLoading(true);
    try {
      await api.deleteDatasource(deletingId);
      await fetchDatasources();
      setDeleteDialogOpen(false);
      setDeletingId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("error_delete"));
    } finally {
      setDeleteLoading(false);
    }
  };

  const handleTestConnection = async (id: string) => {
    if (!api) return;

    setTestingId(id);
    try {
      const result = await api.testDatasource(id);
      setTestResults(prev => ({
        ...prev,
        [id]: { status: result.status, message: result.message }
      }));
    } catch (err) {
      setTestResults(prev => ({
        ...prev,
        [id]: { status: 'error', message: err instanceof Error ? err.message : t("test_error") }
      }));
    } finally {
      setTestingId(null);
    }
  };

  const openDeleteDialog = (id: string) => {
    setDeletingId(id);
    setDeleteDialogOpen(true);
  };

  const getTypeIcon = (type: DatasourceType) => {
    switch (type) {
      case "pmtiles":
        return <FileJson className="h-4 w-4" />;
      case "cog":
        return <ImageIcon className="h-4 w-4" />;
      default:
        return <Database className="h-4 w-4" />;
    }
  };

  const getTypeBadgeVariant = (type: DatasourceType) => {
    switch (type) {
      case "pmtiles":
        return "default";
      case "cog":
        return "secondary";
      default:
        return "outline";
    }
  };

  const getStorageProviderLabel = (provider: string) => {
    switch (provider) {
      case "s3":
        return t("storage_provider_s3");
      case "http":
        return t("storage_provider_http");
      // 旧 'supabase' 値は Issue #72 で廃止済み (PR #88)。既存 DB レコードに残っていた場合の表示用 fallback として残置。
      case "supabase":
        return t("storage_provider_supabase");
      default:
        return provider;
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString(dateLocale, {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const truncateUrl = (url: string, maxLength: number = 50) => {
    if (url.length <= maxLength) return url;
    return url.substring(0, maxLength) + "...";
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
    if (selectedIds.size === datasources.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(datasources.map(ds => ds.id)));
    }
  };

  // 一括削除の実行
  const handleBulkDelete = async () => {
    if (selectedIds.size === 0 || !api) return;

    setIsBulkDeleting(true);
    setError(null);
    
    try {
      // 並列で削除を実行
      const deletePromises = Array.from(selectedIds).map(id => 
        api.deleteDatasource(id).catch(err => ({ id, error: err }))
      );
      
      const results = await Promise.all(deletePromises);
      
      // エラーがあったものをチェック
      const errors = results.filter(r => r && typeof r === 'object' && 'error' in r);
      
      if (errors.length > 0) {
        setError(t("error_bulk_delete", { count: errors.length }));
      }
      
      // データを再取得
      await fetchDatasources();
      setBulkDeleteDialogOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("error_delete"));
    } finally {
      setIsBulkDeleting(false);
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
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={fetchDatasources} disabled={loading}>
              <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              {t("refresh")}
            </Button>
            <Button asChild>
              <Link href="/datasources/new">
                <Plus className="mr-2 h-4 w-4" />
                {t("register")}
              </Link>
            </Button>
          </div>
        </div>

        {/* フィルター */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">{t("filter_title")}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap items-center gap-4">
              <div className="flex items-center gap-2" data-testid="datasource-filter-type">
                <span className="text-sm text-muted-foreground">{t("filter_type_label")}</span>
                <div className="flex gap-1">
                  <Button
                    variant={filterType === "all" ? "default" : "outline"}
                    size="sm"
                    onClick={() => setFilterType("all")}
                    data-testid="datasource-filter-type-all"
                  >
                    {t("filter_type_all")}
                  </Button>
                  <Button
                    variant={filterType === "pmtiles" ? "default" : "outline"}
                    size="sm"
                    onClick={() => setFilterType("pmtiles")}
                    data-testid="datasource-filter-type-pmtiles"
                  >
                    <FileJson className="mr-1 h-3 w-3" />
                    PMTiles
                  </Button>
                  <Button
                    variant={filterType === "cog" ? "default" : "outline"}
                    size="sm"
                    onClick={() => setFilterType("cog")}
                    data-testid="datasource-filter-type-cog"
                  >
                    <ImageIcon className="mr-1 h-3 w-3" />
                    COG
                  </Button>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <label className="flex items-center gap-2 text-sm cursor-pointer">
                  <input
                    type="checkbox"
                    checked={includePrivate}
                    onChange={(e) => setIncludePrivate(e.target.checked)}
                    className="rounded border-gray-300"
                    data-testid="datasource-include-private-toggle"
                  />
                  {t("filter_include_private")}
                </label>
              </div>
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
                    variant="destructive"
                    size="sm"
                    onClick={() => setBulkDeleteDialogOpen(true)}
                    data-testid="datasource-bulk-delete"
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    {t("bulk_delete")}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* データソース一覧 */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>{t("section_title")}</CardTitle>
                <CardDescription>
                  {loading
                    ? t("loading")
                    : t("count", { count: datasources.length })}
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : datasources.length === 0 ? (
              <div className="text-center py-8">
                <Database className="mx-auto h-12 w-12 text-muted-foreground" />
                <h3 className="mt-4 text-lg font-semibold">
                  {t("empty_title")}
                </h3>
                <p className="mt-2 text-muted-foreground">
                  {t("empty_description")}
                </p>
                <Button asChild className="mt-4">
                  <Link href="/datasources/new" data-testid="datasource-empty-register-button">
                    <Plus className="mr-2 h-4 w-4" />
                    {t("empty_register")}
                  </Link>
                </Button>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-12">
                        <input
                          type="checkbox"
                          checked={selectedIds.size === datasources.length && datasources.length > 0}
                          onChange={toggleAllSelection}
                          className="h-4 w-4 rounded border-gray-300"
                          data-testid="datasource-select-all"
                        />
                      </TableHead>
                      <TableHead>{t("column_type")}</TableHead>
                      <TableHead>{t("column_tileset")}</TableHead>
                      <TableHead>{t("column_url")}</TableHead>
                      <TableHead>{t("column_storage")}</TableHead>
                      <TableHead>{t("column_visibility")}</TableHead>
                      <TableHead>{t("column_status")}</TableHead>
                      <TableHead>{t("column_created")}</TableHead>
                      <TableHead className="text-right">{t("column_actions")}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {datasources.map((ds) => (
                      <TableRow
                        key={ds.id}
                        className={selectedIds.has(ds.id) ? "bg-muted/50" : ""}
                        data-testid="datasource-list-row"
                      >
                        <TableCell>
                          <input
                            type="checkbox"
                            checked={selectedIds.has(ds.id)}
                            onChange={() => toggleSelection(ds.id)}
                            className="h-4 w-4 rounded border-gray-300"
                          />
                        </TableCell>
                        <TableCell>
                          <Badge variant={getTypeBadgeVariant(ds.type)}>
                            {getTypeIcon(ds.type)}
                            <span className="ml-1 uppercase">{ds.type}</span>
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Link
                            href={`/tilesets/${ds.tileset_id}`}
                            className="text-primary hover:underline font-medium"
                          >
                            {ds.tileset_name}
                          </Link>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <span
                              className="text-sm text-muted-foreground max-w-xs truncate"
                              title={ds.url}
                            >
                              {truncateUrl(ds.url)}
                            </span>
                            {isOpenableUrl(ds.url) && (
                              <a
                                href={ds.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-muted-foreground hover:text-foreground"
                              >
                                <ExternalLink className="h-3 w-3" />
                              </a>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">
                            {getStorageProviderLabel(ds.storage_provider)}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant={ds.is_public ? "default" : "secondary"}>
                            {ds.is_public ? t("visibility_public") : t("visibility_private")}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {testResults[ds.id] ? (
                            testResults[ds.id].status === 'success' ? (
                              <div className="flex items-center gap-1 text-green-600">
                                <CheckCircle2 className="h-4 w-4" />
                                <span className="text-xs">OK</span>
                              </div>
                            ) : (
                              <div className="flex items-center gap-1 text-red-600" title={testResults[ds.id].message}>
                                <XCircle className="h-4 w-4" />
                                <span className="text-xs">{t("status_error")}</span>
                              </div>
                            )
                          ) : (
                            <span className="text-xs text-muted-foreground">{t("status_untested")}</span>
                          )}
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {formatDate(ds.created_at)}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleTestConnection(ds.id)}
                              disabled={testingId === ds.id}
                              title={t("test_connection_title")}
                            >
                              {testingId === ds.id ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : (
                                <Play className="h-4 w-4" />
                              )}
                            </Button>
                            <Button variant="ghost" size="sm" asChild>
                              <Link href={`/datasources/${ds.id}`}>
                                <Eye className="h-4 w-4" />
                              </Link>
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => openDeleteDialog(ds.id)}
                              className="text-destructive hover:text-destructive"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* サマリーカード */}
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">PMTiles</CardTitle>
              <FileJson className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {datasources.filter((ds) => ds.type === "pmtiles").length}
              </div>
              <p className="text-xs text-muted-foreground">
                {t("summary_pmtiles_desc")}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">COG</CardTitle>
              <ImageIcon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {datasources.filter((ds) => ds.type === "cog").length}
              </div>
              <p className="text-xs text-muted-foreground">
                {t("summary_cog_desc")}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{t("summary_public_title")}</CardTitle>
              <Map className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {datasources.filter((ds) => ds.is_public).length}
              </div>
              <p className="text-xs text-muted-foreground">
                {t("summary_public_desc")}
              </p>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* 単一削除確認ダイアログ */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("delete_title")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("delete_description")}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteLoading}>{t("cancel")}</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={deleteLoading}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {t("deleting")}
                </>
              ) : (
                t("delete_confirm")
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* 一括削除確認ダイアログ */}
      <AlertDialog open={bulkDeleteDialogOpen} onOpenChange={setBulkDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("bulk_delete_title")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("bulk_delete_description", { count: selectedIds.size })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isBulkDeleting}>{t("cancel")}</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleBulkDelete}
              disabled={isBulkDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              data-testid="datasource-bulk-delete-confirm"
            >
              {isBulkDeleting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {t("deleting")}
                </>
              ) : (
                <>
                  <Trash2 className="mr-2 h-4 w-4" />
                  {t("bulk_delete_confirm", { count: selectedIds.size })}
                </>
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </AdminLayout>
  );
}
