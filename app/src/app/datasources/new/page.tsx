"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { AdminLayout } from "@/components/layout";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useApi } from "@/hooks/use-api";
import type { Tileset, DatasourceType, StorageProvider, DatasourceCreate } from "@/lib/api";
import {
  Plus,
  ArrowLeft,
  Loader2,
  FileJson,
  Image,
  AlertCircle,
  CheckCircle2,
  ExternalLink,
  Upload,
} from "lucide-react";

type InputMode = "url" | "upload";

export default function NewDatasourcePage() {
  const router = useRouter();
  const { api, isReady } = useApi();

  // フォーム状態
  const [inputMode, setInputMode] = useState<InputMode>("url");
  const [datasourceType, setDatasourceType] = useState<DatasourceType>("pmtiles");
  const [tilesetId, setTilesetId] = useState<string>("");
  const [url, setUrl] = useState<string>("");
  const [storageProvider, setStorageProvider] = useState<StorageProvider>("http");
  const [file, setFile] = useState<File | null>(null);

  // タイルセット一覧
  const [tilesets, setTilesets] = useState<Tileset[]>([]);
  const [tilesetsLoading, setTilesetsLoading] = useState(true);

  // 送信状態
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // URL検証状態
  const [urlValid, setUrlValid] = useState<boolean | null>(null);

  // タイルセット一覧を取得
  useEffect(() => {
    const fetchTilesets = async () => {
      if (!isReady || !api) return;

      setTilesetsLoading(true);
      try {
        const response = await api.listTilesets({ include_private: true });
        let tilesetsArray: Tileset[] = [];
        if (Array.isArray(response)) {
          tilesetsArray = response;
        } else if (response && typeof response === "object" && "tilesets" in response) {
          tilesetsArray = (response as { tilesets: Tileset[] }).tilesets;
        }
        setTilesets(tilesetsArray);
      } catch (err) {
        console.error("Failed to fetch tilesets:", err);
      } finally {
        setTilesetsLoading(false);
      }
    };

    fetchTilesets();
  }, [api, isReady]);

  // タイプに応じてフィルタリングされたタイルセット
  const filteredTilesets = tilesets.filter((ts) => {
    if (datasourceType === "pmtiles") {
      return ts.type === "pmtiles";
    } else if (datasourceType === "cog") {
      return ts.type === "raster";
    }
    return true;
  });

  // URL検証
  const validateUrl = (inputUrl: string) => {
    if (!inputUrl) {
      setUrlValid(null);
      return;
    }

    try {
      const parsed = new URL(inputUrl);
      const isValid =
        (parsed.protocol === "http:" || parsed.protocol === "https:") &&
        parsed.hostname.length > 0;
      setUrlValid(isValid);
    } catch {
      setUrlValid(false);
    }
  };

  // URL変更時の検証
  const handleUrlChange = (value: string) => {
    setUrl(value);
    validateUrl(value);

    // URL からストレージプロバイダーを自動判定
    // S3 互換 storage には Fly Tigris (`*.fly.storage.tigris.dev`) /
    // AWS S3 (`amazonaws.com` / `s3.`) / Cloudflare R2 (`r2.cloudflarestorage.com`)
    // を含める。Issue #72 (PR #88) で旧 supabase 自動判定は廃止。
    const isS3Compatible =
      value.includes("fly.storage.tigris.dev") ||
      value.includes("amazonaws.com") ||
      value.includes("s3.") ||
      value.includes("r2.cloudflarestorage.com");
    setStorageProvider(isS3Compatible ? "s3" : "http");
  };

  // タイプ変更時にタイルセット選択とファイル選択をリセット
  const handleTypeChange = (value: DatasourceType) => {
    setDatasourceType(value);
    setTilesetId("");
    setFile(null);
  };

  const handleModeChange = (value: InputMode) => {
    setInputMode(value);
    setError(null);
    setSuccess(null);
  };

  // ファイル拡張子のヒント（type に応じて変える）
  const acceptHint =
    datasourceType === "pmtiles" ? ".pmtiles" : ".tif,.tiff,.geotiff";

  // フォーム送信
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!isReady || !api) {
      setError("APIが準備できていません。しばらくお待ちください。");
      return;
    }

    if (!tilesetId) {
      setError("タイルセットを選択してください。");
      return;
    }

    if (inputMode === "url") {
      if (!url || !urlValid) {
        setError("有効なURLを入力してください。");
        return;
      }
    } else {
      if (!file) {
        setError("アップロードするファイルを選択してください。");
        return;
      }
    }

    setIsSubmitting(true);
    setError(null);
    setSuccess(null);

    try {
      let resultId: string;
      if (inputMode === "url") {
        const data: DatasourceCreate = {
          tileset_id: tilesetId,
          type: datasourceType,
          url: url,
          storage_provider: storageProvider,
        };
        const result = await api.createDatasource(data);
        resultId = result.id;
      } else {
        // Direct upload mode (Issue #101)
        const result =
          datasourceType === "cog"
            ? await api.uploadCog(file as File, tilesetId)
            : await api.uploadPmtiles(file as File, tilesetId);
        resultId = result.id;
      }
      setSuccess("データソースを登録しました。");

      // 詳細ページへリダイレクト
      setTimeout(() => {
        router.push(`/datasources/${resultId}`);
      }, 1000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "データソースの登録に失敗しました");
      setIsSubmitting(false);
    }
  };

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* ヘッダー */}
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" asChild>
            <Link href="/datasources">
              <ArrowLeft className="mr-2 h-4 w-4" />
              戻る
            </Link>
          </Button>
        </div>

        <div>
          <div className="flex items-center gap-2">
            <Plus className="h-8 w-8" />
            <h1 className="text-3xl font-bold">新規データソース登録</h1>
          </div>
          <p className="mt-1 text-muted-foreground">
            PMTilesまたはCOGファイルを登録します
          </p>
        </div>

        {/* フォーム */}
        <div className="max-w-2xl">
          <form onSubmit={handleSubmit}>
            <Card>
              <CardHeader>
                <CardTitle>データソース情報</CardTitle>
                <CardDescription>
                  タイルセットに紐づけるデータソースの情報を入力してください
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* エラー表示 */}
                {error && (
                  <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                )}

                {/* 成功表示 */}
                {success && (
                  <Alert className="border-green-500 bg-green-50">
                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                    <AlertDescription className="text-green-600">
                      {success}
                    </AlertDescription>
                  </Alert>
                )}

                {/* データソースタイプ */}
                <div className="space-y-2">
                  <Label htmlFor="type">データソースタイプ *</Label>
                  <Select
                    value={datasourceType}
                    onValueChange={(v) => handleTypeChange(v as DatasourceType)}
                    disabled={isSubmitting}
                  >
                    <SelectTrigger id="type" data-testid="datasource-form-type">
                      <SelectValue placeholder="タイプを選択" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="pmtiles">
                        <div className="flex items-center gap-2">
                          <FileJson className="h-4 w-4" />
                          PMTiles
                        </div>
                      </SelectItem>
                      <SelectItem value="cog">
                        <div className="flex items-center gap-2">
                          <Image className="h-4 w-4" />
                          COG (Cloud Optimized GeoTIFF)
                        </div>
                      </SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="text-sm text-muted-foreground">
                    {datasourceType === "pmtiles"
                      ? "PMTilesはベクタタイルアーカイブ形式です（タイプが「pmtiles」のタイルセットに紐づけられます）"
                      : "COGはCloud Optimized GeoTIFF形式です（タイプが「raster」のタイルセットに紐づけられます）"}
                  </p>
                </div>

                {/* タイルセット選択 */}
                <div className="space-y-2">
                  <Label htmlFor="tileset">タイルセット *</Label>
                  {tilesetsLoading ? (
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      タイルセットを読み込み中...
                    </div>
                  ) : filteredTilesets.length === 0 ? (
                    <div className="space-y-2">
                      <Alert>
                        <AlertCircle className="h-4 w-4" />
                        <AlertDescription>
                          {datasourceType === "pmtiles"
                            ? "pmtilesタイプのタイルセットがありません。"
                            : "rasterタイプのタイルセットがありません。"}
                          <br />
                          先にタイルセットを作成してください。
                        </AlertDescription>
                      </Alert>
                      <Button variant="outline" asChild>
                        <Link href="/tilesets/new">
                          <Plus className="mr-2 h-4 w-4" />
                          タイルセットを作成
                        </Link>
                      </Button>
                    </div>
                  ) : (
                    <Select
                      value={tilesetId}
                      onValueChange={setTilesetId}
                      disabled={isSubmitting}
                    >
                      <SelectTrigger id="tileset" data-testid="datasource-form-tileset">
                        <SelectValue placeholder="タイルセットを選択" />
                      </SelectTrigger>
                      <SelectContent>
                        {filteredTilesets.map((ts) => (
                          <SelectItem key={ts.id} value={ts.id}>
                            <div className="flex items-center gap-2">
                              <span>{ts.name}</span>
                              <span className="text-xs text-muted-foreground">
                                ({ts.type})
                              </span>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                </div>

                {/* 入力モード切り替え (Issue #101) */}
                <div className="space-y-2">
                  <Label htmlFor="mode">入力方法 *</Label>
                  <Select
                    value={inputMode}
                    onValueChange={(v) => handleModeChange(v as InputMode)}
                    disabled={isSubmitting}
                  >
                    <SelectTrigger id="mode" data-testid="datasource-form-mode">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="url">
                        <div className="flex items-center gap-2">
                          <ExternalLink className="h-4 w-4" />
                          URL を指定（外部 HTTP(S) サーバー）
                        </div>
                      </SelectItem>
                      <SelectItem value="upload">
                        <div className="flex items-center gap-2">
                          <Upload className="h-4 w-4" />
                          ファイルをアップロード（Fly Tigris に保存）
                        </div>
                      </SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="text-sm text-muted-foreground">
                    {inputMode === "url"
                      ? "外部の HTTP(S) URL を指定します（s3:// 等の内部 URL は対象外）"
                      : "ローカルのファイルを直接 Fly Tigris (S3 互換 storage) にアップロードします"}
                  </p>
                </div>

                {inputMode === "url" ? (
                  <>
                    {/* URL */}
                    <div className="space-y-2">
                      <Label htmlFor="url">URL *</Label>
                      <div className="relative">
                        <Input
                          id="url"
                          type="url"
                          value={url}
                          onChange={(e) => handleUrlChange(e.target.value)}
                          placeholder={
                            datasourceType === "pmtiles"
                              ? "https://example.com/tiles.pmtiles"
                              : "https://example.com/image.tif"
                          }
                          disabled={isSubmitting}
                          className={
                            urlValid === false
                              ? "border-red-500 focus:ring-red-500"
                              : urlValid === true
                              ? "border-green-500 focus:ring-green-500"
                              : ""
                          }
                          data-testid="datasource-form-url"
                        />
                        {urlValid !== null && (
                          <div className="absolute right-3 top-1/2 -translate-y-1/2">
                            {urlValid ? (
                              <CheckCircle2 className="h-4 w-4 text-green-500" />
                            ) : (
                              <AlertCircle className="h-4 w-4 text-red-500" />
                            )}
                          </div>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground">
                        {datasourceType === "pmtiles"
                          ? "PMTilesファイルのURLを入力してください（HTTP Range Requestsに対応している必要があります）"
                          : "Cloud Optimized GeoTIFFファイルのURLを入力してください"}
                      </p>
                      {url && (
                        <a
                          href={url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
                        >
                          URLを開く
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      )}
                    </div>

                    {/* ストレージプロバイダー */}
                    <div className="space-y-2">
                      <Label htmlFor="storage">ストレージプロバイダー</Label>
                      <Select
                        value={storageProvider}
                        onValueChange={(v) => setStorageProvider(v as StorageProvider)}
                        disabled={isSubmitting}
                      >
                        <SelectTrigger id="storage" data-testid="datasource-form-storage-provider">
                          <SelectValue placeholder="ストレージを選択" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="http">HTTP（汎用）</SelectItem>
                          <SelectItem value="s3">S3 互換 (Fly Tigris / AWS S3 / R2)</SelectItem>
                        </SelectContent>
                      </Select>
                      <p className="text-sm text-muted-foreground">
                        URLから自動判定されますが、手動で変更することもできます
                      </p>
                    </div>
                  </>
                ) : (
                  /* アップロードモード (Issue #101) */
                  <div className="space-y-2">
                    <Label htmlFor="file">ファイル *</Label>
                    {/*
                     * `<input type="file">` は uncontrolled element のため、
                     * `setFile(null)` だけでは DOM 側の選択ファイル名が残り
                     * UI と state がずれる。`key` に datasourceType / inputMode
                     * を含めることで、type 切替時に input ごと remount し
                     * 表示・state を同期させる。
                     */}
                    <Input
                      key={`file-${datasourceType}-${inputMode}`}
                      id="file"
                      data-testid="datasource-form-file"
                      type="file"
                      accept={acceptHint}
                      disabled={isSubmitting}
                      onChange={(e) => {
                        const f = e.target.files?.[0] ?? null;
                        setFile(f);
                      }}
                    />
                    <p className="text-sm text-muted-foreground">
                      {datasourceType === "pmtiles"
                        ? "PMTiles ファイル（拡張子 .pmtiles）を選択してください"
                        : "Cloud Optimized GeoTIFF ファイル（拡張子 .tif / .tiff / .geotiff）を選択してください"}
                    </p>
                    {file && (
                      <p className="text-sm">
                        選択中: <span className="font-mono">{file.name}</span>{" "}
                        <span className="text-muted-foreground">
                          ({(file.size / (1024 * 1024)).toFixed(2)} MB)
                        </span>
                      </p>
                    )}
                  </div>
                )}

                {/* 送信ボタン */}
                <div className="flex justify-end gap-2 pt-4">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => router.push("/datasources")}
                    disabled={isSubmitting}
                  >
                    キャンセル
                  </Button>
                  <Button
                    type="submit"
                    disabled={
                      isSubmitting ||
                      !tilesetId ||
                      filteredTilesets.length === 0 ||
                      (inputMode === "url" ? !url || !urlValid : !file)
                    }
                    data-testid="datasource-form-submit"
                  >
                    {isSubmitting ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        {inputMode === "upload" ? "アップロード中..." : "登録中..."}
                      </>
                    ) : (
                      <>
                        {inputMode === "upload" ? (
                          <Upload className="mr-2 h-4 w-4" />
                        ) : (
                          <Plus className="mr-2 h-4 w-4" />
                        )}
                        {inputMode === "upload" ? "アップロード" : "登録する"}
                      </>
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </form>
        </div>

        {/* ヘルプ */}
        <Card className="max-w-2xl">
          <CardHeader>
            <CardTitle className="text-lg">ヒント</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm text-muted-foreground">
            <div>
              <h4 className="font-medium text-foreground">PMTilesとは？</h4>
              <p>
                PMTilesは、ベクタタイルを単一ファイルにアーカイブした形式です。
                HTTP Range Requestsを利用して効率的にタイルを取得できます。
              </p>
            </div>
            <div>
              <h4 className="font-medium text-foreground">COGとは？</h4>
              <p>
                Cloud Optimized GeoTIFF（COG）は、クラウド上での効率的なアクセスに最適化されたGeoTIFF形式です。
                部分的な読み取りが可能で、大きな画像でも必要な部分だけを取得できます。
              </p>
            </div>
            <div>
              <h4 className="font-medium text-foreground">対応ストレージ</h4>
              <ul className="list-disc list-inside space-y-1 mt-1">
                <li>S3 互換 - Fly Tigris / AWS S3 / Cloudflare R2 等（API キーで認証）</li>
                <li>HTTP - 一般的なHTTPサーバー（CORSとRange Requestsが必要）</li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium text-foreground">直接アップロード（Issue #101）</h4>
              <p>
                「ファイルをアップロード」を選ぶと、Fly Tigris の private bucket
                に直接保存され、内部 URL（<span className="font-mono">s3://</span>）として
                管理されます。タイル配信は API 経由で行われるため、外部からは bucket に
                アクセスできない安全な構成になります。
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </AdminLayout>
  );
}
