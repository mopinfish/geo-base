"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { AdminLayout } from "@/components/layout";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useApi } from "@/hooks/use-api";
import { FeatureForm } from "@/components/features";
import type { Tileset, FeatureCreate, FeatureUpdate } from "@/lib/api";
import { ArrowLeft, Plus, RefreshCw } from "lucide-react";

export default function NewFeaturePage() {
  const router = useRouter();
  const { api, isReady } = useApi();
  const [tilesets, setTilesets] = useState<Tileset[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchTilesets = async () => {
    if (!isReady) return;
    
    setIsLoading(true);
    try {
      const result = await api.listTilesets();
      if (Array.isArray(result)) {
        setTilesets(result);
      } else if (result && typeof result === 'object' && 'tilesets' in result) {
        setTilesets((result as { tilesets: Tileset[] }).tilesets);
      } else {
        setTilesets([]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "タイルセットの取得に失敗しました");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchTilesets();
  }, [isReady]);

  const handleSubmit = async (data: FeatureCreate | FeatureUpdate) => {
    setIsSubmitting(true);
    setError(null);
    try {
      const feature = await api.createFeature(data as FeatureCreate);
      router.push(`/features/${feature.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "フィーチャーの作成に失敗しました");
      setIsSubmitting(false);
    }
  };

  const handleCancel = () => {
    router.push("/features");
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

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* ヘッダー */}
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" asChild>
            <Link href="/features">
              <ArrowLeft className="mr-2 h-4 w-4" />
              戻る
            </Link>
          </Button>
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Plus className="h-6 w-6" />
              フィーチャー新規作成
            </h1>
            <p className="text-sm text-muted-foreground">
              新しい地物データを作成します
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

        {/* タイルセットがない場合 */}
        {tilesets.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <p className="mb-4 text-muted-foreground">
                フィーチャーを作成するには、まずタイルセットが必要です
              </p>
              <Button asChild>
                <Link href="/tilesets/new">
                  <Plus className="mr-2 h-4 w-4" />
                  タイルセットを作成
                </Link>
              </Button>
            </CardContent>
          </Card>
        ) : (
          <FeatureForm
            tilesets={tilesets}
            onSubmit={handleSubmit}
            onCancel={handleCancel}
            isSubmitting={isSubmitting}
          />
        )}
      </div>
    </AdminLayout>
  );
}
