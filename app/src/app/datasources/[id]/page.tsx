"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
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
import { Badge } from "@/components/ui/badge";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useApi } from "@/hooks/use-api";
import type { Datasource, DatasourceTestResult } from "@/lib/api";
import {
  ArrowLeft,
  Loader2,
  FileJson,
  Image,
  Database,
  Trash2,
  ExternalLink,
  RefreshCw,
  Play,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Layers,
  Globe,
  Lock,
  Calendar,
  Link as LinkIcon,
} from "lucide-react";

export default function DatasourceDetailPage() {
  const router = useRouter();
  const params = useParams();
  const datasourceId = params.id as string;
  const { api, isReady } = useApi();

  const [datasource, setDatasource] = useState<Datasource | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 接続テスト状態
  const [testLoading, setTestLoading] = useState(false);
  const [testResult, setTestResult] = useState<DatasourceTestResult | null>(null);

  // 削除ダイアログ
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);

  // データソース取得
  const fetchDatasource = async () => {
    if (!isReady || !api) return;

    setLoading(true);
    setError(null);
    try {
      const data = await api.getDatasource(datasourceId);
      setDatasource(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "データソースの取得に失敗しました");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDatasource();
  }, [api, isReady, datasourceId]);

  // 接続テスト
  const handleTestConnection = async () => {
    if (!api) return;

    setTestLoading(true);
    setTestResult(null);
    try {
      const result = await api.testDatasource(datasourceId);
      setTestResult(result);
    } catch (err) {
      setTestResult({
        status: "error",
        type: datasource?.type || "pmtiles",
        message: err instanceof Error ? err.message : "テストに失敗しました",
      });
    } finally {
      setTestLoading(false);
    }
  };

  // 削除
  const handleDelete = async () => {
    if (!api) return;

    setDeleteLoading(true);
    try {
      await api.deleteDatasource(datasourceId);
      router.push("/datasources");
    } catch (err) {
      setError(err instanceof Error ? err.message : "削除に失敗しました");
      setDeleteLoading(false);
      setDeleteDialogOpen(false);
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case "pmtiles":
        return <FileJson className="h-5 w-5" />;
      case "cog":
        return <Image className="h-5 w-5" />;
      default:
        return <Database className="h-5 w-5" />;
    }
  };

  const getStorageProviderLabel = (provider: string) => {
    switch (provider) {
      case "supabase":
        return "Supabase Storage";
      case "s3":
        return "AWS S3";
      case "http":
        return "HTTP";
      default:
        return provider;
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("ja-JP", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  };

  const formatBounds = (bounds: number[] | Record<string, number> | undefined) => {
    if (!bounds) return "未設定";
    if (Array.isArray(bounds)) {
      return `[${bounds.map((b) => b.toFixed(4)).join(", ")}]`;
    }
    return JSON.stringify(bounds);
  };

  if (loading) {
    return (
      <AdminLayout>
        <div className="flex items-center justify-center min-h-[400px]">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </AdminLayout>
    );
  }

  if (error || !datasource) {
    return (
      <AdminLayout>
        <div className="space-y-6">
          <Button variant="ghost" size="sm" asChild>
            <Link href="/datasources">
              <ArrowLeft className="mr-2 h-4 w-4" />
              戻る
            </Link>
          </Button>
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              {error || "データソースが見つかりませんでした"}
            </AlertDescription>
          </Alert>
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
            <Link href="/datasources">
              <ArrowLeft className="mr-2 h-4 w-4" />
              戻る
            </Link>
          </Button>
        </div>

        <div className="flex items-start justify-between">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-muted">
              {getTypeIcon(datasource.type)}
            </div>
            <div>
              <h1 className="text-3xl font-bold flex items-center gap-2">
                {datasource.tileset_name}
                <Badge variant="outline" className="uppercase">
                  {datasource.type}
                </Badge>
              </h1>
              <p className="text-muted-foreground">データソース詳細</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              onClick={handleTestConnection}
              disabled={testLoading}
            >
              {testLoading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Play className="mr-2 h-4 w-4" />
              )}
              接続テスト
            </Button>
            <Button
              variant="destructive"
              onClick={() => setDeleteDialogOpen(true)}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              削除
            </Button>
          </div>
        </div>

        {/* 接続テスト結果 */}
        {testResult && (
          <Alert
            variant={testResult.status === "ok" ? "default" : "destructive"}
            className={
              testResult.status === "ok"
                ? "border-green-500 bg-green-50"
                : ""
            }
          >
            {testResult.status === "ok" ? (
              <CheckCircle2 className="h-4 w-4 text-green-600" />
            ) : (
              <XCircle className="h-4 w-4" />
            )}
            <AlertDescription
              className={testResult.status === "ok" ? "text-green-600" : ""}
            >
              {testResult.status === "ok"
                ? "接続に成功しました。データソースは正常にアクセス可能です。"
                : testResult.message || "接続に失敗しました。"}
            </AlertDescription>
          </Alert>
        )}

        <div className="grid gap-6 lg:grid-cols-2">
          {/* 基本情報 */}
          <Card>
            <CardHeader>
              <CardTitle>基本情報</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">ID</p>
                  <p className="font-mono text-sm">{datasource.id}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">タイプ</p>
                  <Badge className="uppercase mt-1">{datasource.type}</Badge>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">ストレージ</p>
                  <Badge variant="outline" className="mt-1">
                    {getStorageProviderLabel(datasource.storage_provider)}
                  </Badge>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">公開設定</p>
                  <Badge
                    variant={datasource.is_public ? "default" : "secondary"}
                    className="mt-1"
                  >
                    {datasource.is_public ? (
                      <>
                        <Globe className="mr-1 h-3 w-3" />
                        公開
                      </>
                    ) : (
                      <>
                        <Lock className="mr-1 h-3 w-3" />
                        非公開
                      </>
                    )}
                  </Badge>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* タイルセット情報 */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Layers className="h-5 w-5" />
                関連タイルセット
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Link
                href={`/tilesets/${datasource.tileset_id}`}
                className="flex items-center gap-2 text-primary hover:underline font-medium"
              >
                {datasource.tileset_name}
                <ExternalLink className="h-4 w-4" />
              </Link>
              <p className="text-sm text-muted-foreground mt-2">
                タイルセットID: {datasource.tileset_id}
              </p>
            </CardContent>
          </Card>

          {/* URL情報 */}
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <LinkIcon className="h-5 w-5" />
                データソースURL
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2 p-3 bg-muted rounded-lg">
                <code className="flex-1 text-sm break-all">{datasource.url}</code>
                <a
                  href={datasource.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="shrink-0"
                >
                  <Button variant="ghost" size="sm">
                    <ExternalLink className="h-4 w-4" />
                  </Button>
                </a>
              </div>
            </CardContent>
          </Card>

          {/* 詳細情報（PMTiles固有） */}
          {datasource.type === "pmtiles" && (
            <Card>
              <CardHeader>
                <CardTitle>PMTiles情報</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">タイルタイプ</p>
                    <p className="font-medium">{datasource.tile_type || "未取得"}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">圧縮形式</p>
                    <p className="font-medium">{datasource.compression || "未取得"}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">最小ズーム</p>
                    <p className="font-medium">
                      {datasource.min_zoom !== undefined ? datasource.min_zoom : "未設定"}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">最大ズーム</p>
                    <p className="font-medium">
                      {datasource.max_zoom !== undefined ? datasource.max_zoom : "未設定"}
                    </p>
                  </div>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">バウンディングボックス</p>
                  <p className="font-mono text-sm mt-1">
                    {formatBounds(datasource.bounds)}
                  </p>
                </div>
                {datasource.layers && Array.isArray(datasource.layers) && (
                  <div>
                    <p className="text-sm text-muted-foreground">レイヤー数</p>
                    <p className="font-medium">{datasource.layers.length}</p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* 詳細情報（COG固有） */}
          {datasource.type === "cog" && (
            <Card>
              <CardHeader>
                <CardTitle>COG情報</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">バンド数</p>
                    <p className="font-medium">
                      {datasource.band_count !== undefined ? datasource.band_count : "未取得"}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">ネイティブCRS</p>
                    <p className="font-medium">{datasource.native_crs || "未取得"}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">推奨最小ズーム</p>
                    <p className="font-medium">
                      {datasource.min_zoom !== undefined ? datasource.min_zoom : "未設定"}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">推奨最大ズーム</p>
                    <p className="font-medium">
                      {datasource.max_zoom !== undefined ? datasource.max_zoom : "未設定"}
                    </p>
                  </div>
                </div>
                {datasource.band_descriptions && (
                  <div>
                    <p className="text-sm text-muted-foreground">バンド説明</p>
                    <ul className="list-disc list-inside mt-1">
                      {datasource.band_descriptions.map((desc, i) => (
                        <li key={i} className="text-sm">
                          Band {i + 1}: {desc}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* 日時情報 */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calendar className="h-5 w-5" />
                日時情報
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p className="text-sm text-muted-foreground">作成日時</p>
                <p className="font-medium">{formatDate(datasource.created_at)}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">更新日時</p>
                <p className="font-medium">{formatDate(datasource.updated_at)}</p>
              </div>
            </CardContent>
          </Card>

          {/* メタデータ */}
          {datasource.metadata && Object.keys(datasource.metadata).length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>メタデータ</CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="text-sm bg-muted p-3 rounded-lg overflow-auto max-h-64">
                  {JSON.stringify(datasource.metadata, null, 2)}
                </pre>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* 削除確認ダイアログ */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>データソースを削除しますか？</AlertDialogTitle>
            <AlertDialogDescription>
              この操作は取り消せません。データソースが削除されますが、タイルセットは削除されません。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteLoading}>キャンセル</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={deleteLoading}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  削除中...
                </>
              ) : (
                "削除する"
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </AdminLayout>
  );
}
