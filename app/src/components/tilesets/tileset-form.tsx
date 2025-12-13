"use client";

import { useState } from "react";
import Link from "next/link";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
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
import type { Tileset, TilesetCreate, TilesetUpdate } from "@/lib/api";
import { ArrowLeft, Save, Loader2 } from "lucide-react";

interface TilesetFormProps {
  mode: "create" | "edit";
  initialData?: Tileset;
  onSubmit: (data: TilesetCreate | TilesetUpdate) => Promise<void>;
  isSubmitting?: boolean;
  error?: string | null;
}

/**
 * bounds/centerを安全に文字列に変換
 */
const coordinatesToString = (value: unknown): string => {
  if (!value) return "";
  
  // すでに文字列の場合はそのまま返す
  if (typeof value === "string") {
    return value;
  }
  
  // 配列の場合はjoinする
  if (Array.isArray(value)) {
    return value.join(", ");
  }
  
  return "";
};

export function TilesetForm({
  mode,
  initialData,
  onSubmit,
  isSubmitting = false,
  error,
}: TilesetFormProps) {
  const [name, setName] = useState(initialData?.name || "");
  const [description, setDescription] = useState(initialData?.description || "");
  const [type, setType] = useState<"vector" | "raster" | "pmtiles">(
    initialData?.type || "vector"
  );
  const [format, setFormat] = useState<"pbf" | "png" | "webp" | "jpg" | "geojson">(
    initialData?.format || "pbf"
  );
  const [minZoom, setMinZoom] = useState(initialData?.min_zoom?.toString() || "0");
  const [maxZoom, setMaxZoom] = useState(initialData?.max_zoom?.toString() || "22");
  const [isPublic, setIsPublic] = useState(initialData?.is_public ?? true);
  const [attribution, setAttribution] = useState(initialData?.attribution || "");
  const [boundsStr, setBoundsStr] = useState(
    coordinatesToString(initialData?.bounds)
  );
  const [centerStr, setCenterStr] = useState(
    coordinatesToString(initialData?.center)
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // バウンディングボックスをパース
    let bounds: number[] | undefined;
    if (boundsStr.trim()) {
      const parts = boundsStr.split(",").map((s) => parseFloat(s.trim()));
      if (parts.length === 4 && parts.every((n) => !isNaN(n))) {
        bounds = parts;
      }
    }

    // 中心座標をパース
    let center: number[] | undefined;
    if (centerStr.trim()) {
      const parts = centerStr.split(",").map((s) => parseFloat(s.trim()));
      if (parts.length >= 2 && parts.every((n) => !isNaN(n))) {
        center = parts;
      }
    }

    if (mode === "create") {
      const data: TilesetCreate = {
        name,
        description: description || undefined,
        type,
        format,
        min_zoom: parseInt(minZoom, 10),
        max_zoom: parseInt(maxZoom, 10),
        is_public: isPublic,
        attribution: attribution || undefined,
        bounds,
        center,
      };
      await onSubmit(data);
    } else {
      const data: TilesetUpdate = {
        name,
        description: description || undefined,
        min_zoom: parseInt(minZoom, 10),
        max_zoom: parseInt(maxZoom, 10),
        is_public: isPublic,
        attribution: attribution || undefined,
        bounds,
        center,
      };
      await onSubmit(data);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <Card>
        <CardHeader>
          <CardTitle>
            {mode === "create" ? "タイルセット情報" : "タイルセット編集"}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* エラー表示 */}
          {error && (
            <div className="rounded-md bg-destructive/15 p-3 text-sm text-destructive">
              {error}
            </div>
          )}

          {/* 名前 */}
          <div className="space-y-2">
            <Label htmlFor="name">名前 *</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="タイルセット名"
              required
            />
          </div>

          {/* 説明 */}
          <div className="space-y-2">
            <Label htmlFor="description">説明</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="タイルセットの説明（任意）"
              rows={3}
            />
          </div>

          {/* タイプとフォーマット（新規作成時のみ） */}
          {mode === "create" && (
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="type">タイプ *</Label>
                <Select
                  value={type}
                  onValueChange={(v) => setType(v as typeof type)}
                >
                  <SelectTrigger id="type">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="vector">ベクタ</SelectItem>
                    <SelectItem value="raster">ラスタ</SelectItem>
                    <SelectItem value="pmtiles">PMTiles</SelectItem>
                  </SelectContent>
                </Select>
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
                    <SelectItem value="pbf">PBF (Protocol Buffers)</SelectItem>
                    <SelectItem value="png">PNG</SelectItem>
                    <SelectItem value="webp">WebP</SelectItem>
                    <SelectItem value="jpg">JPEG</SelectItem>
                    <SelectItem value="geojson">GeoJSON</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}

          {/* ズームレベル */}
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="minZoom">最小ズーム</Label>
              <Input
                id="minZoom"
                type="number"
                min="0"
                max="22"
                value={minZoom}
                onChange={(e) => setMinZoom(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="maxZoom">最大ズーム</Label>
              <Input
                id="maxZoom"
                type="number"
                min="0"
                max="22"
                value={maxZoom}
                onChange={(e) => setMaxZoom(e.target.value)}
              />
            </div>
          </div>

          {/* バウンディングボックス */}
          <div className="space-y-2">
            <Label htmlFor="bounds">バウンディングボックス</Label>
            <Input
              id="bounds"
              value={boundsStr}
              onChange={(e) => setBoundsStr(e.target.value)}
              placeholder="west, south, east, north（例: 139.5, 35.5, 140.0, 36.0）"
            />
            <p className="text-xs text-muted-foreground">
              カンマ区切りで西経、南緯、東経、北緯の順に入力
            </p>
          </div>

          {/* 中心座標 */}
          <div className="space-y-2">
            <Label htmlFor="center">中心座標</Label>
            <Input
              id="center"
              value={centerStr}
              onChange={(e) => setCenterStr(e.target.value)}
              placeholder="longitude, latitude（例: 139.7671, 35.6812）"
            />
            <p className="text-xs text-muted-foreground">
              カンマ区切りで経度、緯度の順に入力（オプションでズームレベルも指定可）
            </p>
          </div>

          {/* 帰属表示 */}
          <div className="space-y-2">
            <Label htmlFor="attribution">帰属表示（Attribution）</Label>
            <Input
              id="attribution"
              value={attribution}
              onChange={(e) => setAttribution(e.target.value)}
              placeholder="© OpenStreetMap contributors"
            />
            <p className="text-xs text-muted-foreground">
              地図上に表示するデータ提供者のクレジット表記
            </p>
          </div>

          {/* 公開設定 */}
          <div className="flex items-center justify-between rounded-lg border p-4">
            <div className="space-y-0.5">
              <Label htmlFor="isPublic">公開設定</Label>
              <p className="text-sm text-muted-foreground">
                公開すると誰でもアクセスできます
              </p>
            </div>
            <Switch
              id="isPublic"
              checked={isPublic}
              onCheckedChange={setIsPublic}
            />
          </div>
        </CardContent>
        <CardFooter className="flex justify-between">
          <Link href="/tilesets">
            <Button type="button" variant="outline">
              <ArrowLeft className="mr-2 h-4 w-4" />
              キャンセル
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
        </CardFooter>
      </Card>
    </form>
  );
}
