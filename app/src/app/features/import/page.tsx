"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { AdminLayout } from "@/components/layout";
import { 
  GeoJSONDropzone, 
  GeoJSONPreview,
  type ParsedGeoJSON,
  type GeoJSONFeature,
} from "@/components/features";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { useApi } from "@/hooks/use-api";
import type { Tileset } from "@/lib/api";
import { 
  Upload, 
  ArrowLeft, 
  AlertCircle, 
  Check, 
  Loader2,
  FileJson,
  MapPin,
} from "lucide-react";
import Link from "next/link";

type ImportStatus = "idle" | "importing" | "success" | "error";

interface ImportProgress {
  total: number;
  completed: number;
  failed: number;
  errors: string[];
}

export default function GeoJSONImportPage() {
  const router = useRouter();
  const { api, isReady } = useApi();
  
  // 状態管理
  const [tilesets, setTilesets] = useState<Tileset[]>([]);
  const [selectedTilesetId, setSelectedTilesetId] = useState<string>("");
  const [parsedGeoJSON, setParsedGeoJSON] = useState<ParsedGeoJSON | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<ImportStatus>("idle");
  const [progress, setProgress] = useState<ImportProgress>({
    total: 0,
    completed: 0,
    failed: 0,
    errors: [],
  });

  // タイルセット一覧の取得（vectorタイプのみ）
  useEffect(() => {
    if (!isReady) return;

    const fetchTilesets = async () => {
      try {
        const response = await api.listTilesets();
        // APIレスポンス形式に対応
        const data = Array.isArray(response) ? response : response?.tilesets || [];
        // vectorタイプのみフィルタリング
        const vectorTilesets = data.filter((t: Tileset) => t.type === "vector");
        setTilesets(vectorTilesets);
        
        // 最初のタイルセットを選択
        if (vectorTilesets.length > 0 && !selectedTilesetId) {
          setSelectedTilesetId(vectorTilesets[0].id);
        }
      } catch (err) {
        console.error("Failed to fetch tilesets:", err);
      }
    };

    fetchTilesets();
  }, [isReady, api]);

  // ファイル読み込み成功時
  const handleFileLoaded = (result: ParsedGeoJSON) => {
    setParsedGeoJSON(result);
    setError(null);
    setStatus("idle");
    setProgress({ total: 0, completed: 0, failed: 0, errors: [] });
  };

  // ファイル読み込みエラー時
  const handleFileError = (errorMessage: string) => {
    setError(errorMessage);
    setParsedGeoJSON(null);
  };

  // インポート実行
  const handleImport = async () => {
    if (!parsedGeoJSON || !selectedTilesetId) return;

    setStatus("importing");
    setError(null);
    
    const features = parsedGeoJSON.data.features;
    const total = features.length;
    let completed = 0;
    let failed = 0;
    const errors: string[] = [];

    setProgress({ total, completed, failed, errors });

    // バッチサイズ（同時に送信する数）
    const batchSize = 5;

    for (let i = 0; i < features.length; i += batchSize) {
      const batch = features.slice(i, i + batchSize);
      
      const results = await Promise.allSettled(
        batch.map((feature) => createFeature(feature))
      );

      results.forEach((result, index) => {
        if (result.status === "fulfilled") {
          completed++;
        } else {
          failed++;
          const featureIndex = i + index;
          errors.push(`フィーチャー #${featureIndex + 1}: ${result.reason}`);
        }
      });

      setProgress({ total, completed, failed, errors: [...errors] });
    }

    if (failed === 0) {
      setStatus("success");
    } else if (completed === 0) {
      setStatus("error");
      setError(`すべてのフィーチャーのインポートに失敗しました`);
    } else {
      setStatus("success");
    }
  };

  // 単一フィーチャーの作成
  const createFeature = async (feature: GeoJSONFeature): Promise<void> => {
    try {
      const response = await api.createFeature({
        tileset_id: selectedTilesetId,
        geometry: feature.geometry,
        properties: feature.properties || {},
        layer_name: "imported",
      });

      if (!response) {
        throw new Error("作成に失敗しました");
      }
    } catch (err) {
      throw new Error(err instanceof Error ? err.message : "作成に失敗しました");
    }
  };

  // リセット
  const handleReset = () => {
    setParsedGeoJSON(null);
    setError(null);
    setStatus("idle");
    setProgress({ total: 0, completed: 0, failed: 0, errors: [] });
  };

  // 進捗率の計算
  const progressPercent = progress.total > 0 
    ? Math.round((progress.completed + progress.failed) / progress.total * 100) 
    : 0;

  const selectedTileset = tilesets.find((t) => t.id === selectedTilesetId);

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* ヘッダー */}
        <div className="flex items-center gap-4">
          <Link href="/features">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-2">
              <FileJson className="h-8 w-8" />
              GeoJSONインポート
            </h1>
            <p className="text-muted-foreground">
              GeoJSONファイルからフィーチャーを一括インポート
            </p>
          </div>
        </div>

        {/* エラー表示 */}
        {error && (
          <Card className="border-destructive">
            <CardContent className="pt-6">
              <div className="flex items-center gap-2 text-destructive">
                <AlertCircle className="h-5 w-5" />
                <p>{error}</p>
              </div>
            </CardContent>
          </Card>
        )}

        {/* 成功メッセージ */}
        {status === "success" && (
          <Card className="border-green-500 bg-green-500/5">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-green-600">
                  <Check className="h-5 w-5" />
                  <p>
                    {progress.completed}件のフィーチャーをインポートしました
                    {progress.failed > 0 && (
                      <span className="text-destructive ml-2">
                        （{progress.failed}件失敗）
                      </span>
                    )}
                  </p>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" onClick={handleReset}>
                    別のファイルをインポート
                  </Button>
                  <Link href="/features">
                    <Button>
                      <MapPin className="mr-2 h-4 w-4" />
                      フィーチャー一覧へ
                    </Button>
                  </Link>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        <div className="grid gap-6 lg:grid-cols-2">
          {/* 左カラム：ファイルアップロード */}
          <div className="space-y-6">
            {/* ファイルドロップゾーン */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Upload className="h-5 w-5" />
                  ファイルを選択
                </CardTitle>
                <CardDescription>
                  GeoJSON形式のファイルをアップロードしてください
                </CardDescription>
              </CardHeader>
              <CardContent>
                <GeoJSONDropzone
                  onFileLoaded={handleFileLoaded}
                  onError={handleFileError}
                  disabled={status === "importing"}
                />
              </CardContent>
            </Card>

            {/* タイルセット選択 */}
            <Card>
              <CardHeader>
                <CardTitle>インポート先タイルセット</CardTitle>
                <CardDescription>
                  フィーチャーを追加するタイルセットを選択
                </CardDescription>
              </CardHeader>
              <CardContent>
                {tilesets.length === 0 ? (
                  <div className="text-center py-4">
                    <p className="text-muted-foreground mb-4">
                      vectorタイプのタイルセットがありません
                    </p>
                    <Link href="/tilesets/new">
                      <Button variant="outline">タイルセットを作成</Button>
                    </Link>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <Label htmlFor="tileset-select">タイルセット</Label>
                    <select
                      id="tileset-select"
                      value={selectedTilesetId}
                      onChange={(e) => setSelectedTilesetId(e.target.value)}
                      disabled={status === "importing"}
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                    >
                      {tilesets.map((tileset) => (
                        <option key={tileset.id} value={tileset.id}>
                          {tileset.name}
                        </option>
                      ))}
                    </select>
                    {selectedTileset && (
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Badge variant="outline">{selectedTileset.type}</Badge>
                        <Badge variant="outline">{selectedTileset.format}</Badge>
                        {selectedTileset.is_public && (
                          <Badge variant="secondary">公開</Badge>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* インポート実行 */}
            {status === "importing" && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Loader2 className="h-5 w-5 animate-spin" />
                    インポート中...
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="w-full bg-secondary rounded-full h-3">
                    <div
                      className="bg-primary h-3 rounded-full transition-all duration-300"
                      style={{ width: `${progressPercent}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>
                      {progress.completed + progress.failed} / {progress.total}
                    </span>
                    <span>{progressPercent}%</span>
                  </div>
                  <div className="text-sm text-muted-foreground">
                    <span className="text-green-600">成功: {progress.completed}</span>
                    {progress.failed > 0 && (
                      <span className="text-destructive ml-4">
                        失敗: {progress.failed}
                      </span>
                    )}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* アクションボタン */}
            {status !== "importing" && status !== "success" && (
              <div className="flex gap-2">
                <Link href="/features" className="flex-1">
                  <Button variant="outline" className="w-full">
                    キャンセル
                  </Button>
                </Link>
                <Button
                  className="flex-1"
                  disabled={!parsedGeoJSON || !selectedTilesetId || tilesets.length === 0}
                  onClick={handleImport}
                >
                  <Upload className="mr-2 h-4 w-4" />
                  インポート実行
                  {parsedGeoJSON && ` (${parsedGeoJSON.featureCount}件)`}
                </Button>
              </div>
            )}
          </div>

          {/* 右カラム：プレビュー */}
          <Card>
            <CardHeader>
              <CardTitle>プレビュー</CardTitle>
              <CardDescription>
                インポートするフィーチャーを地図上で確認
              </CardDescription>
            </CardHeader>
            <CardContent>
              <GeoJSONPreview
                data={parsedGeoJSON?.data || null}
                height="500px"
              />
            </CardContent>
          </Card>
        </div>

        {/* エラー詳細（インポート中に失敗したもの） */}
        {progress.errors.length > 0 && (
          <Card className="border-destructive">
            <CardHeader>
              <CardTitle className="text-destructive">
                インポートエラー詳細
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-1 text-sm max-h-40 overflow-y-auto">
                {progress.errors.slice(0, 20).map((err, index) => (
                  <li key={index} className="text-destructive">
                    {err}
                  </li>
                ))}
                {progress.errors.length > 20 && (
                  <li className="text-muted-foreground">
                    ...他 {progress.errors.length - 20} 件のエラー
                  </li>
                )}
              </ul>
            </CardContent>
          </Card>
        )}
      </div>
    </AdminLayout>
  );
}
