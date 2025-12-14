"use client";

import { useState, useCallback } from "react";
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
import { Loader2, Plus, Trash2, MapPin, ChevronDown, ChevronUp } from "lucide-react";
import { GeometryEditor } from "@/components/map";
import type { Tileset, FeatureCreate, FeatureUpdate } from "@/lib/api";

// ジオメトリタイプ
type GeometryType = "Point" | "LineString" | "Polygon";

// フォームのスキーマ
const featureFormSchema = z.object({
  tileset_id: z.string().min(1, "タイルセットを選択してください"),
  layer_name: z.string().min(1, "レイヤー名を入力してください"),
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

  const coordsArray = getCoordinatesArray();
  const minPointsRequired = geometryType === "Point" ? 1 : geometryType === "LineString" ? 2 : 3;
  const isGeometryValid = coordsArray.length >= minPointsRequired;

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
          <CardTitle className="flex items-center gap-2">
            <MapPin className="h-5 w-5" />
            ジオメトリ
          </CardTitle>
          <CardDescription>
            地図をクリックして座標を設定、またはマーカーをドラッグして移動できます
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* ジオメトリタイプ選択 */}
          <div className="space-y-2">
            <Label>ジオメトリタイプ</Label>
            <Select
              value={geometryType}
              onValueChange={(value) => handleGeometryTypeChange(value as GeometryType)}
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

          {/* ジオメトリステータス */}
          <div className="flex items-center gap-2">
            <Badge variant={isGeometryValid ? "default" : "secondary"}>
              {coordsArray.length}点
            </Badge>
            {!isGeometryValid && (
              <span className="text-sm text-muted-foreground">
                ({minPointsRequired}点以上必要)
              </span>
            )}
          </div>

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
              <span>座標を数値で編集</span>
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
                        <Label className="text-xs">経度</Label>
                        <Input
                          type="number"
                          step="any"
                          value={coord[0]}
                          onChange={(e) =>
                            updateCoordinate(index, "lng", parseFloat(e.target.value))
                          }
                          placeholder="経度"
                          className="h-8"
                        />
                      </div>
                      <div>
                        <Label className="text-xs">緯度</Label>
                        <Input
                          type="number"
                          step="any"
                          value={coord[1]}
                          onChange={(e) =>
                            updateCoordinate(index, "lat", parseFloat(e.target.value))
                          }
                          placeholder="緯度"
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
                    座標を追加
                  </Button>
                )}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* プロパティ */}
      <Card>
        <CardHeader>
          <CardTitle>プロパティ（属性）</CardTitle>
          <CardDescription>
            フィーチャーに付加する属性情報を入力してください
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
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
        <Button type="submit" disabled={isSubmitting || !isGeometryValid}>
          {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {isEditMode ? "更新" : "作成"}
        </Button>
      </div>
    </form>
  );
}
