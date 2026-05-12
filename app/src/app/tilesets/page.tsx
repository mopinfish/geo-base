"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";

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
import type { Tileset } from "@/lib/api";
import {
  Plus,
  RefreshCw,
  Search,
  Layers,
  Eye,
  Pencil,
  Globe,
  Lock,
  Trash2,
  Loader2,
  ChevronDown,
} from "lucide-react";

export default function TilesetsPage() {
  const { api, isReady } = useApi();
  const t = useTranslations("tilesets.list");
  const locale = useLocale();
  const dateLocale = locale === "ja" ? "ja-JP" : "en-US";

  const [tilesets, setTilesets] = useState<Tileset[]>([]);
  const [filteredTilesets, setFilteredTilesets] = useState<Tileset[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [publicFilter, setPublicFilter] = useState<string>("all");

  // 選択状態の管理
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // 一括削除ダイアログの状態
  const [bulkDeleteDialogOpen, setBulkDeleteDialogOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const fetchTilesets = useCallback(async () => {
    if (!isReady) return;

    setIsLoading(true);
    setError(null);
    try {
      // ログイン済みユーザーが所有する非公開タイルセットも一覧に出すため
      // include_private=true を明示する（issue #102）。`/api/tilesets` の既定は
      // 公開のみなので、これが無いと自分の非公開タイルセットが UI から消える。
      // 公開/非公開の絞り込みは下流の `publicFilter` (client-side) で行う。
      const data = await api.listTilesets({ include_private: true });

      // APIレスポンスの形式に対応
      // - 配列の場合: data そのもの
      // - オブジェクトの場合: data.tilesets
      let tilesetsArray: Tileset[] = [];
      if (Array.isArray(data)) {
        tilesetsArray = data;
      } else if (data && typeof data === "object" && "tilesets" in data) {
        tilesetsArray = (data as { tilesets: Tileset[] }).tilesets;
      }

      setTilesets(tilesetsArray);
      setFilteredTilesets(tilesetsArray);

      // 選択状態をクリア
      setSelectedIds(new Set());
    } catch (err) {
      console.error("Fetch error:", err);
      setError(err instanceof Error ? err.message : t("error_fetch"));
      setTilesets([]);
      setFilteredTilesets([]);
    } finally {
      setIsLoading(false);
    }
  }, [api, isReady, t]);

  // isReadyになったらfetch
  useEffect(() => {
    if (isReady) {
      fetchTilesets();
    }
  }, [isReady, fetchTilesets]);

  // フィルタリング
  useEffect(() => {
    // 安全にフィルタリング
    const safeTilesets = Array.isArray(tilesets) ? tilesets : [];
    let filtered = safeTilesets;

    // 検索クエリでフィルタ
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (t) =>
          t.name.toLowerCase().includes(query) ||
          t.description?.toLowerCase().includes(query)
      );
    }

    // タイプでフィルタ
    if (typeFilter !== "all") {
      filtered = filtered.filter((t) => t.type === typeFilter);
    }

    // 公開状態でフィルタ
    if (publicFilter !== "all") {
      const isPublic = publicFilter === "public";
      filtered = filtered.filter((t) => t.is_public === isPublic);
    }

    setFilteredTilesets(filtered);
  }, [tilesets, searchQuery, typeFilter, publicFilter]);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString(dateLocale, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
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
    if (selectedIds.size === filteredTilesets.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(filteredTilesets.map((t) => t.id)));
    }
  };

  // 一括削除の実行
  const handleBulkDelete = async () => {
    if (selectedIds.size === 0) return;

    setIsDeleting(true);
    setError(null);

    try {
      // 並列で削除を実行
      const deletePromises = Array.from(selectedIds).map((id) =>
        api.deleteTileset(id).catch((err) => ({ id, error: err }))
      );

      const results = await Promise.all(deletePromises);

      // エラーがあったものをチェック
      const errors = results.filter(
        (r) => r && typeof r === "object" && "error" in r
      );

      if (errors.length > 0) {
        setError(t("bulk_delete_partial_error", { count: errors.length }));
      }

      // データを再取得
      await fetchTilesets();
      setBulkDeleteDialogOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("error_delete"));
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* ヘッダー */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">{t("title")}</h1>
            <p className="text-muted-foreground">{t("subtitle")}</p>
          </div>
          <div className="flex gap-2">
            <Button
              onClick={fetchTilesets}
              variant="outline"
              size="sm"
              disabled={!isReady}
            >
              <RefreshCw
                className={`mr-2 h-4 w-4 ${isLoading ? "animate-spin" : ""}`}
              />
              {t("refresh")}
            </Button>
            <Link href="/tilesets/new" data-testid="tileset-create-link">
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                {t("new")}
              </Button>
            </Link>
          </div>
        </div>

        {/* フィルター */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-col gap-4 md:flex-row md:items-center">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder={t("search_placeholder")}
                  className="pl-9"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  data-testid="tileset-search-input"
                />
              </div>
              {/* ネイティブ select を使用（Radix UI のポータル問題を回避） */}
              <div className="relative">
                <select
                  data-testid="tileset-filter-type"
                  aria-label={t("filter_type_label")}
                  value={typeFilter}
                  onChange={(e) => setTypeFilter(e.target.value)}
                  className="h-9 w-[150px] appearance-none rounded-md border border-input bg-transparent px-3 py-2 pr-8 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
                >
                  <option value="all">{t("filter_type_all")}</option>
                  <option value="vector">{t("filter_type_vector")}</option>
                  <option value="raster">{t("filter_type_raster")}</option>
                  <option value="pmtiles">{t("filter_type_pmtiles")}</option>
                </select>
                <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-4 w-4 -translate-y-1/2 opacity-50" />
              </div>
              <div className="relative">
                <select
                  data-testid="tileset-filter-public"
                  aria-label={t("filter_public_label")}
                  value={publicFilter}
                  onChange={(e) => setPublicFilter(e.target.value)}
                  className="h-9 w-[150px] appearance-none rounded-md border border-input bg-transparent px-3 py-2 pr-8 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
                >
                  <option value="all">{t("filter_public_all")}</option>
                  <option value="public">{t("filter_public_public")}</option>
                  <option value="private">{t("filter_public_private")}</option>
                </select>
                <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-4 w-4 -translate-y-1/2 opacity-50" />
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
                    data-testid="tileset-bulk-delete"
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    {t("bulk_delete")}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* タイルセット一覧 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Layers className="h-5 w-5" />
              {t("section_title")}
              <Badge variant="secondary" className="ml-2">
                {t("count_badge", { count: filteredTilesets.length })}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {!isReady || isLoading ? (
              <div className="flex h-32 items-center justify-center">
                <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : filteredTilesets.length === 0 ? (
              <div className="flex h-32 flex-col items-center justify-center text-muted-foreground">
                <Layers className="mb-2 h-8 w-8" />
                <p>{t("empty")}</p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-12">
                      <input
                        type="checkbox"
                        checked={
                          selectedIds.size === filteredTilesets.length &&
                          filteredTilesets.length > 0
                        }
                        onChange={toggleAllSelection}
                        className="h-4 w-4 rounded border-gray-300"
                        data-testid="tileset-select-all"
                      />
                    </TableHead>
                    <TableHead>{t("column_name")}</TableHead>
                    <TableHead>{t("column_type")}</TableHead>
                    <TableHead>{t("column_format")}</TableHead>
                    <TableHead>{t("column_public")}</TableHead>
                    <TableHead>{t("column_updated")}</TableHead>
                    <TableHead className="text-right">{t("column_actions")}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredTilesets.map((tileset) => (
                    <TableRow
                      key={tileset.id}
                      data-testid="tileset-list-row"
                      className={
                        selectedIds.has(tileset.id) ? "bg-muted/50" : ""
                      }
                    >
                      <TableCell>
                        <input
                          type="checkbox"
                          checked={selectedIds.has(tileset.id)}
                          onChange={() => toggleSelection(tileset.id)}
                          className="h-4 w-4 rounded border-gray-300"
                        />
                      </TableCell>
                      <TableCell>
                        <Link
                          href={`/tilesets/${tileset.id}`}
                          className="hover:underline"
                        >
                          <div>
                            <div className="font-medium">{tileset.name}</div>
                            {tileset.description && (
                              <div className="text-xs text-muted-foreground">
                                {tileset.description.slice(0, 50)}
                                {tileset.description.length > 50 && "..."}
                              </div>
                            )}
                          </div>
                        </Link>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{tileset.type}</Badge>
                      </TableCell>
                      <TableCell>
                        <code className="text-xs">{tileset.format}</code>
                      </TableCell>
                      <TableCell>
                        {tileset.is_public ? (
                          <Badge variant="default" className="gap-1">
                            <Globe className="h-3 w-3" />
                            {t("badge_public")}
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="gap-1">
                            <Lock className="h-3 w-3" />
                            {t("badge_private")}
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {formatDate(tileset.updated_at)}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Link href={`/tilesets/${tileset.id}`}>
                            <Button
                              variant="ghost"
                              size="icon"
                              title={t("action_view")}
                              aria-label={t("action_view")}
                            >
                              <Eye className="h-4 w-4" />
                            </Button>
                          </Link>
                          <Link href={`/tilesets/${tileset.id}/edit`}>
                            <Button
                              variant="ghost"
                              size="icon"
                              title={t("action_edit")}
                              aria-label={t("action_edit")}
                            >
                              <Pencil className="h-4 w-4" />
                            </Button>
                          </Link>
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
      <AlertDialog
        open={bulkDeleteDialogOpen}
        onOpenChange={setBulkDeleteDialogOpen}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("bulk_delete_title")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("bulk_delete_description", { count: selectedIds.size })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>
              {t("cancel")}
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleBulkDelete}
              disabled={isDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              data-testid="tileset-bulk-delete-confirm"
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
    </AdminLayout>
  );
}
