"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import maplibregl from "maplibre-gl";
import type { MapLayerMouseEvent } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { TileJSON, Tileset } from "@/lib/api";
import { Maximize2, X, Eye, EyeOff, Layers, Palette, SlidersHorizontal } from "lucide-react";

export interface TilesetMapPreviewProps {
  /** タイルセット情報 */
  tileset: Tileset;
  /** TileJSON（オプション） */
  tileJSON?: TileJSON | null;
  /** 地図の高さ */
  height?: string;
  /** ベースマップを非表示にするか */
  hideBaseMap?: boolean;
  /** 初期表示時にboundsに自動フィットするか（デフォルト: true） */
  autoFitBounds?: boolean;
  /** 強制リフレッシュ用のキー（変更するとタイルを再読み込み） */
  refreshKey?: number | string;
}

// レイヤーごとの色パレット（複数レイヤー対応）
const LAYER_COLORS = [
  { fill: "#3b82f6", line: "#2563eb", point: "#3b82f6" }, // blue
  { fill: "#22c55e", line: "#16a34a", point: "#22c55e" }, // green
  { fill: "#f59e0b", line: "#d97706", point: "#f59e0b" }, // amber
  { fill: "#ef4444", line: "#dc2626", point: "#ef4444" }, // red
  { fill: "#8b5cf6", line: "#7c3aed", point: "#8b5cf6" }, // violet
  { fill: "#ec4899", line: "#db2777", point: "#ec4899" }, // pink
  { fill: "#06b6d4", line: "#0891b2", point: "#06b6d4" }, // cyan
  { fill: "#84cc16", line: "#65a30d", point: "#84cc16" }, // lime
  { fill: "#f43f5e", line: "#e11d48", point: "#f43f5e" }, // rose
  { fill: "#6366f1", line: "#4f46e5", point: "#6366f1" }, // indigo
];

// ラスター用カラーマッププリセット
const COLORMAP_PRESETS = [
  { value: "", labelKey: "colormap_default" },
  { value: "viridis", labelKey: "colormap_viridis" },
  { value: "terrain", labelKey: "colormap_terrain" },
  { value: "ndvi", labelKey: "colormap_ndvi" },
  { value: "temperature", labelKey: "colormap_temperature" },
  { value: "precipitation", labelKey: "colormap_precipitation" },
  { value: "bathymetry", labelKey: "colormap_bathymetry" },
  { value: "grayscale", labelKey: "colormap_grayscale" },
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
 * - vector: PostGISベースのMVTタイルを表示（全レイヤー表示・レイヤー別スタイリング対応）
 * - pmtiles: PMTilesファイルからタイルを表示
 * - raster: COGベースのラスタータイルを表示（opacity調整・カラーマップ対応）
 */
export function TilesetMapPreview({
  tileset,
  tileJSON,
  height = "400px",
  hideBaseMap = false,
  autoFitBounds = true,
  refreshKey,
}: TilesetMapPreviewProps) {
  const t = useTranslations("tilesets.detail");
  const mapContainer = useRef<HTMLDivElement>(null);
  const fullscreenMapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const fullscreenMap = useRef<maplibregl.Map | null>(null);
  const tRef = useRef(t);
  const [isLoaded, setIsLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasFittedBounds, setHasFittedBounds] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [visibleLayers, setVisibleLayers] = useState<Set<string>>(new Set());
  
  // ラスター用の状態
  const [rasterOpacity, setRasterOpacity] = useState(0.9);
  const [colormap, setColormap] = useState("");
  const [showRasterControls, setShowRasterControls] = useState(false);

  useEffect(() => {
    tRef.current = t;
  }, [t]);

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
    return [{ id: "features" }];
  }, [tileJSON]);

  /**
   * タイルURLを生成
   */
  const getTileUrl = useCallback((cacheBuster?: number | string, colormapOverride?: string) => {
    const apiBaseUrl =
      process.env.NEXT_PUBLIC_API_URL || "https://geo-base-api.fly.dev";

    const bustParam = cacheBuster ? `_t=${cacheBuster}` : "";
    const currentColormap = colormapOverride !== undefined ? colormapOverride : colormap;

    switch (tileset.type) {
      case "vector":
        return `${apiBaseUrl}/api/tiles/features/{z}/{x}/{y}.pbf?tileset_id=${tileset.id}${bustParam ? `&${bustParam}` : ""}`;
      case "pmtiles":
        if (tileJSON?.tiles && tileJSON.tiles.length > 0) {
          const baseUrl = tileJSON.tiles[0];
          const separator = baseUrl.includes("?") ? "&" : "?";
          return cacheBuster ? `${baseUrl}${separator}${bustParam}` : baseUrl;
        }
        return `${apiBaseUrl}/api/tiles/pmtiles/${tileset.id}/{z}/{x}/{y}.pbf${bustParam ? `?${bustParam}` : ""}`;
      case "raster": {
        const params: string[] = [];
        if (currentColormap) {
          params.push(`colormap=${currentColormap}`);
        }
        if (bustParam) {
          params.push(bustParam);
        }
        const queryString = params.length > 0 ? `?${params.join("&")}` : "";
        
        if (tileJSON?.tiles && tileJSON.tiles.length > 0) {
          const baseUrl = tileJSON.tiles[0];
          const separator = baseUrl.includes("?") ? "&" : "?";
          const additionalParams = params.length > 0 ? `${separator}${params.join("&")}` : "";
          return `${baseUrl}${additionalParams}`;
        }
        return `${apiBaseUrl}/api/tiles/raster/${tileset.id}/{z}/{x}/{y}.${tileset.format || "png"}${queryString}`;
      }
      default:
        return null;
    }
  }, [tileset, tileJSON, colormap]);

  /**
   * レイヤーの表示/非表示をトグル
   */
  const toggleLayerVisibility = useCallback((layerId: string) => {
    setVisibleLayers(prev => {
      const newSet = new Set(prev);
      if (newSet.has(layerId)) {
        newSet.delete(layerId);
      } else {
        newSet.add(layerId);
      }
      return newSet;
    });

    const layerIds = [
      `tileset-polygon-${layerId}`,
      `tileset-polygon-outline-${layerId}`,
      `tileset-line-${layerId}`,
      `tileset-point-${layerId}`,
    ];

    const visibility = visibleLayers.has(layerId) ? "none" : "visible";

    if (map.current) {
      layerIds.forEach(id => {
        if (map.current?.getLayer(id)) {
          map.current.setLayoutProperty(id, "visibility", visibility);
        }
      });
    }

    if (fullscreenMap.current) {
      layerIds.forEach(id => {
        if (fullscreenMap.current?.getLayer(id)) {
          fullscreenMap.current.setLayoutProperty(id, "visibility", visibility);
        }
      });
    }
  }, [visibleLayers]);

  /**
   * 全レイヤーの表示/非表示を一括設定
   */
  const setAllLayersVisibility = useCallback((visible: boolean) => {
    const vectorLayers = getVectorLayers();
    const layerIdSet = new Set(vectorLayers.map(l => l.id));

    if (visible) {
      setVisibleLayers(layerIdSet);
    } else {
      setVisibleLayers(new Set());
    }

    vectorLayers.forEach(layer => {
      const layerIds = [
        `tileset-polygon-${layer.id}`,
        `tileset-polygon-outline-${layer.id}`,
        `tileset-line-${layer.id}`,
        `tileset-point-${layer.id}`,
      ];

      const visibility = visible ? "visible" : "none";

      if (map.current) {
        layerIds.forEach(id => {
          if (map.current?.getLayer(id)) {
            map.current.setLayoutProperty(id, "visibility", visibility);
          }
        });
      }

      if (fullscreenMap.current) {
        layerIds.forEach(id => {
          if (fullscreenMap.current?.getLayer(id)) {
            fullscreenMap.current.setLayoutProperty(id, "visibility", visibility);
          }
        });
      }
    });
  }, [getVectorLayers]);

  /**
   * ラスターopacityを更新
   */
  const updateRasterOpacity = useCallback((opacity: number) => {
    setRasterOpacity(opacity);
    
    if (map.current?.getLayer("tileset-raster")) {
      map.current.setPaintProperty("tileset-raster", "raster-opacity", opacity);
    }
    if (fullscreenMap.current?.getLayer("tileset-raster")) {
      fullscreenMap.current.setPaintProperty("tileset-raster", "raster-opacity", opacity);
    }
  }, []);

  // 再帰呼び出し (style ロード待ち) で TDZ を回避するため ref 経由で参照する
  const updateRasterSourceRef = useRef<
    ((mapInstance: maplibregl.Map, newColormap: string) => void) | null
  >(null);

  /**
   * ラスターソースを安全に更新（カラーマップ変更時）
   */
  const updateRasterSource = useCallback((mapInstance: maplibregl.Map, newColormap: string) => {
    // スタイルがロード済みかチェック
    if (!mapInstance.isStyleLoaded()) {
      console.log("Style not loaded yet, waiting...");
      mapInstance.once("idle", () => {
        updateRasterSourceRef.current?.(mapInstance, newColormap);
      });
      return;
    }

    const tileUrl = getTileUrl(refreshKey, newColormap);
    if (!tileUrl) return;

    try {
      // 既存のレイヤーとソースを削除
      if (mapInstance.getLayer("tileset-raster")) {
        mapInstance.removeLayer("tileset-raster");
      }
      if (mapInstance.getSource("tileset")) {
        mapInstance.removeSource("tileset");
      }

      // 新しいソースとレイヤーを追加
      mapInstance.addSource("tileset", {
        type: "raster",
        tiles: [tileUrl],
        tileSize: 256,
        minzoom: tileJSON?.minzoom ?? tileset.min_zoom ?? 0,
        maxzoom: tileJSON?.maxzoom ?? tileset.max_zoom ?? 22,
      });

      mapInstance.addLayer({
        id: "tileset-raster",
        type: "raster",
        source: "tileset",
        paint: {
          "raster-opacity": rasterOpacity,
        },
      });
    } catch (err) {
      console.error("Error updating raster source:", err);
    }
  }, [getTileUrl, tileJSON, tileset, rasterOpacity, refreshKey]);

  // ref を最新の callback に同期 (上記再帰呼び出し用)
  useEffect(() => {
    updateRasterSourceRef.current = updateRasterSource;
  }, [updateRasterSource]);

  /**
   * カラーマップ変更ハンドラ
   */
  const handleColormapChange = useCallback((newColormap: string) => {
    setColormap(newColormap);
    
    if (map.current) {
      updateRasterSource(map.current, newColormap);
    }
    
    if (fullscreenMap.current) {
      updateRasterSource(fullscreenMap.current, newColormap);
    }
  }, [updateRasterSource]);

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

  /**
   * 地図にレイヤーを追加する共通関数
   */
  const addMapLayers = useCallback((mapInstance: maplibregl.Map, tileUrl: string) => {
    if (tileset.type === "raster") {
      mapInstance.addSource("tileset", {
        type: "raster",
        tiles: [tileUrl],
        tileSize: 256,
        minzoom: tileJSON?.minzoom ?? tileset.min_zoom ?? 0,
        maxzoom: tileJSON?.maxzoom ?? tileset.max_zoom ?? 22,
      });

      mapInstance.addLayer({
        id: "tileset-raster",
        type: "raster",
        source: "tileset",
        paint: {
          "raster-opacity": rasterOpacity,
        },
      });
    } else {
      mapInstance.addSource("tileset", {
        type: "vector",
        tiles: [tileUrl],
        minzoom: tileJSON?.minzoom ?? tileset.min_zoom ?? 0,
        maxzoom: tileJSON?.maxzoom ?? tileset.max_zoom ?? 22,
      });

      const vectorLayers = getVectorLayers();
      
      console.log(`[TilesetMapPreview] tileset.type: ${tileset.type}`);
      console.log(`[TilesetMapPreview] tileUrl: ${tileUrl}`);
      console.log(`[TilesetMapPreview] vector_layers:`, vectorLayers.map(l => l.id));

      vectorLayers.forEach((layer, idx) => {
        const layerId = layer.id;
        const colors = LAYER_COLORS[idx % LAYER_COLORS.length];
        const sourceLayerName = layerId;

        const polygonFilter: maplibregl.FilterSpecification = ["==", ["geometry-type"], "Polygon"];
        const lineFilter: maplibregl.FilterSpecification = ["==", ["geometry-type"], "LineString"];
        const pointFilter: maplibregl.FilterSpecification = ["==", ["geometry-type"], "Point"];

        mapInstance.addLayer({
          id: `tileset-polygon-${layerId}`,
          type: "fill",
          source: "tileset",
          "source-layer": sourceLayerName,
          filter: polygonFilter,
          paint: {
            "fill-color": colors.fill,
            "fill-opacity": 0.4,
          },
        });

        mapInstance.addLayer({
          id: `tileset-polygon-outline-${layerId}`,
          type: "line",
          source: "tileset",
          "source-layer": sourceLayerName,
          filter: polygonFilter,
          paint: {
            "line-color": colors.line,
            "line-width": 1.5,
          },
        });

        mapInstance.addLayer({
          id: `tileset-line-${layerId}`,
          type: "line",
          source: "tileset",
          "source-layer": sourceLayerName,
          filter: lineFilter,
          paint: {
            "line-color": colors.line,
            "line-width": 2,
          },
        });

        mapInstance.addLayer({
          id: `tileset-point-${layerId}`,
          type: "circle",
          source: "tileset",
          "source-layer": sourceLayerName,
          filter: pointFilter,
          paint: {
            "circle-radius": 6,
            "circle-color": colors.point,
            "circle-stroke-width": 2,
            "circle-stroke-color": "#ffffff",
          },
        });
      });

      const handlePopupClick = (e: MapLayerMouseEvent) => {
        if (!e.features || e.features.length === 0) return;

        const feature = e.features[0];
        const props = feature.properties || {};

        const formatValue = (value: unknown): string => {
          if (value === null || value === undefined) return "-";
          const str = String(value);
          
          if (str.match(/^https?:\/\//)) {
            const displayUrl = str.length > 40 ? str.substring(0, 40) + "..." : str;
            return `<a href="${str}" target="_blank" rel="noopener noreferrer" class="text-blue-600 hover:underline">${displayUrl}</a>`;
          }
          
          if (str.length > 50) {
            return str.substring(0, 50) + "...";
          }
          
          return str;
        };

        let content = "<div style='max-width: 280px; word-wrap: break-word; overflow-wrap: break-word;' class='p-2 text-sm'>";
        
        if (props.layer_name) {
          content += `<span class='inline-block text-xs bg-gray-200 rounded px-1 mb-1'>${props.layer_name}</span><br/>`;
        }
        
        if (props.name || props["名称"]) {
          const name = props.name || props["名称"];
          content += `<strong class='text-gray-900'>${name}</strong><br/>`;
        }
        
        const excludeKeys = ["name", "名称", "layer_name", "feature_id"];
        const keys = Object.keys(props).filter((k) => !excludeKeys.includes(k));
        
        if (keys.length > 0) {
          content += "<table class='mt-1 text-xs' style='border-collapse: collapse;'>";
          keys.slice(0, 5).forEach((key) => {
            const formattedValue = formatValue(props[key]);
            content += `<tr>
              <td class='text-gray-500 pr-2 py-0.5 align-top' style='white-space: nowrap;'>${key}:</td>
              <td class='text-gray-700 py-0.5' style='word-break: break-all;'>${formattedValue}</td>
            </tr>`;
          });
          content += "</table>";
          
          if (keys.length > 5) {
            content += `<div class='text-xs text-gray-400 mt-1'>${tRef.current("popup_more_items", { count: keys.length - 5 })}</div>`;
          }
        }
        
        content += "</div>";

        new maplibregl.Popup({ maxWidth: "300px" })
          .setLngLat(e.lngLat)
          .setHTML(content)
          .addTo(mapInstance);
      };

      const setCursor = (cursor: string) => () => {
        mapInstance.getCanvas().style.cursor = cursor;
      };

      vectorLayers.forEach((layer) => {
        const layerId = layer.id;
        const pointLayerId = `tileset-point-${layerId}`;
        const polygonLayerId = `tileset-polygon-${layerId}`;

        mapInstance.on("click", pointLayerId, handlePopupClick);
        mapInstance.on("click", polygonLayerId, handlePopupClick);

        mapInstance.on("mouseenter", pointLayerId, setCursor("pointer"));
        mapInstance.on("mouseleave", pointLayerId, setCursor(""));
        mapInstance.on("mouseenter", polygonLayerId, setCursor("pointer"));
        mapInstance.on("mouseleave", polygonLayerId, setCursor(""));
      });
    }
  }, [tileset, tileJSON, getVectorLayers, rasterOpacity]);

  /**
   * 地図のベーススタイルを生成
   */
  const getBaseStyle = useCallback((): maplibregl.StyleSpecification => {
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

    return baseStyle;
  }, [hideBaseMap]);

  // 地図の初期化
  useEffect(() => {
    if (map.current) {
      map.current.remove();
      map.current = null;
      // 地図の再初期化フローでローカル UI 状態をリセット。
      // React 19 の set-state-in-effect ルールが警告するが、deps 変更時の
      // 再初期化シーケンスで意図的に必要。
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setIsLoaded(false);
      setHasFittedBounds(false);
    }

    if (!mapContainer.current) return;

    const tileUrl = getTileUrl(refreshKey);
    if (!tileUrl) {
      setError(tRef.current("tile_url_missing"));
      return;
    }

    const { center, zoom } = getInitialView();

    try {
      map.current = new maplibregl.Map({
        container: mapContainer.current,
        style: getBaseStyle(),
        center: center,
        zoom: zoom,
        minZoom: tileJSON?.minzoom ?? tileset.min_zoom ?? 0,
        maxZoom: tileJSON?.maxzoom ?? tileset.max_zoom ?? 22,
      });

      map.current.addControl(new maplibregl.NavigationControl(), "top-right");
      map.current.addControl(new maplibregl.ScaleControl(), "bottom-left");

      map.current.on("load", () => {
        if (!map.current) return;
        addMapLayers(map.current, tileUrl);
        setIsLoaded(true);
        setError(null);
      });

      map.current.on("error", (e) => {
        console.error("Map error:", e);
        setError(tRef.current("map_load_failed"));
      });
    } catch (err) {
      console.error("Map initialization error:", err);
      setError(
        err instanceof Error ? err.message : tRef.current("map_init_failed")
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
    getBaseStyle,
    addMapLayers,
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

  // 地図ロード後にレイヤー可視性を初期化
  useEffect(() => {
    if (!isLoaded) return;
    
    const vectorLayers = getVectorLayers();
    if (vectorLayers.length > 0 && visibleLayers.size === 0) {
      // 地図 load 完了後に動的に決定される vectorLayers を初期表示状態として
      // 1 度だけ反映する用途。derived state では tileJSON 取得タイミングに
      // 追随できないため、effect 内 setState が必要。
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setVisibleLayers(new Set(vectorLayers.map(l => l.id)));
    }
  }, [isLoaded, getVectorLayers, visibleLayers.size]);

  // 全画面表示の切り替え
  const toggleFullscreen = useCallback(() => {
    setIsFullscreen((prev) => !prev);
  }, []);

  // 全画面地図の初期化
  useEffect(() => {
    if (!isFullscreen) {
      if (fullscreenMap.current) {
        fullscreenMap.current.remove();
        fullscreenMap.current = null;
      }
      return;
    }

    if (!fullscreenMapContainer.current) return;

    const tileUrl = getTileUrl(refreshKey);
    if (!tileUrl) return;

    const currentCenter = map.current?.getCenter();
    const currentZoom = map.current?.getZoom();

    try {
      fullscreenMap.current = new maplibregl.Map({
        container: fullscreenMapContainer.current,
        style: getBaseStyle(),
        center: currentCenter ? [currentCenter.lng, currentCenter.lat] : getInitialView().center,
        zoom: currentZoom ?? getInitialView().zoom,
        minZoom: tileJSON?.minzoom ?? tileset.min_zoom ?? 0,
        maxZoom: tileJSON?.maxzoom ?? tileset.max_zoom ?? 22,
      });

      fullscreenMap.current.addControl(new maplibregl.NavigationControl(), "top-right");
      fullscreenMap.current.addControl(new maplibregl.ScaleControl(), "bottom-left");
      fullscreenMap.current.addControl(new maplibregl.FullscreenControl(), "top-right");

      fullscreenMap.current.on("load", () => {
        if (!fullscreenMap.current) return;
        addMapLayers(fullscreenMap.current, tileUrl);
      });
    } catch (err) {
      console.error("Fullscreen map initialization error:", err);
    }

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setIsFullscreen(false);
      }
    };
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      if (fullscreenMap.current) {
        fullscreenMap.current.remove();
        fullscreenMap.current = null;
      }
    };
  }, [isFullscreen, getTileUrl, getInitialView, getBaseStyle, addMapLayers, tileJSON, tileset, refreshKey]);

  // 全画面モードを閉じたときにメイン地図の状態を同期
  useEffect(() => {
    if (!isFullscreen && fullscreenMap.current && map.current) {
      const center = fullscreenMap.current.getCenter();
      const zoom = fullscreenMap.current.getZoom();
      map.current.jumpTo({ center, zoom });
    }
  }, [isFullscreen]);

  if (error) {
    return (
      <div
        className="flex items-center justify-center rounded-md border bg-muted/50"
        style={{ height }}
      >
        <div className="text-center text-muted-foreground">
          <p className="text-sm">{error}</p>
          <p className="mt-1 text-xs">{t("tile_load_failed")}</p>
        </div>
      </div>
    );
  }

  const validBounds = getValidBounds();
  const hasBounds = validBounds !== null;
  const vectorLayers = getVectorLayers();
  const isRaster = tileset.type === "raster";

  return (
    <>
      {/* 通常表示 */}
      <div className="relative">
        <div
          ref={mapContainer}
          className="w-full rounded-md border"
          style={{ height }}
        />

        {/* ラスターコントロールパネル */}
        {isLoaded && isRaster && (
          <div className="absolute top-2 left-2 z-10">
            <button
              onClick={() => setShowRasterControls(!showRasterControls)}
              className={`bg-white/95 backdrop-blur-sm rounded-md px-3 py-2 text-xs shadow-md border flex items-center gap-1.5 hover:bg-gray-50 transition-colors ${
                showRasterControls ? "bg-blue-50 border-blue-300 text-blue-700" : "border-gray-200 text-gray-700"
              }`}
              title={t("raster_controls_title")}
            >
              <SlidersHorizontal className="w-3.5 h-3.5" />
              <span>{t("controls_label")}</span>
            </button>
            
            {showRasterControls && (
              <div className="mt-2 bg-white/95 backdrop-blur-sm rounded-md shadow-md border border-gray-200 min-w-[240px] overflow-hidden">
                {/* ヘッダー */}
                <div className="px-3 py-2 bg-gray-50 border-b border-gray-200">
                  <h4 className="text-xs font-semibold text-gray-700 flex items-center gap-1.5">
                    <Layers className="w-3.5 h-3.5" />
                    {t("raster_controls_title")}
                  </h4>
                </div>
                
                <div className="p-3 space-y-4">
                  {/* 不透明度スライダー */}
                  <div>
                    <label className="flex items-center justify-between text-xs text-gray-700 mb-2">
                      <span className="font-medium">{t("opacity_label")}</span>
                      <span className="text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded text-[10px]">
                        {Math.round(rasterOpacity * 100)}%
                      </span>
                    </label>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={rasterOpacity * 100}
                      onChange={(e) => updateRasterOpacity(Number(e.target.value) / 100)}
                      className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-500"
                    />
                    <div className="flex justify-between text-[10px] text-gray-400 mt-1">
                      <span>{t("opacity_transparent")}</span>
                      <span>{t("opacity_opaque")}</span>
                    </div>
                  </div>
                  
                  {/* カラーマップ選択 */}
                  <div>
                    <label className="flex items-center gap-1.5 text-xs font-medium text-gray-700 mb-2">
                      <Palette className="w-3.5 h-3.5" />
                      {t("colormap_label")}
                    </label>
                    <select
                      value={colormap}
                      onChange={(e) => handleColormapChange(e.target.value)}
                      className="w-full px-2.5 py-2 border border-gray-300 rounded-md text-xs bg-white hover:border-gray-400 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-colors cursor-pointer"
                    >
                      {COLORMAP_PRESETS.map((cm) => (
                        <option key={cm.value} value={cm.value}>
                          {t(cm.labelKey)}
                        </option>
                      ))}
                    </select>
                    <p className="text-[10px] text-gray-400 mt-1.5 leading-relaxed">
                      {t("raster_note")}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* レイヤー凡例（vectorタイプで複数レイヤーがある場合） */}
        {isLoaded && tileset.type === "vector" && vectorLayers.length > 0 && (
          <div className="absolute top-2 left-2 bg-white/95 backdrop-blur-sm rounded-md px-3 py-2 text-xs shadow-md border border-gray-200 max-w-[220px]">
            <div className="flex items-center justify-between mb-1.5">
              <span className="font-semibold text-gray-700">{t("layer_label")}</span>
              <div className="flex gap-1">
                <button
                  onClick={() => setAllLayersVisibility(true)}
                  className="px-1.5 py-0.5 text-[10px] rounded bg-gray-100 hover:bg-gray-200 text-gray-600"
                  title={t("show_all_title")}
                >
                  {t("show_all")}
                </button>
                <button
                  onClick={() => setAllLayersVisibility(false)}
                  className="px-1.5 py-0.5 text-[10px] rounded bg-gray-100 hover:bg-gray-200 text-gray-600"
                  title={t("hide_all_title")}
                >
                  {t("hide_all")}
                </button>
              </div>
            </div>
            {vectorLayers.map((layer, idx) => {
              const isVisible = visibleLayers.has(layer.id);
              return (
                <button
                  key={layer.id}
                  onClick={() => toggleLayerVisibility(layer.id)}
                  className={`flex items-center gap-1.5 w-full py-0.5 px-1 rounded hover:bg-gray-100 transition-colors ${
                    isVisible ? "" : "opacity-50"
                  }`}
                  title={isVisible ? t("hide_layer_title", { id: layer.id }) : t("show_layer_title", { id: layer.id })}
                >
                  {isVisible ? (
                    <Eye className="w-3 h-3 text-gray-500 flex-shrink-0" />
                  ) : (
                    <EyeOff className="w-3 h-3 text-gray-400 flex-shrink-0" />
                  )}
                  <span
                    className={`w-3 h-3 rounded-sm border border-gray-300 flex-shrink-0 ${
                      isVisible ? "" : "opacity-40"
                    }`}
                    style={{ backgroundColor: LAYER_COLORS[idx % LAYER_COLORS.length].fill }}
                  />
                  <span className={`truncate text-left ${isVisible ? "text-gray-700" : "text-gray-400"}`}>
                    {layer.id}
                  </span>
                </button>
              );
            })}
          </div>
        )}

        {/* コントロールボタン */}
        {isLoaded && (
          <div className="absolute bottom-8 right-2 flex flex-col gap-2">
            <button
              onClick={toggleFullscreen}
              className="rounded-md px-3 py-1.5 text-xs font-medium shadow-md bg-white/95 backdrop-blur-sm hover:bg-gray-50 cursor-pointer flex items-center gap-1.5 border border-gray-200 text-gray-700"
              title={t("fullscreen_title")}
            >
              <Maximize2 className="h-3.5 w-3.5" />
              {t("fullscreen")}
            </button>
            <button
              onClick={fitToBounds}
              disabled={!hasBounds}
              className={`rounded-md px-3 py-1.5 text-xs font-medium shadow-md border border-gray-200 ${
                hasBounds 
                  ? "bg-white/95 backdrop-blur-sm hover:bg-gray-50 cursor-pointer text-gray-700" 
                  : "bg-gray-100/90 text-gray-400 cursor-not-allowed"
              }`}
              title={hasBounds ? t("fit_bounds_title") : t("fit_bounds_missing_title")}
            >
              {t("fit_bounds")}
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
              <p className="mt-2 text-sm">{t("loading_map")}</p>
            </div>
          </div>
        )}
      </div>

      {/* 全画面モード */}
      {isFullscreen && (
        <div className="fixed inset-0 z-50 bg-black">
          <div
            ref={fullscreenMapContainer}
            className="w-full h-full"
          />

          <button
            onClick={toggleFullscreen}
            className="absolute top-4 right-4 z-10 rounded-full bg-white/95 backdrop-blur-sm p-2.5 shadow-lg hover:bg-gray-50 transition-colors border border-gray-200"
            title={t("close_title")}
          >
            <X className="h-5 w-5 text-gray-700" />
          </button>

          <div className="absolute top-4 left-4 z-10 bg-white/95 backdrop-blur-sm rounded-md px-4 py-2.5 shadow-lg border border-gray-200">
            <h2 className="font-semibold text-gray-800">{tileset.name}</h2>
            {tileset.description && (
              <p className="text-sm text-gray-600 mt-1 max-w-md truncate">{tileset.description}</p>
            )}
          </div>

          {/* ラスターコントロール（全画面モード） */}
          {isRaster && (
            <div className="absolute bottom-20 left-4 z-10 bg-white/95 backdrop-blur-sm rounded-md shadow-lg border border-gray-200 min-w-[240px] overflow-hidden">
              <div className="px-3 py-2 bg-gray-50 border-b border-gray-200">
                <h4 className="text-xs font-semibold text-gray-700 flex items-center gap-1.5">
                  <Layers className="w-3.5 h-3.5" />
                  {t("raster_controls_title")}
                </h4>
              </div>
              <div className="p-3 space-y-4">
                <div>
                  <label className="flex items-center justify-between text-xs text-gray-700 mb-2">
                    <span className="font-medium">{t("opacity_label")}</span>
                    <span className="text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded text-[10px]">
                      {Math.round(rasterOpacity * 100)}%
                    </span>
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={rasterOpacity * 100}
                    onChange={(e) => updateRasterOpacity(Number(e.target.value) / 100)}
                    className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-500"
                  />
                </div>
                <div>
                  <label className="flex items-center gap-1.5 text-xs font-medium text-gray-700 mb-2">
                    <Palette className="w-3.5 h-3.5" />
                    {t("colormap_label")}
                  </label>
                  <select
                    value={colormap}
                    onChange={(e) => handleColormapChange(e.target.value)}
                    className="w-full px-2.5 py-2 border border-gray-300 rounded-md text-xs bg-white hover:border-gray-400 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-colors cursor-pointer"
                  >
                    {COLORMAP_PRESETS.map((cm) => (
                      <option key={cm.value} value={cm.value}>
                        {t(cm.labelKey)}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
          )}

          {/* レイヤー凡例（全画面モード） */}
          {tileset.type === "vector" && vectorLayers.length > 0 && (
            <div className="absolute bottom-20 left-4 z-10 bg-white/95 backdrop-blur-sm rounded-md px-3 py-2 text-xs shadow-lg border border-gray-200 max-w-[220px]">
              <div className="flex items-center justify-between mb-1.5">
                <span className="font-semibold text-gray-700">{t("layer_label")}</span>
                <div className="flex gap-1">
                  <button
                    onClick={() => setAllLayersVisibility(true)}
                    className="px-1.5 py-0.5 text-[10px] rounded bg-gray-100 hover:bg-gray-200 text-gray-600"
                    title={t("show_all_title")}
                  >
                    {t("show_all")}
                  </button>
                  <button
                    onClick={() => setAllLayersVisibility(false)}
                    className="px-1.5 py-0.5 text-[10px] rounded bg-gray-100 hover:bg-gray-200 text-gray-600"
                    title={t("hide_all_title")}
                  >
                    {t("hide_all")}
                  </button>
                </div>
              </div>
              {vectorLayers.map((layer, idx) => {
                const isVisible = visibleLayers.has(layer.id);
                return (
                  <button
                    key={layer.id}
                    onClick={() => toggleLayerVisibility(layer.id)}
                    className={`flex items-center gap-1.5 w-full py-0.5 px-1 rounded hover:bg-gray-100 transition-colors ${
                      isVisible ? "" : "opacity-50"
                    }`}
                    title={isVisible ? t("hide_layer_title", { id: layer.id }) : t("show_layer_title", { id: layer.id })}
                  >
                    {isVisible ? (
                      <Eye className="w-3 h-3 text-gray-500 flex-shrink-0" />
                    ) : (
                      <EyeOff className="w-3 h-3 text-gray-400 flex-shrink-0" />
                    )}
                    <span
                      className={`w-3 h-3 rounded-sm border border-gray-300 flex-shrink-0 ${
                        isVisible ? "" : "opacity-40"
                      }`}
                      style={{ backgroundColor: LAYER_COLORS[idx % LAYER_COLORS.length].fill }}
                    />
                    <span className={`truncate text-left ${isVisible ? "text-gray-700" : "text-gray-400"}`}>
                      {layer.id}
                    </span>
                  </button>
                );
              })}
            </div>
          )}

          <button
            onClick={() => {
              const bounds = getValidBounds();
              if (bounds && fullscreenMap.current) {
                fullscreenMap.current.fitBounds(
                  [[bounds[0], bounds[1]], [bounds[2], bounds[3]]],
                  { padding: 50, duration: 500 }
                );
              }
            }}
            disabled={!hasBounds}
            className={`absolute bottom-8 right-4 z-10 rounded-md px-4 py-2 text-sm font-medium shadow-lg border border-gray-200 ${
              hasBounds 
                ? "bg-white/95 backdrop-blur-sm hover:bg-gray-50 cursor-pointer text-gray-700" 
                : "bg-gray-100/90 text-gray-400 cursor-not-allowed"
            }`}
            title={hasBounds ? t("fit_bounds_title") : t("fit_bounds_missing_title")}
          >
            {t("fit_bounds")}
          </button>
        </div>
      )}
    </>
  );
}
