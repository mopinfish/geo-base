"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2, Save, ArrowLeft, AlertCircle } from "lucide-react";
import Link from "next/link";
import type { Tileset, TilesetCreate, TilesetUpdate } from "@/lib/api";

interface TilesetFormProps {
  mode: "create" | "edit";
  initialData?: Tileset;
  onSubmit: (data: TilesetCreate | TilesetUpdate) => Promise<void>;
  isSubmitting?: boolean;
  error?: string | null;
}

export function TilesetForm({
  mode,
  initialData,
  onSubmit,
  isSubmitting = false,
  error,
}: TilesetFormProps) {
  const router = useRouter();
  
  // フォーム状態
  const [name, setName] = useState(initialData?.name || "");
  const [description, setDescription] = useState(initialData?.description || "");
  const [type, setType] = useState<"vector" | "raster" | "pmtiles">(initialData?.type || "vector");
  const [format, setFormat] = useState<"pbf" | "png" | "webp" | "jpg" | "geojson">(
    initialData?.format || "pbf"
  );
  const [minZoom, setMinZoom] = useState(initialData?.min_zoom?.toString() || "0");
  const [maxZoom, setMaxZoom] = useState(initialData?.max_zoom?.toString() || "22");
  const [isPublic, setIsPublic] = useState(initialData?.is_public ?? false);
  const [attribution, setAttribution] = useState(initialData?.attribution || "");
  const [boundsStr, setBoundsStr] = useState(
    initialData?.bounds ? initialData.bounds.join(", ") : ""
  );
  const [centerStr, setCenterStr] = useState(
    initialData?.center ? initialData.center.join(", ") : ""
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // バウンディングボックスのパース
    let bounds: number[] | undefined;
    if (boundsStr.trim()) {
      bounds = boundsStr.split(",").map((s) => parseFloat(s.trim()));
      if (bounds.length !== 4 || bounds.some(isNaN)) {
        bounds = undefined;
      }
    }

    // センターのパース
    let center: number[] | undefined;
    if (centerStr.trim()) {
      center = centerStr.split(",").map((s) => parseFloat(s.trim()));
      if (center.length < 2 || center.length > 3 || center.some(isNaN)) {
        center = undefined;
      }
    }

    if (mode === "create") {
      const data: TilesetCreate = {
        name,
        description: description || undefined,
        type,
        format,
        min_zoom: minZoom ? parseInt(minZoom) : 0,
        max_zoom: maxZoom ? parseInt(maxZoom) : 22,
        bounds,
        center,
        attribution: attribution || undefined,
        is_public: isPublic,
      };
      await onSubmit(data);
    } else {
      const data: TilesetUpdate = {
        name,
        description: description || undefined,
        min_zoom: minZoom ? parseInt(minZoom) : undefined,
        max_zoom: maxZoom ? parseInt(maxZoom) : undefined,
        bounds,
        center,
        attribution: attribution || undefined,
        is_public: isPublic,
      };
      await onSubmit(data);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* エラー表示 */}
      {error && (
        <div className="flex items-center gap-2 rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* 基本情報 */}
      <Card>
        <CardHeader>
          <CardTitle>基本情報</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">名前 *</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="タイルセット名"
              required
              disabled={isSubmitting}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">説明</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="タイルセットの説明（任意）"
              rows={3}
              disabled={isSubmitting}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="attribution">帰属表示（Attribution）</Label>
            <Input
              id="attribution"
              value={attribution}
              onChange={(e) => setAttribution(e.target.value)}
              placeholder="© OpenStreetMap contributors"
              disabled={isSubmitting}
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="is_public">公開設定</Label>
              <p className="text-xs text-muted-foreground">
                公開すると誰でもアクセスできます
              </p>
            </div>
            <Switch
              id="is_public"
              checked={isPublic}
              onCheckedChange={setIsPublic}
              disabled={isSubmitting}
            />
          </div>
        </CardContent>
      </Card>

      {/* タイル設定（新規作成時のみ） */}
      {mode === "create" && (
        <Card>
          <CardHeader>
            <CardTitle>タイル設定</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="type">タイプ *</Label>
                <Select value={type} onValueChange={(v) => setType(v as "vector" | "raster" | "pmtiles")}>
                  <SelectTrigger id="type">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="vector">ベクタ</SelectItem>
                    <SelectItem value="raster">ラスタ</SelectItem>
                    <SelectItem value="pmtiles">PMTiles</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  PostGISからの動的生成はベクタを選択
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="format">フォーマット *</Label>
                <Select
                  value={format}
                  onValueChange={(v) => setFormat(v as typeof format)}
                >
                  <SelectTrigger id="format">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="pbf">PBF (Mapbox Vector Tiles)</SelectItem>
                    <SelectItem value="geojson">GeoJSON</SelectItem>
                    <SelectItem value="png">PNG</SelectItem>
                    <SelectItem value="webp">WebP</SelectItem>
                    <SelectItem value="jpg">JPEG</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  ベクタタイルには PBF を推奨
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* ズーム・範囲設定 */}
      <Card>
        <CardHeader>
          <CardTitle>ズーム・範囲設定</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="min_zoom">最小ズーム</Label>
              <Input
                id="min_zoom"
                type="number"
                min="0"
                max="22"
                value={minZoom}
                onChange={(e) => setMinZoom(e.target.value)}
                disabled={isSubmitting}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="max_zoom">最大ズーム</Label>
              <Input
                id="max_zoom"
                type="number"
                min="0"
                max="22"
                value={maxZoom}
                onChange={(e) => setMaxZoom(e.target.value)}
                disabled={isSubmitting}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="bounds">バウンディングボックス</Label>
            <Input
              id="bounds"
              value={boundsStr}
              onChange={(e) => setBoundsStr(e.target.value)}
              placeholder="west, south, east, north (例: 139.5, 35.5, 140.0, 36.0)"
              disabled={isSubmitting}
            />
            <p className="text-xs text-muted-foreground">
              カンマ区切りで4つの値を入力（西経度, 南緯度, 東経度, 北緯度）
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="center">中心座標</Label>
            <Input
              id="center"
              value={centerStr}
              onChange={(e) => setCenterStr(e.target.value)}
              placeholder="longitude, latitude (例: 139.7, 35.7)"
              disabled={isSubmitting}
            />
            <p className="text-xs text-muted-foreground">
              カンマ区切りで2〜3つの値を入力（経度, 緯度, [ズーム]）
            </p>
          </div>
        </CardContent>
      </Card>

      {/* アクションボタン */}
      <div className="flex items-center justify-between">
        <Link href="/tilesets">
          <Button type="button" variant="outline">
            <ArrowLeft className="mr-2 h-4 w-4" />
            戻る
          </Button>
        </Link>
        <Button type="submit" disabled={isSubmitting || !name}>
          {isSubmitting ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              保存中...
            </>
          ) : (
            <>
              <Save className="mr-2 h-4 w-4" />
              {mode === "create" ? "作成" : "保存"}
            </>
          )}
        </Button>
      </div>
    </form>
  );
}
