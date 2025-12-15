"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { TileJSON, Tileset } from "@/lib/api";

export interface TilesetMapPreviewProps {
  /** タイルセット情報 */
  tileset: Tileset;
  /** TileJSON（オプション） */
  tileJSON?: TileJSON | null;
  /** 地図の高さ */
  height?: string;
  /** ベクターレイヤーの塗りつぶし色 */
  fillColor?: string;
  /** ベクターレイヤーの線色 */
  lineColor?: string;
  /** ベクターレイヤーのポイント色 */
  pointColor?: string;
  /** ベースマップを非表示にするか */
  hideBaseMap?: boolean;
  /** 初期表示時にboundsに自動フィットするか（デフォルト: true） */
  autoFitBounds?: boolean;
  /** 強制リフレッシュ用のキー（変更するとタイルを再読み込み） */
  refreshKey?: number | string;
}

// レイヤーごとの色パレット
const LAYER_COLORS = [
  { fill: "#3b82f6", line: "#2563eb", point: "#22c55e" }, // blue/green
  { fill: "#f59e0b", line: "#d97706", point: "#ef4444" }, // amber/red
  { fill: "#8b5cf6", line: "#7c3aed", point: "#ec4899" }, // violet/pink
  { fill: "#06b6d4", line: "#0891b2", point: "#84cc16" }, // cyan/lime
  { fill: "#f43f5e", line: "#e11d48", point: "#6366f1" }, // rose/indigo
];

/**
 * boundsが有効な値かどうかをチェック
 * デフォルト値（全世界）や無効な値を除外
 */
function isValidBounds(bounds: number[] | null | undefined): bounds is number[] {
  if (!bounds || !Array.isArray(bounds) || bounds.length !== 4) {
    return false;
  }
  
  const [west, south, east, north] = bounds;
  
  // NaNや無効な値をチェック
  if (bounds.some(v => typeof v !== 'number' || isNaN(v))) {
    return false;
  }
  
  // 全世界を覆うデフォルト値は除外（自動フィットには使わない）
  const isWorldDefault = 
    (west <= -170 && east >= 170) ||
    (south <= -80 && north >= 80);
  
  if (isWorldDefault) {
    return false;
  }
  
  // 範囲が妥当かチェック
  if (west >= east || south >= north) {
    return false;
  }
  
  return true;
}

/**
 * 文字列またはnumber[]からnumber[]を取得
 */
function parseBounds(value: number[] | string | null | undefined): number[] | null {
  if (!value) return null;
  
  if (Array.isArray(value)) {
    return value;
  }
  
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value);
      if (Array.isArray(parsed)) {
        return parsed;
      }
    } catch {
      const parts = value.split(',').map(Number);
      if (parts.length === 4 && !parts.some(isNaN)) {
        return parts;
      }
    }
  }
  
  return null;
}

/**
 * 文字列またはnumber[]からcenterを取得
 */
function parseCenter(value: number[] | string | null | undefined): number[] | null {
  if (!value) return null;
  
  if (Array.isArray(value)) {
    return value;
  }
  
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value);
      if (Array.isArray(parsed)) {
        return parsed;
      }
    } catch {
      const parts = value.split(',').map(Number);
      if (parts.length >= 2 && !parts.some(isNaN)) {
        return parts;
      }
    }
  }
  
  return null;
}

// TileJSON with vector_layers の型定義
interface VectorLayer {
  id: string;
  fields?: Record<string, string>;
  minzoom?: number;
  maxzoom?: number;
  description?: string;
}

interface TileJSONWithLayers extends TileJSON {
  vector_layers?: VectorLayer[];
}

/**
 * タイルセットのプレビュー表示用マップコンポーネント
 *
 * タイルセットのタイプに応じて適切な表示を行う：
 * - vector: PostGISベースのMVTタイルを表示（レイヤー別スタイリング対応）
 * - pmtiles: PMTilesファイルからタイルを表示
 * - raster: COGベースのラスタータイルを表示
 */
export function TilesetMapPreview({
  tileset,
  tileJSON,
  height = "400px",
  fillColor = "#3b82f6",
  lineColor = "#2563eb",
  pointColor = "#22c55e",
  hideBaseMap = false,
  autoFitBounds = true,
  refreshKey,
}: TilesetMapPreviewProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasFittedBounds, setHasFittedBounds] = useState(false);

  // 有効なboundsを取得
  const getValidBounds = useCallback((): number[] | null => {
    const tileJSONBounds = parseBounds(tileJSON?.bounds);
    if (isValidBounds(tileJSONBounds)) {
      return tileJSONBounds;
    }
    
    const tilesetBounds = parseBounds(tileset.bounds as number[] | string | undefined);
    if (isValidBounds(tilesetBounds)) {
      return tilesetBounds;
    }
    
    return null;
  }, [tileset, tileJSON]);

  // 初期の中心座標とズームを計算
  const getInitialView = useCallback(() => {
    const tileJSONCenter = parseCenter(tileJSON?.center);
    if (tileJSONCenter && tileJSONCenter.length >= 2) {
      return {
        center: [tileJSONCenter[0], tileJSONCenter[1]] as [number, number],
        zoom: tileJSONCenter[2] ?? 10,
      };
    }

    const tilesetCenter = parseCenter(tileset.center as number[] | string | undefined);
    if (tilesetCenter && tilesetCenter.length >= 2) {
      return {
        center: [tilesetCenter[0], tilesetCenter[1]] as [number, number],
        zoom: tilesetCenter[2] ?? 10,
      };
    }

    const bounds = getValidBounds();
    if (bounds) {
      const [west, south, east, north] = bounds;
      return {
        center: [(west + east) / 2, (south + north) / 2] as [number, number],
        zoom: 8,
      };
    }

    return {
      center: [139.7671, 35.6812] as [number, number],
      zoom: 5,
    };
  }, [tileset, tileJSON, getValidBounds]);

  /**
   * vector_layersを取得
   * TileJSONから取得できない場合はデフォルト値を返す
   */
  const getVectorLayers = useCallback((): VectorLayer[] => {
    const tileJSONWithLayers = tileJSON as TileJSONWithLayers | null;
    
    if (tileJSONWithLayers?.vector_layers && tileJSONWithLayers.vector_layers.length > 0) {
      return tileJSONWithLayers.vector_layers;
    }
    
    // デフォルト：単一レイヤー
    return [{ id: "default" }];
  }, [tileJSON]);

  /**
   * タイルURLを生成
   * 
   * vectorタイプの場合：
   * - layerパラメータなしの場合、全フィーチャーが "features" レイヤーにまとめられる
   * - layerパラメータありの場合、そのレイヤー名でMVTが生成される
   * 
   * マッププレビューでは全フィーチャーを表示するため、layerパラメータなしで取得し
   * source-layer: "features" を使用する
   */
  const getTileUrl = useCallback((cacheBuster?: number | string) => {
    const apiBaseUrl =
      process.env.NEXT_PUBLIC_API_URL || "https://geo-base-puce.vercel.app";

    const bustParam = cacheBuster ? `&_t=${cacheBuster}` : "";

    if (tileJSON?.tiles && tileJSON.tiles.length > 0) {
      const baseUrl = tileJSON.tiles[0];
      const separator = baseUrl.includes("?") ? "&" : "?";
      return cacheBuster ? `${baseUrl}${separator}_t=${cacheBuster}` : baseUrl;
    }

    switch (tileset.type) {
      case "vector":
        // layerパラメータなし → 全フィーチャーが "features" レイヤーに
        return `${apiBaseUrl}/api/tiles/features/{z}/{x}/{y}.pbf?tileset_id=${tileset.id}${bustParam}`;
      case "pmtiles":
        return `${apiBaseUrl}/api/tiles/pmtiles/${tileset.id}/{z}/{x}/{y}.pbf${cacheBuster ? `?_t=${cacheBuster}` : ""}`;
      case "raster":
        return `${apiBaseUrl}/api/tiles/raster/${tileset.id}/{z}/{x}/{y}.${tileset.format || "png"}${cacheBuster ? `?_t=${cacheBuster}` : ""}`;
      default:
        return null;
    }
  }, [tileset, tileJSON]);

  /**
   * ソースレイヤー名を決定
   * 
   * vectorタイプ:
   *   - TileJSONのtiles URLにlayerパラメータが含まれるため、
   *     MVT内のレイヤー名はvector_layers[0].idになる
   *   - TileJSONがない場合は "features" にフォールバック
   * 
   * pmtiles:
   *   - TileJSONのvector_layersから取得（PMTilesに含まれるレイヤー名）
   */
  const getSourceLayerName = useCallback((): string => {
    // TileJSONのvector_layersから取得を試みる
    const vectorLayers = getVectorLayers();
    
    if (tileset.type === "vector") {
      // vectorタイプ: TileJSONのvector_layers[0].idを使用
      // TileJSONのtiles URLにlayerパラメータが含まれるため、
      // MVTレイヤー名はそのlayer名になる
      if (vectorLayers.length > 0 && vectorLayers[0].id) {
        return vectorLayers[0].id;
      }
      // フォールバック: TileJSONがない場合は "features"
      return "features";
    }
    
    if (tileset.type === "pmtiles") {
      if (vectorLayers.length > 0 && vectorLayers[0].id) {
        return vectorLayers[0].id;
      }
    }
    
    return "default";
  }, [tileset.type, getVectorLayers]);

  // boundsにフィット
  const fitToBounds = useCallback(() => {
    if (!map.current || !isLoaded) return;

    const bounds = getValidBounds();
    if (bounds) {
      map.current.fitBounds(
        [
          [bounds[0], bounds[1]],
          [bounds[2], bounds[3]],
        ],
        { padding: 50, duration: 500 }
      );
    }
  }, [getValidBounds, isLoaded]);

  // 地図の初期化
  useEffect(() => {
    if (map.current) {
      map.current.remove();
      map.current = null;
      setIsLoaded(false);
      setHasFittedBounds(false);
    }

    if (!mapContainer.current) return;

    const tileUrl = getTileUrl(refreshKey);
    if (!tileUrl) {
      setError("タイルURLが設定されていません");
      return;
    }

    const { center, zoom } = getInitialView();

    try {
      const baseStyle: maplibregl.StyleSpecification = {
        version: 8,
        sources: {},
        layers: [],
      };

      if (!hideBaseMap) {
        baseStyle.sources.osm = {
          type: "raster",
          tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
          tileSize: 256,
          attribution:
            '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        };
        baseStyle.layers.push({
          id: "osm",
          type: "raster",
          source: "osm",
        });
      } else {
        baseStyle.layers.push({
          id: "background",
          type: "background",
          paint: {
            "background-color": "#f0f0f0",
          },
        });
      }

      map.current = new maplibregl.Map({
        container: mapContainer.current,
        style: baseStyle,
        center: center,
        zoom: zoom,
        minZoom: tileJSON?.minzoom ?? tileset.min_zoom ?? 0,
        maxZoom: tileJSON?.maxzoom ?? tileset.max_zoom ?? 22,
      });

      map.current.addControl(new maplibregl.NavigationControl(), "top-right");
      map.current.addControl(new maplibregl.ScaleControl(), "bottom-left");

      map.current.on("load", () => {
        if (!map.current) return;

        if (tileset.type === "raster") {
          // ラスタータイル
          map.current.addSource("tileset", {
            type: "raster",
            tiles: [tileUrl],
            tileSize: 256,
            minzoom: tileJSON?.minzoom ?? tileset.min_zoom ?? 0,
            maxzoom: tileJSON?.maxzoom ?? tileset.max_zoom ?? 22,
          });

          map.current.addLayer({
            id: "tileset-raster",
            type: "raster",
            source: "tileset",
            paint: {
              "raster-opacity": 0.8,
            },
          });
        } else {
          // ベクタータイル（vector, pmtiles）
          map.current.addSource("tileset", {
            type: "vector",
            tiles: [tileUrl],
            minzoom: tileJSON?.minzoom ?? tileset.min_zoom ?? 0,
            maxzoom: tileJSON?.maxzoom ?? tileset.max_zoom ?? 22,
          });

          // ソースレイヤー名を決定
          const sourceLayer = getSourceLayerName();
          
          // デバッグログ
          console.log(`[TilesetMapPreview] tileset.type: ${tileset.type}`);
          console.log(`[TilesetMapPreview] source-layer: "${sourceLayer}"`);
          console.log(`[TilesetMapPreview] tileUrl: ${tileUrl}`);

          // 使用する色（propsまたはデフォルト）
          const colors = {
            fill: fillColor,
            line: lineColor,
            point: pointColor,
          };

          // ポリゴンレイヤー
          map.current.addLayer({
            id: "tileset-polygon",
            type: "fill",
            source: "tileset",
            "source-layer": sourceLayer,
            filter: ["==", ["geometry-type"], "Polygon"],
            paint: {
              "fill-color": colors.fill,
              "fill-opacity": 0.4,
            },
          });

          // ポリゴンの境界線
          map.current.addLayer({
            id: "tileset-polygon-outline",
            type: "line",
            source: "tileset",
            "source-layer": sourceLayer,
            filter: ["==", ["geometry-type"], "Polygon"],
            paint: {
              "line-color": colors.line,
              "line-width": 1.5,
            },
          });

          // ラインレイヤー
          map.current.addLayer({
            id: "tileset-line",
            type: "line",
            source: "tileset",
            "source-layer": sourceLayer,
            filter: ["==", ["geometry-type"], "LineString"],
            paint: {
              "line-color": colors.line,
              "line-width": 2,
            },
          });

          // ポイントレイヤー
          map.current.addLayer({
            id: "tileset-point",
            type: "circle",
            source: "tileset",
            "source-layer": sourceLayer,
            filter: ["==", ["geometry-type"], "Point"],
            paint: {
              "circle-radius": 6,
              "circle-color": colors.point,
              "circle-stroke-width": 2,
              "circle-stroke-color": "#ffffff",
            },
          });

          // クリックでポップアップ表示
          map.current.on("click", "tileset-point", (e) => {
            if (!map.current || !e.features || e.features.length === 0) return;

            const feature = e.features[0];
            const props = feature.properties || {};

            let content = "<div class='p-2'>";
            
            // layer_nameがあれば表示
            if (props.layer_name) {
              content += `<span class='text-xs bg-gray-200 rounded px-1'>${props.layer_name}</span><br/>`;
            }
            
            if (props.name) {
              content += `<strong>${props.name}</strong><br/>`;
            }
            
            // その他のプロパティを表示（最大5件）
            const excludeKeys = ["name", "layer_name", "feature_id"];
            const keys = Object.keys(props).filter((k) => !excludeKeys.includes(k));
            keys.slice(0, 5).forEach((key) => {
              content += `<span class='text-sm text-gray-600'>${key}: ${props[key]}</span><br/>`;
            });
            content += "</div>";

            new maplibregl.Popup()
              .setLngLat(e.lngLat)
              .setHTML(content)
              .addTo(map.current!);
          });

          // ポイントにホバーでカーソル変更
          map.current.on("mouseenter", "tileset-point", () => {
            if (map.current) {
              map.current.getCanvas().style.cursor = "pointer";
            }
          });

          map.current.on("mouseleave", "tileset-point", () => {
            if (map.current) {
              map.current.getCanvas().style.cursor = "";
            }
          });
        }

        setIsLoaded(true);
        setError(null);
      });

      map.current.on("error", (e) => {
        console.error("Map error:", e);
        setError("地図の読み込みに失敗しました");
      });
    } catch (err) {
      console.error("Map initialization error:", err);
      setError(
        err instanceof Error ? err.message : "地図の初期化に失敗しました"
      );
    }

    return () => {
      if (map.current) {
        map.current.remove();
        map.current = null;
      }
    };
  }, [
    tileset,
    tileJSON,
    getTileUrl,
    getInitialView,
    getSourceLayerName,
    fillColor,
    lineColor,
    pointColor,
    hideBaseMap,
    refreshKey,
  ]);

  // 地図ロード後に自動的にboundsにフィット
  useEffect(() => {
    if (!isLoaded || !autoFitBounds || hasFittedBounds) return;

    const bounds = getValidBounds();
    if (bounds && map.current) {
      const timer = setTimeout(() => {
        if (map.current) {
          map.current.fitBounds(
            [
              [bounds[0], bounds[1]],
              [bounds[2], bounds[3]],
            ],
            { padding: 50, duration: 1000 }
          );
          setHasFittedBounds(true);
        }
      }, 100);

      return () => clearTimeout(timer);
    }
  }, [isLoaded, autoFitBounds, hasFittedBounds, getValidBounds]);

  if (error) {
    return (
      <div
        className="flex items-center justify-center rounded-md border bg-muted/50"
        style={{ height }}
      >
        <div className="text-center text-muted-foreground">
          <p className="text-sm">{error}</p>
          <p className="mt-1 text-xs">タイルの読み込みに失敗しました</p>
        </div>
      </div>
    );
  }

  const validBounds = getValidBounds();
  const hasBounds = validBounds !== null;
  const vectorLayers = getVectorLayers();

  return (
    <div className="relative">
      <div
        ref={mapContainer}
        className="w-full rounded-md border"
        style={{ height }}
      />

      {/* レイヤー情報（vectorタイプの場合） */}
      {isLoaded && tileset.type === "vector" && vectorLayers.length > 0 && (
        <div className="absolute top-2 left-2 bg-white/90 rounded px-2 py-1 text-xs shadow max-w-[200px]">
          <div className="font-medium mb-1">レイヤー:</div>
          {vectorLayers.map((layer, idx) => (
            <div key={layer.id} className="flex items-center gap-1">
              <span
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: LAYER_COLORS[idx % LAYER_COLORS.length].point }}
              />
              <span className="truncate">{layer.id}</span>
            </div>
          ))}
        </div>
      )}

      {/* コントロールボタン */}
      {isLoaded && (
        <div className="absolute bottom-4 right-4 flex gap-2">
          <button
            onClick={fitToBounds}
            disabled={!hasBounds}
            className={`rounded px-2 py-1 text-xs shadow ${
              hasBounds 
                ? "bg-white hover:bg-gray-100 cursor-pointer" 
                : "bg-gray-200 text-gray-400 cursor-not-allowed"
            }`}
            title={hasBounds ? "データ範囲にフィット" : "boundsが設定されていません"}
          >
            範囲にフィット
          </button>
        </div>
      )}

      {/* ローディング表示 */}
      {!isLoaded && !error && (
        <div
          className="absolute inset-0 flex items-center justify-center rounded-md bg-muted/50"
          style={{ height }}
        >
          <div className="text-center text-muted-foreground">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent mx-auto" />
            <p className="mt-2 text-sm">地図を読み込み中...</p>
          </div>
        </div>
      )}
    </div>
  );
}
