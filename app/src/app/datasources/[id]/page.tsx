"use client";

import { useEffect, useState } from "react";
import { useTranslations, useLocale } from "next-intl";
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
import { isOpenableUrl, type Datasource, type DatasourceTestResult } from "@/lib/api";
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
  const t = useTranslations("datasources.detail");
  const locale = useLocale();
  const dateLocale = locale === "ja" ? "ja-JP" : "en-US";
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
      setError(err instanceof Error ? err.message : t("error_fetch"));
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
        message: err instanceof Error ? err.message : t("test_error"),
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
      setError(err instanceof Error ? err.message : t("error_delete"));
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
      case "s3":
        return "S3 互換 (Fly Tigris / AWS S3 / R2)";
      case "http":
        return "HTTP";
      // 旧 'supabase' 値は Issue #72 で廃止済み (PR #88)。既存 DB レコードに残っていた場合の表示用 fallback として残置。
      case "supabase":
        return "Supabase Storage (legacy)";
      default:
        return provider;
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString(dateLocale, {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  };

  const formatBounds = (bounds: number[] | Record<string, number> | undefined) => {
    if (!bounds) return t("not_set");
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
              {t("back")}
            </Link>
          </Button>
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              {error || t("not_found")}
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
              {t("back")}
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
              <p className="text-muted-foreground">{t("subtitle")}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              onClick={handleTestConnection}
              disabled={testLoading}
              data-testid="datasource-test-connection-button"
            >
              {testLoading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Play className="mr-2 h-4 w-4" />
              )}
              {t("test_button")}
            </Button>
            <Button
              variant="destructive"
              onClick={() => setDeleteDialogOpen(true)}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              {t("delete_button")}
            </Button>
          </div>
        </div>

        {/* 接続テスト結果 */}
        {testResult && (
          <Alert
            variant={testResult.status === "success" ? "default" : "destructive"}
            className={
              testResult.status === "success"
                ? "border-green-500 bg-green-50"
                : ""
            }
            data-testid="datasource-test-connection-result"
            data-status={testResult.status}
          >
            {testResult.status === "success" ? (
              <CheckCircle2 className="h-4 w-4 text-green-600" />
            ) : (
              <XCircle className="h-4 w-4" />
            )}
            <AlertDescription
              className={testResult.status === "success" ? "text-green-600" : ""}
            >
              {testResult.status === "success"
                ? t("test_success")
                : testResult.message || t("test_failure_default")}
            </AlertDescription>
          </Alert>
        )}

        <div className="grid gap-6 lg:grid-cols-2">
          {/* 基本情報 */}
          <Card>
            <CardHeader>
              <CardTitle>{t("section_basic_info")}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">{t("field_id")}</p>
                  <p className="font-mono text-sm">{datasource.id}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">{t("field_type")}</p>
                  <Badge className="uppercase mt-1">{datasource.type}</Badge>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">{t("field_storage")}</p>
                  <Badge variant="outline" className="mt-1">
                    {getStorageProviderLabel(datasource.storage_provider)}
                  </Badge>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">{t("field_visibility")}</p>
                  <Badge
                    variant={datasource.is_public ? "default" : "secondary"}
                    className="mt-1"
                  >
                    {datasource.is_public ? (
                      <>
                        <Globe className="mr-1 h-3 w-3" />
                        {t("visibility_public")}
                      </>
                    ) : (
                      <>
                        <Lock className="mr-1 h-3 w-3" />
                        {t("visibility_private")}
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
                {t("section_tileset")}
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
                {t("tileset_id_label")} {datasource.tileset_id}
              </p>
            </CardContent>
          </Card>

          {/* URL情報 */}
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <LinkIcon className="h-5 w-5" />
                {t("section_url")}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2 p-3 bg-muted rounded-lg">
                <code className="flex-1 text-sm break-all">{datasource.url}</code>
                {isOpenableUrl(datasource.url) && (
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
                )}
              </div>
              {!isOpenableUrl(datasource.url) && (
                <p className="mt-2 text-xs text-muted-foreground">
                  {t("url_internal_note", { type: datasource.url.startsWith("s3://") ? t("url_type_s3") : t("url_type_non_http") })}
                </p>
              )}
            </CardContent>
          </Card>

          {/* 詳細情報（PMTiles固有） */}
          {datasource.type === "pmtiles" && (
            <Card>
              <CardHeader>
                <CardTitle>{t("section_pmtiles")}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">{t("field_tile_type")}</p>
                    <p className="font-medium">{datasource.tile_type || t("not_fetched")}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">{t("field_compression")}</p>
                    <p className="font-medium">{datasource.compression || t("not_fetched")}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">{t("field_min_zoom")}</p>
                    <p className="font-medium">
                      {datasource.min_zoom !== undefined ? datasource.min_zoom : t("not_set")}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">{t("field_max_zoom")}</p>
                    <p className="font-medium">
                      {datasource.max_zoom !== undefined ? datasource.max_zoom : t("not_set")}
                    </p>
                  </div>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">{t("field_bbox")}</p>
                  <p className="font-mono text-sm mt-1">
                    {formatBounds(datasource.bounds)}
                  </p>
                </div>
                {datasource.layers && Array.isArray(datasource.layers) && (
                  <div>
                    <p className="text-sm text-muted-foreground">{t("field_layer_count")}</p>
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
                <CardTitle>{t("section_cog")}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">{t("field_band_count")}</p>
                    <p className="font-medium">
                      {datasource.band_count !== undefined ? datasource.band_count : t("not_fetched")}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">{t("field_native_crs")}</p>
                    <p className="font-medium">{datasource.native_crs || t("not_fetched")}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">{t("field_min_zoom_rec")}</p>
                    <p className="font-medium">
                      {datasource.min_zoom !== undefined ? datasource.min_zoom : t("not_set")}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">{t("field_max_zoom_rec")}</p>
                    <p className="font-medium">
                      {datasource.max_zoom !== undefined ? datasource.max_zoom : t("not_set")}
                    </p>
                  </div>
                </div>
                {datasource.band_descriptions && (
                  <div>
                    <p className="text-sm text-muted-foreground">{t("field_band_desc")}</p>
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
                {t("section_datetime")}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p className="text-sm text-muted-foreground">{t("field_created_at")}</p>
                <p className="font-medium">{formatDate(datasource.created_at)}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">{t("field_updated_at")}</p>
                <p className="font-medium">{formatDate(datasource.updated_at)}</p>
              </div>
            </CardContent>
          </Card>

          {/* メタデータ */}
          {datasource.metadata && Object.keys(datasource.metadata).length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>{t("section_metadata")}</CardTitle>
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
            <AlertDialogTitle>{t("delete_title")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("delete_description")}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteLoading}>{t("cancel")}</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={deleteLoading}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {t("deleting")}
                </>
              ) : (
                t("delete_confirm")
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </AdminLayout>
  );
}
