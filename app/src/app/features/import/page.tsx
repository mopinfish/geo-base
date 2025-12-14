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
  Map,
} from "lucide-react";
import Link from "next/link";

type ImportStatus = "idle" | "importing" | "calculating" | "success" | "error";

interface ImportProgress {
  total: number;
  completed: number;
  failed: number;
  errors: string[];
}

interface BoundsResult {
  feature_count: number;
  bounds: number[] | null;
  center: number[] | null;
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
  const [boundsResult, setBoundsResult] = useState<BoundsResult | null>(null);

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
    setBoundsResult(null);
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
    setBoundsResult(null);
    
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

    // インポート完了後、boundsを計算
    if (completed > 0) {
      setStatus("calculating");
      try {
        const boundsResponse = await api.calculateTilesetBounds(selectedTilesetId);
        setBoundsResult({
          feature_count: boundsResponse.feature_count,
          bounds: boundsResponse.bounds,
          center: boundsResponse.center,
        });
        setStatus("success");
      } catch (boundsError) {
        console.warn("Failed to calculate bounds:", boundsError);
        // bounds計算に失敗してもインポート自体は成功とみなす
        setStatus("success");
      }
    } else {
      setStatus("error");
      setError(`すべてのフィーチャーのインポートに失敗しました`);
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
    setBoundsResult(null);
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
                <div className="space-y-2">
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
                  {boundsResult && boundsResult.bounds && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Map className="h-4 w-4" />
                      <span>
                        Bounds更新: [{boundsResult.bounds.map(b => b.toFixed(4)).join(", ")}]
                      </span>
                    </div>
                  )}
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" onClick={handleReset}>
                    別のファイルをインポート
                  </Button>
                  <Link href={`/tilesets/${selectedTilesetId}`}>
                    <Button>
                      <MapPin className="mr-2 h-4 w-4" />
                      タイルセットを確認
                    </Button>
                  </Link>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Bounds計算中 */}
        {status === "calculating" && (
          <Card className="border-blue-500 bg-blue-500/5">
            <CardContent className="pt-6">
              <div className="flex items-center gap-2 text-blue-600">
                <Loader2 className="h-5 w-5 animate-spin" />
                <p>タイルセットのBoundsを計算中...</p>
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
                  disabled={status === "importing" || status === "calculating"}
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
                      disabled={status === "importing" || status === "calculating"}
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

            {/* インポートボタン */}
            {parsedGeoJSON && status !== "success" && (
              <Card>
                <CardContent className="pt-6">
                  <div className="space-y-4">
                    {status === "importing" && (
                      <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span>インポート中...</span>
                          <span>{progressPercent}%</span>
                        </div>
                        <div className="h-2 bg-secondary rounded-full overflow-hidden">
                          <div
                            className="h-full bg-primary transition-all duration-300"
                            style={{ width: `${progressPercent}%` }}
                          />
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {progress.completed} / {progress.total} 完了
                          {progress.failed > 0 && ` (${progress.failed} 失敗)`}
                        </p>
                      </div>
                    )}

                    <Button
                      onClick={handleImport}
                      disabled={status === "importing" || status === "calculating" || !selectedTilesetId}
                      className="w-full"
                    >
                      {status === "importing" ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          インポート中...
                        </>
                      ) : (
                        <>
                          <Upload className="mr-2 h-4 w-4" />
                          {parsedGeoJSON.data.features.length}件のフィーチャーをインポート
                        </>
                      )}
                    </Button>

                    {progress.errors.length > 0 && (
                      <div className="mt-4 max-h-32 overflow-y-auto text-sm text-destructive">
                        {progress.errors.slice(0, 5).map((error, index) => (
                          <p key={index}>{error}</p>
                        ))}
                        {progress.errors.length > 5 && (
                          <p>...他 {progress.errors.length - 5} 件のエラー</p>
                        )}
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          {/* 右カラム：プレビュー */}
          <div>
            {parsedGeoJSON ? (
              <Card>
                <CardHeader>
                  <CardTitle>プレビュー</CardTitle>
                  <CardDescription>
                    {parsedGeoJSON.fileName} - {parsedGeoJSON.data.features.length}件のフィーチャー
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <GeoJSONPreview 
                    data={parsedGeoJSON.data}
                    height="400px"
                  />
                </CardContent>
              </Card>
            ) : (
              <Card>
                <CardContent className="pt-6">
                  <div className="flex flex-col items-center justify-center h-64 text-center text-muted-foreground">
                    <FileJson className="h-16 w-16 mb-4 opacity-50" />
                    <p>GeoJSONファイルをアップロードすると</p>
                    <p>ここにプレビューが表示されます</p>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </AdminLayout>
  );
}
