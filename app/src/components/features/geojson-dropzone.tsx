"use client";

import { useState, useCallback, useRef } from "react";
import { useTranslations } from "next-intl";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Upload, FileJson, Check } from "lucide-react";

// GeoJSON型定義
export interface GeoJSONFeature {
  type: "Feature";
  geometry: GeoJSON.Geometry;
  properties: Record<string, unknown> | null;
}

export interface GeoJSONFeatureCollection {
  type: "FeatureCollection";
  features: GeoJSONFeature[];
}

export interface ParsedGeoJSON {
  data: GeoJSONFeatureCollection;
  fileName: string;
  fileSize: number;
  featureCount: number;
  geometryTypes: Record<string, number>;
}

interface GeoJSONDropzoneProps {
  onFileLoaded: (result: ParsedGeoJSON) => void;
  onError: (error: string) => void;
  disabled?: boolean;
}

export function GeoJSONDropzone({ onFileLoaded, onError, disabled }: GeoJSONDropzoneProps) {
  const t = useTranslations("features.geojsonDropzone");
  const [isDragging, setIsDragging] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [loadedFile, setLoadedFile] = useState<ParsedGeoJSON | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const parseGeoJSON = useCallback((content: string, fileName: string, fileSize: number): ParsedGeoJSON | null => {
    try {
      const parsed = JSON.parse(content);

      // GeoJSON形式の検証
      if (parsed.type === "FeatureCollection" && Array.isArray(parsed.features)) {
        // FeatureCollection形式
        const geometryTypes: Record<string, number> = {};
        
        for (const feature of parsed.features) {
          if (feature.type !== "Feature" || !feature.geometry) {
            throw new Error(t("error_invalid_feature"));
          }
          const geoType = feature.geometry.type;
          geometryTypes[geoType] = (geometryTypes[geoType] || 0) + 1;
        }

        return {
          data: parsed as GeoJSONFeatureCollection,
          fileName,
          fileSize,
          featureCount: parsed.features.length,
          geometryTypes,
        };
      } else if (parsed.type === "Feature" && parsed.geometry) {
        // 単一Feature形式 -> FeatureCollectionに変換
        const featureCollection: GeoJSONFeatureCollection = {
          type: "FeatureCollection",
          features: [parsed as GeoJSONFeature],
        };
        
        return {
          data: featureCollection,
          fileName,
          fileSize,
          featureCount: 1,
          geometryTypes: { [parsed.geometry.type]: 1 },
        };
      } else {
        throw new Error(t("error_invalid_format"));
      }
    } catch (err) {
      if (err instanceof SyntaxError) {
        onError(t("error_parse_failed"));
      } else if (err instanceof Error) {
        onError(err.message);
      } else {
        onError(t("error_parse_error"));
      }
      return null;
    }
  }, [onError, t]);

  const handleFile = useCallback(async (file: File) => {
    // ファイルタイプの検証
    if (!file.name.endsWith(".geojson") && !file.name.endsWith(".json")) {
      onError(t("error_wrong_extension"));
      return;
    }

    // ファイルサイズの検証（10MB制限）
    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
      onError(t("error_file_too_large"));
      return;
    }

    setIsLoading(true);

    try {
      const content = await file.text();
      const result = parseGeoJSON(content, file.name, file.size);
      
      if (result) {
        if (result.featureCount === 0) {
          onError(t("error_no_features"));
          setLoadedFile(null);
        } else {
          setLoadedFile(result);
          onFileLoaded(result);
        }
      } else {
        setLoadedFile(null);
      }
    } catch {
      onError(t("error_read_failed"));
      setLoadedFile(null);
    } finally {
      setIsLoading(false);
    }
  }, [parseGeoJSON, onFileLoaded, onError, t]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!disabled) {
      setIsDragging(true);
    }
  }, [disabled]);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (disabled) return;

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFile(files[0]);
    }
  }, [disabled, handleFile]);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFile(files[0]);
    }
  }, [handleFile]);

  const handleClick = () => {
    if (!disabled && fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const handleReset = () => {
    setLoadedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="space-y-4">
      {/* ドロップゾーン */}
      <Card
        className={`cursor-pointer transition-colors ${
          isDragging
            ? "border-primary border-2 bg-primary/5"
            : loadedFile
            ? "border-green-500 bg-green-500/5"
            : "border-dashed border-2 hover:border-primary/50"
        } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
        onClick={handleClick}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <CardContent className="flex flex-col items-center justify-center py-10 gap-4">
          {isLoading ? (
            <>
              <div className="h-12 w-12 animate-spin rounded-full border-4 border-primary border-t-transparent" />
              <p className="text-sm text-muted-foreground">{t("parsing")}</p>
            </>
          ) : loadedFile ? (
            <>
              <div className="flex items-center gap-2 text-green-600">
                <Check className="h-8 w-8" />
                <FileJson className="h-8 w-8" />
              </div>
              <div className="text-center">
                <p className="font-medium">{loadedFile.fileName}</p>
                <p className="text-sm text-muted-foreground">
                  {formatFileSize(loadedFile.fileSize)}
                </p>
              </div>
            </>
          ) : (
            <>
              <Upload className="h-12 w-12 text-muted-foreground" />
              <div className="text-center">
                <p className="font-medium">{t("drag")}</p>
                <p className="text-sm text-muted-foreground">
                  {t("click")}
                </p>
              </div>
              <p className="text-xs text-muted-foreground">
                {t("format_hint")}
              </p>
            </>
          )}
        </CardContent>
      </Card>

      <input
        ref={fileInputRef}
        type="file"
        accept=".geojson,.json,application/geo+json,application/json"
        onChange={handleFileSelect}
        className="hidden"
        disabled={disabled}
        data-testid="import-file-input"
      />

      {/* ファイル情報 */}
      {loadedFile && (
        <Card>
          <CardContent className="pt-6">
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <h3 className="font-medium">{t("file_info_title")}</h3>
                <Button variant="ghost" size="sm" onClick={handleReset}>
                  {t("change_file")}
                </Button>
              </div>

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-muted-foreground">{t("feature_count_label")}</span>
                  <span className="ml-2 font-medium">{t("feature_count_value", { count: loadedFile.featureCount })}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">{t("file_size_label")}</span>
                  <span className="ml-2 font-medium">{formatFileSize(loadedFile.fileSize)}</span>
                </div>
              </div>

              <div>
                <span className="text-sm text-muted-foreground">{t("geometry_type_label")}</span>
                <div className="flex flex-wrap gap-2 mt-1">
                  {Object.entries(loadedFile.geometryTypes).map(([type, count]) => (
                    <span
                      key={type}
                      className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-secondary"
                    >
                      {type}: {count}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
