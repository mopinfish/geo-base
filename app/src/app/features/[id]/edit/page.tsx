"use client";

import { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { AdminLayout } from "@/components/layout";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useApi } from "@/hooks/use-api";
import { FeatureForm } from "@/components/features";
import type { Feature, Tileset, FeatureCreate, FeatureUpdate } from "@/lib/api";
import { ArrowLeft, Pencil, RefreshCw } from "lucide-react";

interface EditFeaturePageProps {
  params: Promise<{ id: string }>;
}

export default function EditFeaturePage({ params }: EditFeaturePageProps) {
  const { id } = use(params);
  const router = useRouter();
  const { api, isReady } = useApi();
  const [feature, setFeature] = useState<Feature | null>(null);
  const [tilesets, setTilesets] = useState<Tileset[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    if (!isReady) return;
    
    setIsLoading(true);
    setError(null);
    try {
      const [featureData, tilesetsResult] = await Promise.all([
        api.getFeature(id),
        api.listTilesets(),
      ]);
      
      setFeature(featureData);
      
      if (Array.isArray(tilesetsResult)) {
        setTilesets(tilesetsResult);
      } else if (tilesetsResult && typeof tilesetsResult === 'object' && 'tilesets' in tilesetsResult) {
        setTilesets((tilesetsResult as { tilesets: Tileset[] }).tilesets);
      } else {
        setTilesets([]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "データの取得に失敗しました");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [id, isReady]);

  const handleSubmit = async (data: FeatureCreate | FeatureUpdate) => {
    setIsSubmitting(true);
    setError(null);
    try {
      await api.updateFeature(id, data as FeatureUpdate);
      router.push(`/features/${id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "フィーチャーの更新に失敗しました");
      setIsSubmitting(false);
    }
  };

  const handleCancel = () => {
    router.push(`/features/${id}`);
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

  if (!feature) {
    return (
      <AdminLayout>
        <div className="space-y-6">
          <Button variant="ghost" asChild>
            <Link href="/features">
              <ArrowLeft className="mr-2 h-4 w-4" />
              フィーチャー一覧に戻る
            </Link>
          </Button>
          <Card>
            <CardContent className="flex h-32 items-center justify-center pt-6">
              <p className="text-muted-foreground">フィーチャーが見つかりません</p>
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
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" asChild>
            <Link href={`/features/${id}`}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              戻る
            </Link>
          </Button>
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Pencil className="h-6 w-6" />
              フィーチャー編集
            </h1>
            <p className="text-sm text-muted-foreground">
              ID: {feature.id}
            </p>
          </div>
        </div>

        {/* エラー表示 */}
        {error && (
          <Card className="border-destructive">
            <CardContent className="pt-6">
              <p className="text-destructive">{error}</p>
            </CardContent>
          </Card>
        )}

        {/* フォーム */}
        <FeatureForm
          featureId={id}
          initialData={{
            tileset_id: feature.tileset_id,
            layer_name: feature.layer_name,
            properties: feature.properties,
            geometry: feature.geometry,
          }}
          tilesets={tilesets}
          onSubmit={handleSubmit}
          onCancel={handleCancel}
          isSubmitting={isSubmitting}
        />
      </div>
    </AdminLayout>
  );
}
