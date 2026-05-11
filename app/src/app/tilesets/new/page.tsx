"use client";

import { Plus } from "lucide-react";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { AdminLayout } from "@/components/layout";
import { TilesetForm } from "@/components/tilesets/tileset-form";
import { useApi } from "@/hooks/use-api";
import type { TilesetCreate, TilesetUpdate } from "@/lib/api";

export default function NewTilesetPage() {
  const router = useRouter();
  const { api, isReady } = useApi();
  const t = useTranslations("tilesets.new");

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (data: TilesetCreate | TilesetUpdate) => {
    if (!isReady) {
      setError(t("error_api_not_ready"));
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const tileset = await api.createTileset(data as TilesetCreate);
      router.push(`/tilesets/${tileset.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("error_create"));
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
            <h1 className="text-3xl font-bold">{t("title")}</h1>
          </div>
          <p className="mt-1 text-muted-foreground">{t("subtitle")}</p>
        </div>

        {/* フォーム */}
        <div className="max-w-2xl">
          <TilesetForm
            mode="create"
            onSubmit={handleSubmit}
            isSubmitting={isSubmitting || !isReady}
            error={error}
          />
        </div>
      </div>
    </AdminLayout>
  );
}
