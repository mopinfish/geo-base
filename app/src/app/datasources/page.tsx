"use client";

import { useEffect, useState } from "react";
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
import type { Datasource, DatasourceType } from "@/lib/api";
import {
  Plus,
  RefreshCw,
  Database,
  Map,
  Trash2,
  ExternalLink,
  FileJson,
  Image,
  Eye,
  Loader2,
  CheckCircle2,
  XCircle,
  Play,
} from "lucide-react";

export default function DatasourcesPage() {
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
  const [testResults, setTestResults] = useState<Record<string, { status: 'ok' | 'error'; message?: string }>>({});

  // 選択状態の管理
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  
  // 一括削除ダイアログの状態
  const [bulkDeleteDialogOpen, setBulkDeleteDialogOpen] = useState(false);
  const [isBulkDeleting, setIsBulkDeleting] = useState(false);

  const fetchDatasources = async () => {
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
      setError(err instanceof Error ? err.message : "データソースの取得に失敗しました");
      setDatasources([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDatasources();
  }, [api, isReady, filterType, includePrivate]);

  const handleDelete = async () => {
    if (!deletingId || !api) return;

    setDeleteLoading(true);
    try {
      await api.deleteDatasource(deletingId);
      await fetchDatasources();
      setDeleteDialogOpen(false);
      setDeletingId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "削除に失敗しました");
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
        [id]: { status: 'error', message: err instanceof Error ? err.message : 'テストに失敗しました' }
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
        return <Image className="h-4 w-4" />;
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
      case "supabase":
        return "Supabase Storage";
      case "s3":
        return "AWS S3";
      case "http":
        return "HTTP";
      default:
        return provider;
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("ja-JP", {
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
        setError(`${errors.length}件の削除に失敗しました`);
      }
      
      // データを再取得
      await fetchDatasources();
      setBulkDeleteDialogOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "削除に失敗しました");
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
            <h1 className="text-3xl font-bold">データソース</h1>
            <p className="text-muted-foreground">
              PMTiles・COGファイルなどの外部データソース管理
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={fetchDatasources} disabled={loading}>
              <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              更新
            </Button>
            <Button asChild>
              <Link href="/datasources/new">
                <Plus className="mr-2 h-4 w-4" />
                新規登録
              </Link>
            </Button>
          </div>
        </div>

        {/* フィルター */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">フィルター</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap items-center gap-4">
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">タイプ:</span>
                <div className="flex gap-1">
                  <Button
                    variant={filterType === "all" ? "default" : "outline"}
                    size="sm"
                    onClick={() => setFilterType("all")}
                  >
                    すべて
                  </Button>
                  <Button
                    variant={filterType === "pmtiles" ? "default" : "outline"}
                    size="sm"
                    onClick={() => setFilterType("pmtiles")}
                  >
                    <FileJson className="mr-1 h-3 w-3" />
                    PMTiles
                  </Button>
                  <Button
                    variant={filterType === "cog" ? "default" : "outline"}
                    size="sm"
                    onClick={() => setFilterType("cog")}
                  >
                    <Image className="mr-1 h-3 w-3" />
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
                  />
                  プライベートを含む
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
                    variant="destructive"
                    size="sm"
                    onClick={() => setBulkDeleteDialogOpen(true)}
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    一括削除
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
                <CardTitle>データソース一覧</CardTitle>
                <CardDescription>
                  {loading
                    ? "読み込み中..."
                    : `${datasources.length}件のデータソース`}
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
                  データソースがありません
                </h3>
                <p className="mt-2 text-muted-foreground">
                  「新規登録」からデータソースを追加してください
                </p>
                <Button asChild className="mt-4">
                  <Link href="/datasources/new">
                    <Plus className="mr-2 h-4 w-4" />
                    新規登録
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
                        />
                      </TableHead>
                      <TableHead>タイプ</TableHead>
                      <TableHead>タイルセット</TableHead>
                      <TableHead>URL</TableHead>
                      <TableHead>ストレージ</TableHead>
                      <TableHead>公開設定</TableHead>
                      <TableHead>状態</TableHead>
                      <TableHead>作成日</TableHead>
                      <TableHead className="text-right">操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {datasources.map((ds) => (
                      <TableRow 
                        key={ds.id}
                        className={selectedIds.has(ds.id) ? "bg-muted/50" : ""}
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
                            <a
                              href={ds.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-muted-foreground hover:text-foreground"
                            >
                              <ExternalLink className="h-3 w-3" />
                            </a>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">
                            {getStorageProviderLabel(ds.storage_provider)}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant={ds.is_public ? "default" : "secondary"}>
                            {ds.is_public ? "公開" : "非公開"}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {testResults[ds.id] ? (
                            testResults[ds.id].status === 'ok' ? (
                              <div className="flex items-center gap-1 text-green-600">
                                <CheckCircle2 className="h-4 w-4" />
                                <span className="text-xs">OK</span>
                              </div>
                            ) : (
                              <div className="flex items-center gap-1 text-red-600" title={testResults[ds.id].message}>
                                <XCircle className="h-4 w-4" />
                                <span className="text-xs">エラー</span>
                              </div>
                            )
                          ) : (
                            <span className="text-xs text-muted-foreground">未テスト</span>
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
                              title="接続テスト"
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
                ベクタタイルアーカイブ
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">COG</CardTitle>
              <Image className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {datasources.filter((ds) => ds.type === "cog").length}
              </div>
              <p className="text-xs text-muted-foreground">
                Cloud Optimized GeoTIFF
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">公開</CardTitle>
              <Map className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {datasources.filter((ds) => ds.is_public).length}
              </div>
              <p className="text-xs text-muted-foreground">
                公開データソース数
              </p>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* 単一削除確認ダイアログ */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>データソースを削除しますか？</AlertDialogTitle>
            <AlertDialogDescription>
              この操作は取り消せません。データソースが削除されますが、タイルセットは削除されません。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteLoading}>キャンセル</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={deleteLoading}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  削除中...
                </>
              ) : (
                "削除する"
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* 一括削除確認ダイアログ */}
      <AlertDialog open={bulkDeleteDialogOpen} onOpenChange={setBulkDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>データソースを一括削除しますか？</AlertDialogTitle>
            <AlertDialogDescription>
              選択した {selectedIds.size} 件のデータソースを削除します。
              この操作は取り消せません。タイルセットは削除されません。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isBulkDeleting}>キャンセル</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleBulkDelete}
              disabled={isBulkDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isBulkDeleting ? (
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
    </AdminLayout>
  );
}
