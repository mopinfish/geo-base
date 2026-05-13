"use client";

import { useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { Loader2, Plus, Trash2, MapPin, ChevronDown, ChevronUp } from "lucide-react";
import { GeometryEditor } from "@/components/map";
import type { Tileset, FeatureCreate, FeatureUpdate } from "@/lib/api";

// ジオメトリタイプ
type GeometryType = "Point" | "LineString" | "Polygon";

// フォームのスキーマ（t を受け取ってエラーメッセージを国際化）
const createFeatureFormSchema = (t: (key: string) => string) =>
  z.object({
    tileset_id: z.string().min(1, t("zod_tileset_required")),
    layer_name: z.string().min(1, t("zod_layer_required")),
  });

type FeatureFormValues = z.infer<ReturnType<typeof createFeatureFormSchema>>;

interface PropertyItem {
  key: string;
  value: string;
}

export interface FeatureFormProps {
  /** 編集モードの場合、既存のフィーチャーID */
  featureId?: string;
  /** 初期値（編集時） */
  initialData?: {
    tileset_id: string;
    layer_name: string;
    properties: Record<string, unknown>;
    geometry: GeoJSON.Geometry;
  };
  /** 利用可能なタイルセット一覧 */
  tilesets: Tileset[];
  /** 送信時のハンドラー */
  onSubmit: (data: FeatureCreate | FeatureUpdate) => Promise<void>;
  /** キャンセル時のハンドラー */
  onCancel?: () => void;
  /** 送信中かどうか */
  isSubmitting?: boolean;
}

/**
 * フィーチャー作成・編集フォーム
 */
export function FeatureForm({
  featureId,
  initialData,
  tilesets,
  onSubmit,
  onCancel,
  isSubmitting = false,
}: FeatureFormProps) {
  const t = useTranslations("features.form");
  const isEditMode = !!featureId;

  // フォームの設定
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<FeatureFormValues>({
    resolver: zodResolver(createFeatureFormSchema(t)),
    defaultValues: {
      tileset_id: initialData?.tileset_id || "",
      layer_name: initialData?.layer_name || "default",
    },
  });

  // ジオメトリタイプの状態
  const [geometryType, setGeometryType] = useState<GeometryType>(
    (initialData?.geometry?.type as GeometryType) || "Point"
  );

  // 座標の状態（統一形式）
  const [coordinates, setCoordinates] = useState<[number, number][] | [number, number] | null>(() => {
    if (!initialData?.geometry) return null;
    
    switch (initialData.geometry.type) {
      case "Point":
        return initialData.geometry.coordinates as [number, number];
      case "LineString":
        return initialData.geometry.coordinates as [number, number][];
      case "Polygon":
        return initialData.geometry.coordinates[0] as [number, number][];
      default:
        return null;
    }
  });

  // プロパティの状態
  const [properties, setProperties] = useState<PropertyItem[]>(() => {
    if (initialData?.properties) {
      return Object.entries(initialData.properties).map(([key, value]) => ({
        key,
        value: typeof value === "string" ? value : JSON.stringify(value),
      }));
    }
    return [];
  });

  // 座標入力の展開状態
  const [showCoordInputs, setShowCoordInputs] = useState(false);

  // ジオメトリ入力モード: "map" (既存の MapLibre GeometryEditor) /
  // "geojson" (テキストで GeoJSON 文字列を直接入れる)。既定は "map" で
  // 既存ユーザー体験を変えない。
  const [inputMode, setInputMode] = useState<"map" | "geojson">("map");
  const [geojsonText, setGeojsonText] = useState<string>(() => {
    if (!initialData?.geometry) return "";
    try {
      return JSON.stringify(initialData.geometry, null, 2);
    } catch {
      return "";
    }
  });
  const [geojsonError, setGeojsonError] = useState<string | null>(null);

  // GeoJSON 文字列を既存の geometryType / coordinates state に流し込む。
  // 簡易バリデーションのみで、座標の数値検査は既存の isGeometryValid に委ねる。
  //
  // 空文字 / parse 失敗 / 形式違反のときは coordinates を null にして
  // isGeometryValid を false に倒す。これをしないと、一度有効な GeoJSON を
  // 入れて空に戻したり破壊したりしても古い geometry state が残って submit
  // できてしまう (Copilot PR #122 指摘)。
  const applyGeojsonText = (text: string) => {
    setGeojsonText(text);
    if (!text.trim()) {
      setGeojsonError(null);
      setCoordinates(null);
      return;
    }
    let parsed: unknown;
    try {
      parsed = JSON.parse(text);
    } catch {
      setGeojsonError(t("zod_geojson_not_json"));
      setCoordinates(null);
      return;
    }
    if (!parsed || typeof parsed !== "object") {
      setGeojsonError(t("zod_geojson_not_object"));
      setCoordinates(null);
      return;
    }
    const obj = parsed as { type?: unknown; coordinates?: unknown };
    if (typeof obj.type !== "string" || !Array.isArray(obj.coordinates)) {
      setGeojsonError(t("zod_geojson_missing_fields"));
      setCoordinates(null);
      return;
    }
    if (obj.type !== "Point" && obj.type !== "LineString" && obj.type !== "Polygon") {
      setGeojsonError(t("zod_geojson_unsupported_type"));
      setCoordinates(null);
      return;
    }
    // 各 [number, number] の検査。長さ 2 + 両方 finite な number。
    // 型アサーションだけ通すと文字列座標などが素通りして
    // isGeometryValid (配列長のみで判定) を欺ける (Copilot PR #122 round 4 指摘)。
    const isNumPair = (v: unknown): v is [number, number] =>
      Array.isArray(v) &&
      v.length === 2 &&
      typeof v[0] === "number" &&
      Number.isFinite(v[0]) &&
      typeof v[1] === "number" &&
      Number.isFinite(v[1]);

    // 既存の geometryType / coordinates 形式に変換 (Polygon は外環のみ)。
    if (obj.type === "Point") {
      if (!isNumPair(obj.coordinates)) {
        setGeojsonError(t("zod_geojson_point_invalid"));
        setCoordinates(null);
        return;
      }
      setGeometryType("Point");
      setCoordinates(obj.coordinates);
    } else if (obj.type === "LineString") {
      const arr = obj.coordinates as unknown[];
      if (arr.length < 2 || !arr.every(isNumPair)) {
        setGeojsonError(t("zod_geojson_linestring_invalid"));
        setCoordinates(null);
        return;
      }
      setGeometryType("LineString");
      setCoordinates(arr as [number, number][]);
    } else {
      // Polygon: coordinates = [outerRing, ...holes] の外環だけ拾う。
      const outer = (obj.coordinates as unknown[])[0];
      if (!Array.isArray(outer) || outer.length < 3 || !outer.every(isNumPair)) {
        setGeojsonError(t("zod_geojson_polygon_invalid"));
        setCoordinates(null);
        return;
      }
      setGeometryType("Polygon");
      setCoordinates(outer as [number, number][]);
    }
    setGeojsonError(null);
  };

  // プロパティを追加
  const addProperty = () => {
    setProperties([...properties, { key: "", value: "" }]);
  };

  // プロパティを削除
  const removeProperty = (index: number) => {
    setProperties(properties.filter((_, i) => i !== index));
  };

  // プロパティを更新
  const updateProperty = (
    index: number,
    field: "key" | "value",
    value: string
  ) => {
    const updated = [...properties];
    updated[index][field] = value;
    setProperties(updated);
  };

  // ジオメトリタイプが変更されたとき
  const handleGeometryTypeChange = (newType: GeometryType) => {
    setGeometryType(newType);
    // 座標をリセット
    setCoordinates(null);
  };

  // 座標が変更されたとき
  const handleCoordinatesChange = useCallback((newCoords: [number, number][] | [number, number] | null) => {
    setCoordinates(newCoords);
  }, []);

  // ジオメトリを構築
  const buildGeometry = (): GeoJSON.Geometry | null => {
    if (!coordinates) return null;

    switch (geometryType) {
      case "Point":
        if (!Array.isArray(coordinates) || typeof coordinates[0] !== "number") return null;
        return {
          type: "Point",
          coordinates: coordinates as [number, number],
        };
      case "LineString":
        if (!Array.isArray(coordinates) || coordinates.length < 2) return null;
        return {
          type: "LineString",
          coordinates: coordinates as [number, number][],
        };
      case "Polygon":
        if (!Array.isArray(coordinates) || coordinates.length < 3) return null;
        // ポリゴンは閉じた環である必要がある
        const ring = [...(coordinates as [number, number][])];
        if (
          ring[0][0] !== ring[ring.length - 1][0] ||
          ring[0][1] !== ring[ring.length - 1][1]
        ) {
          ring.push(ring[0]);
        }
        return {
          type: "Polygon",
          coordinates: [ring],
        };
      default:
        return null;
    }
  };

  // プロパティをオブジェクトに変換
  const buildProperties = (): Record<string, unknown> => {
    const result: Record<string, unknown> = {};
    properties.forEach(({ key, value }) => {
      if (key.trim()) {
        // JSONとしてパースを試みる
        try {
          result[key.trim()] = JSON.parse(value);
        } catch {
          result[key.trim()] = value;
        }
      }
    });
    return result;
  };

  // 座標を配列形式で取得（表示用）
  const getCoordinatesArray = (): [number, number][] => {
    if (!coordinates) return [];
    if (geometryType === "Point") {
      return Array.isArray(coordinates) && typeof coordinates[0] === "number"
        ? [coordinates as [number, number]]
        : [];
    }
    return coordinates as [number, number][];
  };

  // 座標を手動で更新
  const updateCoordinate = (index: number, axis: "lng" | "lat", value: number) => {
    const coordsArray = getCoordinatesArray();
    if (index >= coordsArray.length) return;

    const newCoords = [...coordsArray];
    if (axis === "lng") {
      newCoords[index] = [value, newCoords[index][1]];
    } else {
      newCoords[index] = [newCoords[index][0], value];
    }

    if (geometryType === "Point") {
      setCoordinates(newCoords[0]);
    } else {
      setCoordinates(newCoords);
    }
  };

  // 座標を手動で追加
  const addCoordinate = () => {
    const coordsArray = getCoordinatesArray();
    const lastCoord = coordsArray.length > 0 ? coordsArray[coordsArray.length - 1] : [139.7671, 35.6812];
    const newCoord: [number, number] = [lastCoord[0] + 0.001, lastCoord[1] + 0.001];
    
    if (geometryType === "Point") {
      setCoordinates(newCoord);
    } else {
      setCoordinates([...coordsArray, newCoord]);
    }
  };

  // 座標を手動で削除
  const removeCoordinate = (index: number) => {
    const coordsArray = getCoordinatesArray();
    if (geometryType === "Point") {
      setCoordinates(null);
    } else {
      const newCoords = coordsArray.filter((_, i) => i !== index);
      setCoordinates(newCoords.length > 0 ? newCoords : null);
    }
  };

  // フォーム送信
  const handleFormSubmit = async (values: FeatureFormValues) => {
    const geometry = buildGeometry();
    
    if (!geometry) {
      alert(t("alert_no_geometry"));
      return;
    }

    const props = buildProperties();

    if (isEditMode) {
      // 更新
      const updateData: FeatureUpdate = {
        layer_name: values.layer_name,
        properties: props,
        geometry,
      };
      await onSubmit(updateData);
    } else {
      // 新規作成
      const createData: FeatureCreate = {
        tileset_id: values.tileset_id,
        layer_name: values.layer_name,
        properties: props,
        geometry,
      };
      await onSubmit(createData);
    }
  };

  const coordsArray = getCoordinatesArray();
  const minPointsRequired = geometryType === "Point" ? 1 : geometryType === "LineString" ? 2 : 3;
  const isGeometryValid = coordsArray.length >= minPointsRequired;

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-6">
      {/* 基本情報 */}
      <Card>
        <CardHeader>
          <CardTitle>{t("section_basic_info")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* タイルセット選択 */}
          <div className="space-y-2">
            <Label htmlFor="tileset_id">{t("tileset_label")}</Label>
            <Select
              value={watch("tileset_id")}
              onValueChange={(value) => setValue("tileset_id", value)}
              disabled={isEditMode}
            >
              <SelectTrigger data-testid="feature-form-tileset">
                <SelectValue placeholder={t("tileset_placeholder")} />
              </SelectTrigger>
              <SelectContent>
                {tilesets.map((tileset) => (
                  <SelectItem key={tileset.id} value={tileset.id}>
                    {tileset.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.tileset_id && (
              <p className="text-sm text-destructive">
                {errors.tileset_id.message}
              </p>
            )}
          </div>

          {/* レイヤー名 */}
          <div className="space-y-2">
            <Label htmlFor="layer_name">{t("layer_label")}</Label>
            <Input
              data-testid="feature-form-layer-name"
              id="layer_name"
              placeholder="default"
              {...register("layer_name")}
            />
          </div>
        </CardContent>
      </Card>

      {/* ジオメトリ */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MapPin className="h-5 w-5" />
            {t("section_geometry")}
          </CardTitle>
          <CardDescription>
            {t("geometry_description")}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* ジオメトリタイプ選択 */}
          <div className="space-y-2">
            <Label>{t("geometry_type_label")}</Label>
            <Select
              value={geometryType}
              onValueChange={(value) => handleGeometryTypeChange(value as GeometryType)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Point">{t("geometry_type_point")}</SelectItem>
                <SelectItem value="LineString">{t("geometry_type_linestring")}</SelectItem>
                <SelectItem value="Polygon">{t("geometry_type_polygon")}</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* ジオメトリステータス */}
          <div className="flex items-center gap-2">
            <Badge variant={isGeometryValid ? "default" : "secondary"}>
              {t("geometry_status_count", { count: coordsArray.length })}
            </Badge>
            {!isGeometryValid && (
              <span className="text-sm text-muted-foreground">
                {t("geometry_status_min_points", { min_points: minPointsRequired })}
              </span>
            )}
          </div>

          {/* 入力モード切替: マップ描画 or GeoJSON 直接入力 */}
          <Tabs
            value={inputMode}
            onValueChange={(v) => setInputMode(v as "map" | "geojson")}
          >
            <TabsList>
              <TabsTrigger value="map" data-testid="feature-form-mode-map">
                {t("tab_draw_map")}
              </TabsTrigger>
              <TabsTrigger value="geojson" data-testid="feature-form-mode-geojson">
                {t("tab_geojson_input")}
              </TabsTrigger>
            </TabsList>

            <TabsContent value="map" className="space-y-4">
              {/* 地図エディタ */}
              <GeometryEditor
                geometryType={geometryType}
                coordinates={coordinates}
                onChange={handleCoordinatesChange}
                height="400px"
              />

              {/* 座標入力フィールド（折りたたみ可能） */}
              <div className="border rounded-md">
                <button
                  type="button"
                  className="w-full flex items-center justify-between p-3 text-sm font-medium hover:bg-muted/50"
                  onClick={() => setShowCoordInputs(!showCoordInputs)}
                >
                  <span>{t("coord_edit_label")}</span>
                  {showCoordInputs ? (
                    <ChevronUp className="h-4 w-4" />
                  ) : (
                    <ChevronDown className="h-4 w-4" />
                  )}
                </button>

                {showCoordInputs && (
                  <div className="p-3 border-t space-y-3">
                    {coordsArray.map((coord, index) => (
                      <div
                        key={index}
                        className="flex items-center gap-2 rounded-md border p-2"
                      >
                        <span className="text-sm font-medium w-8">#{index + 1}</span>
                        <div className="flex-1 grid grid-cols-2 gap-2">
                          <div>
                            <Label className="text-xs">{t("coord_lng")}</Label>
                            <Input
                              type="number"
                              step="any"
                              value={coord[0]}
                              onChange={(e) =>
                                updateCoordinate(index, "lng", parseFloat(e.target.value))
                              }
                              placeholder={t("coord_lng")}
                              className="h-8"
                            />
                          </div>
                          <div>
                            <Label className="text-xs">{t("coord_lat")}</Label>
                            <Input
                              type="number"
                              step="any"
                              value={coord[1]}
                              onChange={(e) =>
                                updateCoordinate(index, "lat", parseFloat(e.target.value))
                              }
                              placeholder={t("coord_lat")}
                              className="h-8"
                            />
                          </div>
                        </div>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          onClick={() => removeCoordinate(index)}
                          disabled={geometryType !== "Point" && coordsArray.length <= 1}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}

                    {geometryType !== "Point" && (
                      <Button
                        type="button"
                        variant="outline"
                        onClick={addCoordinate}
                        className="w-full"
                      >
                        <Plus className="mr-2 h-4 w-4" />
                        {t("coord_add_button")}
                      </Button>
                    )}
                  </div>
                )}
              </div>
            </TabsContent>

            <TabsContent value="geojson" className="space-y-2">
              <Label htmlFor="feature-form-geometry-text">
                {t("geojson_label")}
              </Label>
              <Textarea
                id="feature-form-geometry-text"
                data-testid="feature-form-geometry-text"
                value={geojsonText}
                onChange={(e) => applyGeojsonText(e.target.value)}
                placeholder='{"type":"Point","coordinates":[139.7,35.6]}'
                rows={6}
                className="font-mono text-sm"
              />
              {geojsonError && (
                <p className="text-sm text-destructive">{geojsonError}</p>
              )}
              <p className="text-xs text-muted-foreground">
                {t("geojson_help")}
              </p>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* プロパティ */}
      <Card>
        <CardHeader>
          <CardTitle>{t("section_properties")}</CardTitle>
          <CardDescription>
            {t("properties_description")}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {properties.map((prop, index) => (
            <div key={index} className="flex items-center gap-2" data-testid="feature-form-property-row">
              <Input
                data-testid="feature-form-property-key"
                placeholder={t("property_key_placeholder")}
                value={prop.key}
                onChange={(e) => updateProperty(index, "key", e.target.value)}
                className="flex-1"
              />
              <Input
                data-testid="feature-form-property-value"
                placeholder={t("property_value_placeholder")}
                value={prop.value}
                onChange={(e) => updateProperty(index, "value", e.target.value)}
                className="flex-1"
              />
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => removeProperty(index)}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          ))}
          <Button
            data-testid="feature-form-property-add"
            type="button"
            variant="outline"
            onClick={addProperty}
            className="w-full"
          >
            <Plus className="mr-2 h-4 w-4" />
            {t("add_property_button")}
          </Button>
        </CardContent>
      </Card>

      {/* アクションボタン */}
      <div className="flex justify-end gap-4">
        {onCancel && (
          <Button type="button" variant="outline" onClick={onCancel}>
            {t("cancel")}
          </Button>
        )}
        <Button
          data-testid="feature-form-submit"
          type="submit"
          disabled={
            isSubmitting ||
            !isGeometryValid ||
            (inputMode === "geojson" &&
              (geojsonError !== null || !geojsonText.trim()))
          }
        >
          {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {isEditMode ? t("submit_edit") : t("submit_create")}
        </Button>
      </div>
    </form>
  );
}
