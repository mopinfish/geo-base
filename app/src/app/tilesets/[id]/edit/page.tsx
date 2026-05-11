"use client";

import { ArrowLeft, Pencil, RefreshCw } from "lucide-react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, use } from "react";

import { AdminLayout } from "@/components/layout";
import { TilesetForm } from "@/components/tilesets/tileset-form";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useApi } from "@/hooks/use-api";
import type { Tileset, TilesetCreate, TilesetUpdate } from "@/lib/api";

interface EditTilesetPageProps {
  params: Promise<{ id: string }>;
}

export default function EditTilesetPage({ params }: EditTilesetPageProps) {
  const { id } = use(params);
  const router = useRouter();
  const { api, isReady } = useApi();
  const t = useTranslations("tilesets.edit");

  const [tileset, setTileset] = useState<Tileset | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const fetchTileset = async () => {
    if (!isReady) return;

    setIsLoading(true);
    setFetchError(null);
    try {
      const data = await api.getTileset(id);
      setTileset(data);
    } catch (err) {
      setFetchError(err instanceof Error ? err.message : t("error_fetch"));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isReady) {
      fetchTileset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, isReady]);

  const handleSubmit = async (data: TilesetCreate | TilesetUpdate) => {
    if (!isReady) {
      setError(t("error_api_not_ready"));
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      await api.updateTileset(id, data as TilesetUpdate);
      router.push(`/tilesets/${id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("error_update"));
      setIsSubmitting(false);
    }
  };

  if (!isReady || isLoading) {
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
              {t("back")}
            </Button>
          </Link>
          <Card className="border-destructive">
            <CardContent className="pt-6">
              <p className="text-destructive">{fetchError || t("not_found")}</p>
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
            <h1 className="text-3xl font-bold">{t("title")}</h1>
          </div>
          <p className="mt-1 text-muted-foreground">
            {t("subtitle_template", { name: tileset.name })}
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
