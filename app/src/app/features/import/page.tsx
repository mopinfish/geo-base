"use client";

import { useState, useEffect, useRef } from "react";
import { useTranslations } from "next-intl";
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
import { Input } from "@/components/ui/input";
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
  Layers,
  Zap,
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

// バルクインサートのチャンクサイズ
const BULK_CHUNK_SIZE = 500;

export default function GeoJSONImportPage() {
  const t = useTranslations("features.import");
  const { api, isReady } = useApi();
  
  // 状態管理
  const [tilesets, setTilesets] = useState<Tileset[]>([]);
  const [selectedTilesetId, setSelectedTilesetId] = useState<string>("");
  const [layerName, setLayerName] = useState<string>("imported");
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
  const [importTime, setImportTime] = useState<number | null>(null);
  const hasAutoSelectedTileset = useRef(false);

  // タイルセット一覧の取得（vectorタイプのみ）
  useEffect(() => {
    if (!isReady) return;

    const fetchTilesets = async () => {
      try {
        const response = await api.listTilesets({ include_private: true });
        // APIレスポンス形式に対応
        const data = Array.isArray(response) ? response : response?.tilesets || [];
        // vectorタイプのみフィルタリング
        const vectorTilesets = data.filter((t: Tileset) => t.type === "vector");
        setTilesets(vectorTilesets);
        
        // 最初のタイルセットを選択
        if (vectorTilesets.length > 0 && !hasAutoSelectedTileset.current) {
          hasAutoSelectedTileset.current = true;
          setSelectedTilesetId((prev) => prev || vectorTilesets[0].id);
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
    setImportTime(null);
  };

  // ファイル読み込みエラー時
  const handleFileError = (errorMessage: string) => {
    setError(errorMessage);
    setParsedGeoJSON(null);
  };

  // バルクインポート実行
  const handleImport = async () => {
    if (!parsedGeoJSON || !selectedTilesetId) return;

    // レイヤー名のバリデーション
    const trimmedLayerName = layerName.trim();
    if (!trimmedLayerName) {
      setError(t("error_no_layer"));
      return;
    }

    setStatus("importing");
    setError(null);
    setBoundsResult(null);
    setImportTime(null);
    
    const startTime = Date.now();
    const features = parsedGeoJSON.data.features;
    const total = features.length;
    let completed = 0;
    let failed = 0;
    const errors: string[] = [];

    setProgress({ total, completed, failed, errors });

    // チャンクに分割してバルクインサート
    const chunks: GeoJSONFeature[][] = [];
    for (let i = 0; i < features.length; i += BULK_CHUNK_SIZE) {
      chunks.push(features.slice(i, i + BULK_CHUNK_SIZE));
    }

    console.log(`[GeoJSONImport] Starting bulk import: ${total} features in ${chunks.length} chunks`);

    for (let chunkIndex = 0; chunkIndex < chunks.length; chunkIndex++) {
      const chunk = chunks[chunkIndex];
      
      try {
        // バルクインサートAPIを呼び出し
        const response = await api.createFeaturesBulk({
          tileset_id: selectedTilesetId,
          layer_name: trimmedLayerName,
          features: chunk,
        });

        completed += response.success_count;
        failed += response.failed_count;
        
        // エラーメッセージを収集
        if (response.errors && response.errors.length > 0) {
          const chunkOffset = chunkIndex * BULK_CHUNK_SIZE;
          response.errors.forEach((err: string) => {
            // エラーメッセージにチャンクオフセットを加算
            errors.push(err.replace(/Feature #(\d+)/, (_, num) => 
              `Feature #${parseInt(num) + chunkOffset}`
            ));
          });
        }

        console.log(`[GeoJSONImport] Chunk ${chunkIndex + 1}/${chunks.length}: ${response.success_count} success, ${response.failed_count} failed`);

      } catch (err) {
        // チャンク全体が失敗した場合
        console.error(`[GeoJSONImport] Chunk ${chunkIndex + 1} failed:`, err);
        failed += chunk.length;
        errors.push(`Chunk ${chunkIndex + 1}: ${err instanceof Error ? err.message : "Unknown error"}`);
      }

      // プログレスを更新
      setProgress({ total, completed, failed, errors: [...errors] });
    }

    const endTime = Date.now();
    setImportTime(endTime - startTime);

    console.log(`[GeoJSONImport] Completed: ${completed} success, ${failed} failed in ${endTime - startTime}ms`);

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
      setError(t("error_all_failed"));
    }
  };

  // リセット
  const handleReset = () => {
    setParsedGeoJSON(null);
    setError(null);
    setStatus("idle");
    setProgress({ total: 0, completed: 0, failed: 0, errors: [] });
    setBoundsResult(null);
    setImportTime(null);
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
              {t("title")}
            </h1>
            <p className="text-muted-foreground flex items-center gap-2">
              <Zap className="h-4 w-4 text-yellow-500" />
              {t("subtitle", { chunk_size: BULK_CHUNK_SIZE })}
            </p>
          </div>
        </div>

        {/* エラー表示 */}
        {error && (
          <Card className="border-destructive" data-testid="import-error-message">
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
          <Card className="border-green-500 bg-green-500/5" data-testid="import-success-message">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-green-600">
                    <Check className="h-5 w-5" />
                    <p>
                      {t("success_count", { count: progress.completed })}
                      {progress.failed > 0 && (
                        <span className="text-destructive ml-2">
                          {t("success_failed_suffix", { failed: progress.failed })}
                        </span>
                      )}
                    </p>
                  </div>
                  {importTime !== null && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Zap className="h-4 w-4 text-yellow-500" />
                      <span>
                        {t("success_time", {
                          time: (importTime / 1000).toFixed(2),
                          rate: (progress.completed / (importTime / 1000)).toFixed(0),
                        })}
                      </span>
                    </div>
                  )}
                  {boundsResult && boundsResult.bounds && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Map className="h-4 w-4" />
                      <span>
                        {t("bounds_updated", {
                          bounds: boundsResult.bounds.map((b) => b.toFixed(4)).join(", "),
                        })}
                      </span>
                    </div>
                  )}
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" onClick={handleReset}>
                    {t("success_button_another")}
                  </Button>
                  <Link href={`/tilesets/${selectedTilesetId}`}>
                    <Button>
                      <MapPin className="mr-2 h-4 w-4" />
                      {t("success_button_view_tileset")}
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
                <p>{t("calculating_bounds")}</p>
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
                  {t("file_card_title")}
                </CardTitle>
                <CardDescription>
                  {t("file_card_description")}
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
                <CardTitle>{t("tileset_card_title")}</CardTitle>
                <CardDescription>
                  {t("tileset_card_description")}
                </CardDescription>
              </CardHeader>
              <CardContent>
                {tilesets.length === 0 ? (
                  <div className="text-center py-4">
                    <p className="text-muted-foreground mb-4">
                      {t("tileset_none")}
                    </p>
                    <Link href="/tilesets/new">
                      <Button variant="outline">{t("tileset_create_link")}</Button>
                    </Link>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <Label htmlFor="tileset-select">{t("tileset_label")}</Label>
                    <select
                      id="tileset-select"
                      value={selectedTilesetId}
                      onChange={(e) => setSelectedTilesetId(e.target.value)}
                      disabled={status === "importing" || status === "calculating"}
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                      data-testid="import-tileset-select"
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
                          <Badge variant="secondary">{t("badge_public")}</Badge>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* レイヤー名設定 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Layers className="h-5 w-5" />
                  {t("layer_card_title")}
                </CardTitle>
                <CardDescription>
                  {t("layer_card_description")}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <Label htmlFor="layer-name">{t("layer_label")}</Label>
                  <Input
                    id="layer-name"
                    value={layerName}
                    onChange={(e) => setLayerName(e.target.value)}
                    placeholder={t("layer_placeholder")}
                    disabled={status === "importing" || status === "calculating"}
                  />
                  <p className="text-xs text-muted-foreground">
                    {t("layer_help")}
                  </p>
                </div>
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
                          <span>{t("progress_importing")}</span>
                          <span>{t("progress_percent", { percent: progressPercent })}</span>
                        </div>
                        <div className="h-2 bg-secondary rounded-full overflow-hidden">
                          <div
                            className="h-full bg-primary transition-all duration-300"
                            style={{ width: `${progressPercent}%` }}
                          />
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {t("progress_detail", { completed: progress.completed, total: progress.total })}
                          {progress.failed > 0 && ` ${t("progress_failed", { failed: progress.failed })}`}
                        </p>
                      </div>
                    )}

                    <Button
                      onClick={handleImport}
                      disabled={status === "importing" || status === "calculating" || !selectedTilesetId}
                      className="w-full"
                      data-testid="import-submit"
                    >
                      {status === "importing" ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          {t("import_button")}
                        </>
                      ) : (
                        <>
                          <Zap className="mr-2 h-4 w-4" />
                          {t("import_button_ready", { count: parsedGeoJSON.data.features.length })}
                        </>
                      )}
                    </Button>

                    {progress.errors.length > 0 && (
                      <div className="mt-4 max-h-32 overflow-y-auto text-sm text-destructive">
                        {progress.errors.slice(0, 5).map((error, index) => (
                          <p key={index}>{error}</p>
                        ))}
                        {progress.errors.length > 5 && (
                          <p>{t("error_summary_more", { count: progress.errors.length - 5 })}</p>
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
                  <CardTitle>{t("preview_card_title")}</CardTitle>
                  <CardDescription>
                    {t("preview_description", { fileName: parsedGeoJSON.fileName, count: parsedGeoJSON.data.features.length })}
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
                    <p>{t("preview_placeholder")}</p>
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
