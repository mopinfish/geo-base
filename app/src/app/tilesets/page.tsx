"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { AdminLayout } from "@/components/layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
} from "lucide-react";

export default function TilesetsPage() {
  const { api, isReady } = useApi();

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
    if (!isReady) {
      console.log("API not ready yet, skipping fetch");
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      console.log("Fetching tilesets...");
      const data = await api.listTilesets();
      console.log("API Response:", data);

      // APIレスポンスの形式に対応
      // - 配列の場合: data そのもの
      // - オブジェクトの場合: data.tilesets
      let tilesetsArray: Tileset[] = [];
      if (Array.isArray(data)) {
        tilesetsArray = data;
      } else if (data && typeof data === "object" && "tilesets" in data) {
        tilesetsArray = (data as { tilesets: Tileset[] }).tilesets;
      }
      console.log("Tilesets array:", tilesetsArray);

      setTilesets(tilesetsArray);
      setFilteredTilesets(tilesetsArray);

      // 選択状態をクリア
      setSelectedIds(new Set());
    } catch (err) {
      console.error("Fetch error:", err);
      setError(
        err instanceof Error ? err.message : "タイルセットの取得に失敗しました"
      );
      setTilesets([]);
      setFilteredTilesets([]);
    } finally {
      setIsLoading(false);
    }
  }, [api, isReady]);

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
    return new Date(dateString).toLocaleDateString("ja-JP", {
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
        setError(`${errors.length}件の削除に失敗しました`);
      }

      // データを再取得
      await fetchTilesets();
      setBulkDeleteDialogOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "削除に失敗しました");
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
            <h1 className="text-3xl font-bold">タイルセット</h1>
            <p className="text-muted-foreground">タイルセットの一覧と管理</p>
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
              更新
            </Button>
            <Link href="/tilesets/new">
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                新規作成
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
                  placeholder="タイルセットを検索..."
                  className="pl-9"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
              <Select value={typeFilter} onValueChange={setTypeFilter}>
                <SelectTrigger className="w-[150px]">
                  <SelectValue placeholder="タイプ" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">すべてのタイプ</SelectItem>
                  <SelectItem value="vector">ベクタ</SelectItem>
                  <SelectItem value="raster">ラスタ</SelectItem>
                  <SelectItem value="pmtiles">PMTiles</SelectItem>
                </SelectContent>
              </Select>
              <Select value={publicFilter} onValueChange={setPublicFilter}>
                <SelectTrigger className="w-[150px]">
                  <SelectValue placeholder="公開状態" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">すべて</SelectItem>
                  <SelectItem value="public">公開</SelectItem>
                  <SelectItem value="private">非公開</SelectItem>
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

        {/* タイルセット一覧 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Layers className="h-5 w-5" />
              タイルセット一覧
              <Badge variant="secondary" className="ml-2">
                {filteredTilesets.length} 件
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
                <p>タイルセットがありません</p>
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
                      />
                    </TableHead>
                    <TableHead>名前</TableHead>
                    <TableHead>タイプ</TableHead>
                    <TableHead>フォーマット</TableHead>
                    <TableHead>公開</TableHead>
                    <TableHead>更新日</TableHead>
                    <TableHead className="text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredTilesets.map((tileset) => (
                    <TableRow
                      key={tileset.id}
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
                            公開
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="gap-1">
                            <Lock className="h-3 w-3" />
                            非公開
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {formatDate(tileset.updated_at)}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Link href={`/tilesets/${tileset.id}`}>
                            <Button variant="ghost" size="icon" title="詳細">
                              <Eye className="h-4 w-4" />
                            </Button>
                          </Link>
                          <Link href={`/tilesets/${tileset.id}/edit`}>
                            <Button variant="ghost" size="icon" title="編集">
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
            <AlertDialogTitle>
              タイルセットを一括削除しますか？
            </AlertDialogTitle>
            <AlertDialogDescription>
              選択した {selectedIds.size} 件のタイルセットを削除します。
              タイルセットに含まれるフィーチャーやデータソースも削除されます。
              この操作は取り消せません。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>
              キャンセル
            </AlertDialogCancel>
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
    </AdminLayout>
  );
}
