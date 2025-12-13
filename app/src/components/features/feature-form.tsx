"use client";

import { useState, useEffect, useCallback } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Loader2, Plus, Trash2 } from "lucide-react";
import { CoordinatePicker } from "@/components/map";
import type { Tileset, FeatureCreate, FeatureUpdate } from "@/lib/api";

// ジオメトリタイプ
type GeometryType = "Point" | "LineString" | "Polygon";

// フォームのスキーマ
const featureFormSchema = z.object({
  tileset_id: z.string().min(1, "タイルセットを選択してください"),
  layer_name: z.string().default("default"),
});

type FeatureFormValues = z.infer<typeof featureFormSchema>;

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
  const isEditMode = !!featureId;

  // フォームの設定
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<FeatureFormValues>({
    resolver: zodResolver(featureFormSchema),
    defaultValues: {
      tileset_id: initialData?.tileset_id || "",
      layer_name: initialData?.layer_name || "default",
    },
  });

  // ジオメトリタイプの状態
  const [geometryType, setGeometryType] = useState<GeometryType>(
    (initialData?.geometry?.type as GeometryType) || "Point"
  );

  // 座標の状態
  const [pointCoords, setPointCoords] = useState<[number, number] | null>(
    initialData?.geometry?.type === "Point"
      ? (initialData.geometry.coordinates as [number, number])
      : null
  );

  // LineStringの座標
  const [lineCoords, setLineCoords] = useState<[number, number][]>(
    initialData?.geometry?.type === "LineString"
      ? (initialData.geometry.coordinates as [number, number][])
      : []
  );

  // Polygonの座標（外周のみ）
  const [polygonCoords, setPolygonCoords] = useState<[number, number][]>(
    initialData?.geometry?.type === "Polygon"
      ? (initialData.geometry.coordinates[0] as [number, number][])
      : []
  );

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

  // LineStringの座標を追加
  const addLineCoord = () => {
    setLineCoords([...lineCoords, [139.7671, 35.6812]]);
  };

  // LineStringの座標を削除
  const removeLineCoord = (index: number) => {
    setLineCoords(lineCoords.filter((_, i) => i !== index));
  };

  // LineStringの座標を更新
  const updateLineCoord = (
    index: number,
    axis: "lng" | "lat",
    value: number
  ) => {
    const updated = [...lineCoords];
    if (axis === "lng") {
      updated[index] = [value, updated[index][1]];
    } else {
      updated[index] = [updated[index][0], value];
    }
    setLineCoords(updated);
  };

  // Polygonの座標を追加
  const addPolygonCoord = () => {
    setPolygonCoords([...polygonCoords, [139.7671, 35.6812]]);
  };

  // Polygonの座標を削除
  const removePolygonCoord = (index: number) => {
    setPolygonCoords(polygonCoords.filter((_, i) => i !== index));
  };

  // Polygonの座標を更新
  const updatePolygonCoord = (
    index: number,
    axis: "lng" | "lat",
    value: number
  ) => {
    const updated = [...polygonCoords];
    if (axis === "lng") {
      updated[index] = [value, updated[index][1]];
    } else {
      updated[index] = [updated[index][0], value];
    }
    setPolygonCoords(updated);
  };

  // ジオメトリを構築
  const buildGeometry = (): GeoJSON.Geometry | null => {
    switch (geometryType) {
      case "Point":
        if (!pointCoords) return null;
        return {
          type: "Point",
          coordinates: pointCoords,
        };
      case "LineString":
        if (lineCoords.length < 2) return null;
        return {
          type: "LineString",
          coordinates: lineCoords,
        };
      case "Polygon":
        if (polygonCoords.length < 3) return null;
        // ポリゴンは閉じた環である必要がある
        const ring = [...polygonCoords];
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

  // フォーム送信
  const handleFormSubmit = async (values: FeatureFormValues) => {
    const geometry = buildGeometry();
    if (!geometry) {
      alert("ジオメトリを入力してください");
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

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-6">
      {/* 基本情報 */}
      <Card>
        <CardHeader>
          <CardTitle>基本情報</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* タイルセット選択 */}
          <div className="space-y-2">
            <Label htmlFor="tileset_id">タイルセット *</Label>
            <Select
              value={watch("tileset_id")}
              onValueChange={(value) => setValue("tileset_id", value)}
              disabled={isEditMode}
            >
              <SelectTrigger>
                <SelectValue placeholder="タイルセットを選択" />
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
            <Label htmlFor="layer_name">レイヤー名</Label>
            <Input
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
          <CardTitle>ジオメトリ</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* ジオメトリタイプ選択 */}
          <div className="space-y-2">
            <Label>ジオメトリタイプ</Label>
            <Select
              value={geometryType}
              onValueChange={(value) => setGeometryType(value as GeometryType)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Point">Point（ポイント）</SelectItem>
                <SelectItem value="LineString">LineString（線）</SelectItem>
                <SelectItem value="Polygon">Polygon（ポリゴン）</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Point入力 */}
          {geometryType === "Point" && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>経度 (Longitude)</Label>
                  <Input
                    type="number"
                    step="any"
                    value={pointCoords?.[0] ?? ""}
                    onChange={(e) => {
                      const lng = parseFloat(e.target.value);
                      if (!isNaN(lng)) {
                        setPointCoords([lng, pointCoords?.[1] ?? 35.6812]);
                      }
                    }}
                    placeholder="139.7671"
                  />
                </div>
                <div className="space-y-2">
                  <Label>緯度 (Latitude)</Label>
                  <Input
                    type="number"
                    step="any"
                    value={pointCoords?.[1] ?? ""}
                    onChange={(e) => {
                      const lat = parseFloat(e.target.value);
                      if (!isNaN(lat)) {
                        setPointCoords([pointCoords?.[0] ?? 139.7671, lat]);
                      }
                    }}
                    placeholder="35.6812"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label>地図でクリックして座標を設定</Label>
                <CoordinatePicker
                  value={pointCoords}
                  onChange={setPointCoords}
                  height="300px"
                />
              </div>
            </div>
          )}

          {/* LineString入力 */}
          {geometryType === "LineString" && (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                2点以上の座標を入力してください
              </p>
              {lineCoords.map((coord, index) => (
                <div
                  key={index}
                  className="flex items-center gap-2 rounded-md border p-3"
                >
                  <span className="text-sm font-medium">#{index + 1}</span>
                  <Input
                    type="number"
                    step="any"
                    value={coord[0]}
                    onChange={(e) =>
                      updateLineCoord(index, "lng", parseFloat(e.target.value))
                    }
                    placeholder="経度"
                    className="flex-1"
                  />
                  <Input
                    type="number"
                    step="any"
                    value={coord[1]}
                    onChange={(e) =>
                      updateLineCoord(index, "lat", parseFloat(e.target.value))
                    }
                    placeholder="緯度"
                    className="flex-1"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => removeLineCoord(index)}
                    disabled={lineCoords.length <= 2}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
              <Button
                type="button"
                variant="outline"
                onClick={addLineCoord}
                className="w-full"
              >
                <Plus className="mr-2 h-4 w-4" />
                座標を追加
              </Button>
            </div>
          )}

          {/* Polygon入力 */}
          {geometryType === "Polygon" && (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                3点以上の座標を入力してください（自動的に閉じられます）
              </p>
              {polygonCoords.map((coord, index) => (
                <div
                  key={index}
                  className="flex items-center gap-2 rounded-md border p-3"
                >
                  <span className="text-sm font-medium">#{index + 1}</span>
                  <Input
                    type="number"
                    step="any"
                    value={coord[0]}
                    onChange={(e) =>
                      updatePolygonCoord(
                        index,
                        "lng",
                        parseFloat(e.target.value)
                      )
                    }
                    placeholder="経度"
                    className="flex-1"
                  />
                  <Input
                    type="number"
                    step="any"
                    value={coord[1]}
                    onChange={(e) =>
                      updatePolygonCoord(
                        index,
                        "lat",
                        parseFloat(e.target.value)
                      )
                    }
                    placeholder="緯度"
                    className="flex-1"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => removePolygonCoord(index)}
                    disabled={polygonCoords.length <= 3}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
              <Button
                type="button"
                variant="outline"
                onClick={addPolygonCoord}
                className="w-full"
              >
                <Plus className="mr-2 h-4 w-4" />
                座標を追加
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* プロパティ */}
      <Card>
        <CardHeader>
          <CardTitle>プロパティ（属性）</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            フィーチャーに付加する属性情報を入力してください
          </p>
          {properties.map((prop, index) => (
            <div key={index} className="flex items-center gap-2">
              <Input
                placeholder="キー"
                value={prop.key}
                onChange={(e) => updateProperty(index, "key", e.target.value)}
                className="flex-1"
              />
              <Input
                placeholder="値"
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
            type="button"
            variant="outline"
            onClick={addProperty}
            className="w-full"
          >
            <Plus className="mr-2 h-4 w-4" />
            プロパティを追加
          </Button>
        </CardContent>
      </Card>

      {/* アクションボタン */}
      <div className="flex justify-end gap-4">
        {onCancel && (
          <Button type="button" variant="outline" onClick={onCancel}>
            キャンセル
          </Button>
        )}
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {isEditMode ? "更新" : "作成"}
        </Button>
      </div>
    </form>
  );
}
