"use client";

import { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { AdminLayout } from "@/components/layout";
import { TilesetForm } from "@/components/tilesets/tileset-form";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useApi } from "@/hooks/use-api";
import type { Tileset, TilesetCreate, TilesetUpdate } from "@/lib/api";
import { Pencil, RefreshCw, ArrowLeft } from "lucide-react";

interface EditTilesetPageProps {
  params: Promise<{ id: string }>;
}

export default function EditTilesetPage({ params }: EditTilesetPageProps) {
  const { id } = use(params);
  const router = useRouter();
  const api = useApi();
  
  const [tileset, setTileset] = useState<Tileset | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const fetchTileset = async () => {
    setIsLoading(true);
    setFetchError(null);
    try {
      const data = await api.getTileset(id);
      setTileset(data);
    } catch (err) {
      setFetchError(err instanceof Error ? err.message : "タイルセットの取得に失敗しました");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchTileset();
  }, [id]);

  const handleSubmit = async (data: TilesetCreate | TilesetUpdate) => {
    setIsSubmitting(true);
    setError(null);
    
    try {
      // 編集時は TilesetUpdate として扱う
      await api.updateTileset(id, data as TilesetUpdate);
      router.push(`/tilesets/${id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "タイルセットの更新に失敗しました");
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <AdminLayout>
        <div className="flex h-64 items-center justify-center">
          <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </AdminLayout>
    );
  }

  if (fetchError || !tileset) {
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
              <p className="text-destructive">{fetchError || "タイルセットが見つかりません"}</p>
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
        <div>
          <div className="flex items-center gap-2">
            <Pencil className="h-8 w-8" />
            <h1 className="text-3xl font-bold">タイルセット編集</h1>
          </div>
          <p className="mt-1 text-muted-foreground">
            <strong>{tileset.name}</strong> を編集します
          </p>
        </div>

        {/* フォーム */}
        <div className="max-w-2xl">
          <TilesetForm
            mode="edit"
            initialData={tileset}
            onSubmit={handleSubmit}
            isSubmitting={isSubmitting}
            error={error}
          />
        </div>
      </div>
    </AdminLayout>
  );
}
