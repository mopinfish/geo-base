"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { AdminLayout } from "@/components/layout";
import { TilesetForm } from "@/components/tilesets/tileset-form";
import { useApi } from "@/hooks/use-api";
import type { TilesetCreate, TilesetUpdate } from "@/lib/api";
import { Plus } from "lucide-react";

export default function NewTilesetPage() {
  const router = useRouter();
  const api = useApi();
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (data: TilesetCreate | TilesetUpdate) => {
    setIsSubmitting(true);
    setError(null);
    
    try {
      // 新規作成時は TilesetCreate として扱う
      const tileset = await api.createTileset(data as TilesetCreate);
      router.push(`/tilesets/${tileset.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "タイルセットの作成に失敗しました");
      setIsSubmitting(false);
    }
  };

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* ヘッダー */}
        <div>
          <div className="flex items-center gap-2">
            <Plus className="h-8 w-8" />
            <h1 className="text-3xl font-bold">新規タイルセット作成</h1>
          </div>
          <p className="mt-1 text-muted-foreground">
            新しいタイルセットを作成します
          </p>
        </div>

        {/* フォーム */}
        <div className="max-w-2xl">
          <TilesetForm
            mode="create"
            onSubmit={handleSubmit}
            isSubmitting={isSubmitting}
            error={error}
          />
        </div>
      </div>
    </AdminLayout>
  );
}
