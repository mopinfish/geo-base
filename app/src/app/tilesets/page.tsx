"use client";

import { useEffect, useState } from "react";
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
import { api, type Tileset } from "@/lib/api";
import { 
  Plus, 
  RefreshCw, 
  Search, 
  Layers,
  Eye,
  Pencil,
} from "lucide-react";

export default function TilesetsPage() {
  const [tilesets, setTilesets] = useState<Tileset[]>([]);
  const [filteredTilesets, setFilteredTilesets] = useState<Tileset[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [publicFilter, setPublicFilter] = useState<string>("all");

  const fetchTilesets = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.listTilesets();
      // 配列であることを確認
      const tilesetsArray = Array.isArray(data) ? data : [];
      setTilesets(tilesetsArray);
      setFilteredTilesets(tilesetsArray);
    } catch (err) {
      setError(err instanceof Error ? err.message : "タイルセットの取得に失敗しました");
      setTilesets([]);
      setFilteredTilesets([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchTilesets();
  }, []);

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

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* ヘッダー */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">タイルセット</h1>
            <p className="text-muted-foreground">
              タイルセットの一覧と管理
            </p>
          </div>
          <div className="flex gap-2">
            <Button onClick={fetchTilesets} variant="outline" size="sm">
              <RefreshCw className={`mr-2 h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
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
            {isLoading ? (
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
                    <TableHead>名前</TableHead>
                    <TableHead>タイプ</TableHead>
                    <TableHead>フォーマット</TableHead>
                    <TableHead>ソース</TableHead>
                    <TableHead>公開</TableHead>
                    <TableHead>更新日</TableHead>
                    <TableHead className="text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredTilesets.map((tileset) => (
                    <TableRow key={tileset.id}>
                      <TableCell>
                        <div>
                          <div className="font-medium">{tileset.name}</div>
                          {tileset.description && (
                            <div className="text-xs text-muted-foreground">
                              {tileset.description.slice(0, 50)}
                              {tileset.description.length > 50 && "..."}
                            </div>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{tileset.type}</Badge>
                      </TableCell>
                      <TableCell>
                        <code className="text-xs">{tileset.format}</code>
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary">
                          {tileset.source_type || "-"}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant={tileset.is_public ? "default" : "outline"}>
                          {tileset.is_public ? "公開" : "非公開"}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {formatDate(tileset.updated_at)}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Link href={`/tilesets/${tileset.id}`}>
                            <Button variant="ghost" size="icon">
                              <Eye className="h-4 w-4" />
                            </Button>
                          </Link>
                          <Link href={`/tilesets/${tileset.id}/edit`}>
                            <Button variant="ghost" size="icon">
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
    </AdminLayout>
  );
}
