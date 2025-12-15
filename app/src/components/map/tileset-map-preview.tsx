"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import maplibregl from "maplibre-gl";
import type { MapLayerMouseEvent } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { TileJSON, Tileset } from "@/lib/api";
import { Maximize2, X, Eye, EyeOff } from "lucide-react";

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
  const fullscreenMapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const fullscreenMap = useRef<maplibregl.Map | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasFittedBounds, setHasFittedBounds] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [visibleLayers, setVisibleLayers] = useState<Set<string>>(new Set());

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
   * 
   * マッププレビューでは全レイヤーを表示するため、
   * vectorタイプの場合はlayerパラメータなしのURLを使用する。
   * これにより全フィーチャーが "features" レイヤーにまとめられ、
   * layer_nameプロパティでスタイリングできる。
   */
  const getTileUrl = useCallback((cacheBuster?: number | string) => {
    const apiBaseUrl =
      process.env.NEXT_PUBLIC_API_URL || "https://geo-base-puce.vercel.app";

    const bustParam = cacheBuster ? `&_t=${cacheBuster}` : "";

    switch (tileset.type) {
      case "vector":
        // マッププレビュー用: layerパラメータなし → 全フィーチャーが "features" レイヤーに
        // TileJSONのURLは使用しない（layerパラメータが含まれているため）
        return `${apiBaseUrl}/api/tiles/features/{z}/{x}/{y}.pbf?tileset_id=${tileset.id}${bustParam}`;
      case "pmtiles":
        if (tileJSON?.tiles && tileJSON.tiles.length > 0) {
          const baseUrl = tileJSON.tiles[0];
          const separator = baseUrl.includes("?") ? "&" : "?";
          return cacheBuster ? `${baseUrl}${separator}_t=${cacheBuster}` : baseUrl;
        }
        return `${apiBaseUrl}/api/tiles/pmtiles/${tileset.id}/{z}/{x}/{y}.pbf${cacheBuster ? `?_t=${cacheBuster}` : ""}`;
      case "raster":
        if (tileJSON?.tiles && tileJSON.tiles.length > 0) {
          const baseUrl = tileJSON.tiles[0];
          const separator = baseUrl.includes("?") ? "&" : "?";
          return cacheBuster ? `${baseUrl}${separator}_t=${cacheBuster}` : baseUrl;
        }
        return `${apiBaseUrl}/api/tiles/raster/${tileset.id}/{z}/{x}/{y}.${tileset.format || "png"}${cacheBuster ? `?_t=${cacheBuster}` : ""}`;
      default:
        return null;
    }
  }, [tileset, tileJSON]);

  /**
   * ソースレイヤー名を決定
   * 
   * vectorタイプ:
   *   - マッププレビューではlayerパラメータなしでリクエストするため、
   *     MVT内のレイヤー名は常に "features"
   * 
   * pmtiles:
   *   - TileJSONのvector_layersから取得（PMTilesに含まれるレイヤー名）
   */
  const getSourceLayerName = useCallback((): string => {
    if (tileset.type === "vector") {
      // マッププレビューではlayerパラメータなし → MVTレイヤー名は "features"
      return "features";
    }
    
    if (tileset.type === "pmtiles") {
      const vectorLayers = getVectorLayers();
      if (vectorLayers.length > 0 && vectorLayers[0].id) {
        return vectorLayers[0].id;
      }
    }
    
    return "default";
  }, [tileset.type, getVectorLayers]);

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

    // MapLibreレイヤーの可視性を更新
    const layerIds = [
      `tileset-polygon-${layerId}`,
      `tileset-polygon-outline-${layerId}`,
      `tileset-line-${layerId}`,
      `tileset-point-${layerId}`,
    ];

    const visibility = visibleLayers.has(layerId) ? "none" : "visible";

    // 通常のマップ
    if (map.current) {
      layerIds.forEach(id => {
        if (map.current?.getLayer(id)) {
          map.current.setLayoutProperty(id, "visibility", visibility);
        }
      });
    }

    // 全画面マップ
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

    // MapLibreレイヤーの可視性を更新
    vectorLayers.forEach(layer => {
      const layerIds = [
        `tileset-polygon-${layer.id}`,
        `tileset-polygon-outline-${layer.id}`,
        `tileset-line-${layer.id}`,
        `tileset-point-${layer.id}`,
      ];

      const visibility = visible ? "visible" : "none";

      // 通常のマップ
      if (map.current) {
        layerIds.forEach(id => {
          if (map.current?.getLayer(id)) {
            map.current.setLayoutProperty(id, "visibility", visibility);
          }
        });
      }

      // 全画面マップ
      if (fullscreenMap.current) {
        layerIds.forEach(id => {
          if (fullscreenMap.current?.getLayer(id)) {
            fullscreenMap.current.setLayoutProperty(id, "visibility", visibility);
          }
        });
      }
    });
  }, [getVectorLayers]);

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
      // ラスタータイル
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
          "raster-opacity": 0.8,
        },
      });
    } else {
      // ベクタータイル（vector, pmtiles）
      mapInstance.addSource("tileset", {
        type: "vector",
        tiles: [tileUrl],
        minzoom: tileJSON?.minzoom ?? tileset.min_zoom ?? 0,
        maxzoom: tileJSON?.maxzoom ?? tileset.max_zoom ?? 22,
      });

      // vector_layersを取得（各layer_nameに対応）
      const vectorLayers = getVectorLayers();
      
      // デバッグログ
      console.log(`[TilesetMapPreview] tileset.type: ${tileset.type}`);
      console.log(`[TilesetMapPreview] tileUrl: ${tileUrl}`);
      console.log(`[TilesetMapPreview] vector_layers:`, vectorLayers.map(l => l.id));

      // 各layer_name（TileJSON vector_layers[].id）ごとに個別のMapLibreレイヤーを作成
      // MVTの各レイヤーは独立したsource-layerとして扱われる
      // これにより、QGISでも各レイヤーに異なるスタイルを適用可能
      vectorLayers.forEach((layer, idx) => {
        const layerId = layer.id;
        const colors = LAYER_COLORS[idx % LAYER_COLORS.length];
        
        // source-layer: 
        // - vectorタイプ: 各layer_nameがMVTの独立したレイヤー名になる
        // - pmtilesタイプ: TileJSONのvector_layers[].idがレイヤー名
        const sourceLayerName = layerId;

        // ジオメトリタイプでフィルタリング（layer_nameでのフィルタは不要）
        const polygonFilter: maplibregl.FilterSpecification = ["==", ["geometry-type"], "Polygon"];
        const lineFilter: maplibregl.FilterSpecification = ["==", ["geometry-type"], "LineString"];
        const pointFilter: maplibregl.FilterSpecification = ["==", ["geometry-type"], "Point"];

        // ポリゴンレイヤー
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

        // ポリゴンの境界線
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

        // ラインレイヤー
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

        // ポイントレイヤー
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

      // クリックでポップアップ表示（MapLayerMouseEvent型を使用）
      const createPopupHandler = (layerId: string) => (e: MapLayerMouseEvent) => {
        if (!e.features || e.features.length === 0) return;

        const feature = e.features[0];
        const props = feature.properties || {};

        // 値をフォーマット（URL検出、長文省略など）
        const formatValue = (value: unknown): string => {
          if (value === null || value === undefined) return "-";
          const str = String(value);
          
          // URLの場合はリンクにする
          if (str.match(/^https?:\/\//)) {
            const displayUrl = str.length > 40 ? str.substring(0, 40) + "..." : str;
            return `<a href="${str}" target="_blank" rel="noopener noreferrer" class="text-blue-600 hover:underline">${displayUrl}</a>`;
          }
          
          // 長い文字列は省略
          if (str.length > 50) {
            return str.substring(0, 50) + "...";
          }
          
          return str;
        };

        // スタイル: 最大幅を設定し、長い単語を折り返す
        let content = "<div style='max-width: 280px; word-wrap: break-word; overflow-wrap: break-word;' class='p-2 text-sm'>";
        
        // layer_nameがあれば表示
        if (props.layer_name) {
          content += `<span class='inline-block text-xs bg-gray-200 rounded px-1 mb-1'>${props.layer_name}</span><br/>`;
        }
        
        // 名称を表示
        if (props.name || props["名称"]) {
          const name = props.name || props["名称"];
          content += `<strong class='text-gray-900'>${name}</strong><br/>`;
        }
        
        // その他のプロパティを表示（最大5件）
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
          
          // 表示されていないプロパティがある場合
          if (keys.length > 5) {
            content += `<div class='text-xs text-gray-400 mt-1'>...他 ${keys.length - 5} 件</div>`;
          }
        }
        
        content += "</div>";

        new maplibregl.Popup({ maxWidth: "300px" })
          .setLngLat(e.lngLat)
          .setHTML(content)
          .addTo(mapInstance);
      };

      // ホバーでカーソル変更
      const setCursor = (cursor: string) => () => {
        mapInstance.getCanvas().style.cursor = cursor;
      };

      // 各レイヤーにイベントリスナーを登録
      vectorLayers.forEach((layer) => {
        const layerId = layer.id;
        const pointLayerId = `tileset-point-${layerId}`;
        const polygonLayerId = `tileset-polygon-${layerId}`;

        // クリックでポップアップ
        mapInstance.on("click", pointLayerId, createPopupHandler(pointLayerId));
        mapInstance.on("click", polygonLayerId, createPopupHandler(polygonLayerId));

        // ホバーでカーソル変更
        mapInstance.on("mouseenter", pointLayerId, setCursor("pointer"));
        mapInstance.on("mouseleave", pointLayerId, setCursor(""));
        mapInstance.on("mouseenter", polygonLayerId, setCursor("pointer"));
        mapInstance.on("mouseleave", polygonLayerId, setCursor(""));
      });
    }
  }, [tileset, tileJSON, getVectorLayers, fillColor, lineColor, pointColor]);

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

  // 地図ロード後にレイヤー可視性を初期化（全レイヤー表示）
  useEffect(() => {
    if (!isLoaded) return;
    
    const vectorLayers = getVectorLayers();
    if (vectorLayers.length > 0 && visibleLayers.size === 0) {
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

    // メイン地図の現在の状態を取得
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

    // ESCキーで閉じる
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
          <p className="mt-1 text-xs">タイルの読み込みに失敗しました</p>
        </div>
      </div>
    );
  }

  const validBounds = getValidBounds();
  const hasBounds = validBounds !== null;
  const vectorLayers = getVectorLayers();

  return (
    <>
      {/* 通常表示 */}
      <div className="relative">
        <div
          ref={mapContainer}
          className="w-full rounded-md border"
          style={{ height }}
        />

        {/* レイヤー凡例（vectorタイプで複数レイヤーがある場合） */}
        {isLoaded && tileset.type === "vector" && vectorLayers.length > 0 && (
          <div className="absolute top-2 left-2 bg-white/95 backdrop-blur-sm rounded-md px-3 py-2 text-xs shadow-md border border-gray-200 max-w-[220px]">
            <div className="flex items-center justify-between mb-1.5">
              <span className="font-semibold text-gray-700">レイヤー:</span>
              <div className="flex gap-1">
                <button
                  onClick={() => setAllLayersVisibility(true)}
                  className="px-1.5 py-0.5 text-[10px] rounded bg-gray-100 hover:bg-gray-200 text-gray-600"
                  title="すべて表示"
                >
                  全表示
                </button>
                <button
                  onClick={() => setAllLayersVisibility(false)}
                  className="px-1.5 py-0.5 text-[10px] rounded bg-gray-100 hover:bg-gray-200 text-gray-600"
                  title="すべて非表示"
                >
                  全非表示
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
                  title={isVisible ? `${layer.id}を非表示` : `${layer.id}を表示`}
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

        {/* コントロールボタン - 位置をクレジット表記の上に調整 */}
        {isLoaded && (
          <div className="absolute bottom-8 right-2 flex flex-col gap-2">
            <button
              onClick={toggleFullscreen}
              className="rounded-md px-3 py-1.5 text-xs font-medium shadow-md bg-white/95 backdrop-blur-sm hover:bg-gray-50 cursor-pointer flex items-center gap-1.5 border border-gray-200 text-gray-700"
              title="全画面表示"
            >
              <Maximize2 className="h-3.5 w-3.5" />
              全画面
            </button>
            <button
              onClick={fitToBounds}
              disabled={!hasBounds}
              className={`rounded-md px-3 py-1.5 text-xs font-medium shadow-md border border-gray-200 ${
                hasBounds 
                  ? "bg-white/95 backdrop-blur-sm hover:bg-gray-50 cursor-pointer text-gray-700" 
                  : "bg-gray-100/90 text-gray-400 cursor-not-allowed"
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

      {/* 全画面モード */}
      {isFullscreen && (
        <div className="fixed inset-0 z-50 bg-black">
          {/* 全画面地図コンテナ */}
          <div
            ref={fullscreenMapContainer}
            className="w-full h-full"
          />

          {/* 閉じるボタン */}
          <button
            onClick={toggleFullscreen}
            className="absolute top-4 right-4 z-10 rounded-full bg-white/95 backdrop-blur-sm p-2.5 shadow-lg hover:bg-gray-50 transition-colors border border-gray-200"
            title="閉じる (ESC)"
          >
            <X className="h-5 w-5 text-gray-700" />
          </button>

          {/* タイルセット名 */}
          <div className="absolute top-4 left-4 z-10 bg-white/95 backdrop-blur-sm rounded-md px-4 py-2.5 shadow-lg border border-gray-200">
            <h2 className="font-semibold text-gray-800">{tileset.name}</h2>
            {tileset.description && (
              <p className="text-sm text-gray-600 mt-1 max-w-md truncate">{tileset.description}</p>
            )}
          </div>

          {/* レイヤー凡例（全画面モード） */}
          {tileset.type === "vector" && vectorLayers.length > 0 && (
            <div className="absolute bottom-20 left-4 z-10 bg-white/95 backdrop-blur-sm rounded-md px-3 py-2 text-xs shadow-lg border border-gray-200 max-w-[220px]">
              <div className="flex items-center justify-between mb-1.5">
                <span className="font-semibold text-gray-700">レイヤー:</span>
                <div className="flex gap-1">
                  <button
                    onClick={() => setAllLayersVisibility(true)}
                    className="px-1.5 py-0.5 text-[10px] rounded bg-gray-100 hover:bg-gray-200 text-gray-600"
                    title="すべて表示"
                  >
                    全表示
                  </button>
                  <button
                    onClick={() => setAllLayersVisibility(false)}
                    className="px-1.5 py-0.5 text-[10px] rounded bg-gray-100 hover:bg-gray-200 text-gray-600"
                    title="すべて非表示"
                  >
                    全非表示
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
                    title={isVisible ? `${layer.id}を非表示` : `${layer.id}を表示`}
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

          {/* 範囲にフィットボタン（全画面モード） - クレジット表記の上に配置 */}
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
            title={hasBounds ? "データ範囲にフィット" : "boundsが設定されていません"}
          >
            範囲にフィット
          </button>
        </div>
      )}
    </>
  );
}
