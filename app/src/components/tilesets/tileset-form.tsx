"use client";

import { ArrowLeft, Loader2, Save } from "lucide-react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import type { Tileset, TilesetCreate, TilesetUpdate } from "@/lib/api";

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
  const t = useTranslations("tilesets.form");

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
            {mode === "create" ? t("title_create") : t("title_edit")}
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
            <Label htmlFor="name">{t("label_name")}</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={t("placeholder_name")}
              required
              data-testid="tileset-form-name"
            />
          </div>

          {/* 説明 */}
          <div className="space-y-2">
            <Label htmlFor="description">{t("label_description")}</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t("placeholder_description")}
              rows={3}
              data-testid="tileset-form-description"
            />
          </div>

          {/* タイプとフォーマット（新規作成時のみ） */}
          {mode === "create" && (
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="type">{t("label_type")}</Label>
                <Select
                  value={type}
                  onValueChange={(v) => setType(v as typeof type)}
                >
                  <SelectTrigger id="type" data-testid="tileset-form-type">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="vector">{t("type_vector")}</SelectItem>
                    <SelectItem value="raster">{t("type_raster")}</SelectItem>
                    <SelectItem value="pmtiles">{t("type_pmtiles")}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="format">{t("label_format")}</Label>
                <Select
                  value={format}
                  onValueChange={(v) => setFormat(v as typeof format)}
                >
                  <SelectTrigger id="format">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="pbf">{t("format_pbf")}</SelectItem>
                    <SelectItem value="png">{t("format_png")}</SelectItem>
                    <SelectItem value="webp">{t("format_webp")}</SelectItem>
                    <SelectItem value="jpg">{t("format_jpg")}</SelectItem>
                    <SelectItem value="geojson">{t("format_geojson")}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}

          {/* ズームレベル */}
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="minZoom">{t("label_min_zoom")}</Label>
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
              <Label htmlFor="maxZoom">{t("label_max_zoom")}</Label>
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
            <Label htmlFor="bounds">{t("label_bounds")}</Label>
            <Input
              id="bounds"
              value={boundsStr}
              onChange={(e) => setBoundsStr(e.target.value)}
              placeholder={t("placeholder_bounds")}
            />
            <p className="text-xs text-muted-foreground">{t("help_bounds")}</p>
          </div>

          {/* 中心座標 */}
          <div className="space-y-2">
            <Label htmlFor="center">{t("label_center")}</Label>
            <Input
              id="center"
              value={centerStr}
              onChange={(e) => setCenterStr(e.target.value)}
              placeholder={t("placeholder_center")}
            />
            <p className="text-xs text-muted-foreground">{t("help_center")}</p>
          </div>

          {/* 帰属表示 */}
          <div className="space-y-2">
            <Label htmlFor="attribution">{t("label_attribution")}</Label>
            <Input
              id="attribution"
              value={attribution}
              onChange={(e) => setAttribution(e.target.value)}
              placeholder={t("placeholder_attribution")}
            />
            <p className="text-xs text-muted-foreground">{t("help_attribution")}</p>
          </div>

          {/* 公開設定 */}
          <div className="flex items-center justify-between rounded-lg border p-4">
            <div className="space-y-0.5">
              <Label htmlFor="isPublic">{t("label_is_public")}</Label>
              <p className="text-sm text-muted-foreground">{t("help_is_public")}</p>
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
              {t("cancel")}
            </Button>
          </Link>
          <Button type="submit" disabled={isSubmitting || !name} data-testid="tileset-form-submit">
            {isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {t("submitting")}
              </>
            ) : (
              <>
                <Save className="mr-2 h-4 w-4" />
                {mode === "create" ? t("submit_create") : t("submit_edit")}
              </>
            )}
          </Button>
        </CardFooter>
      </Card>
    </form>
  );
}
