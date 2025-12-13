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
}

/**
 * タイルセットのプレビュー表示用マップコンポーネント
 *
 * タイルセットのタイプに応じて適切な表示を行う：
 * - vector: PostGISベースのMVTタイルを表示
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
}: TilesetMapPreviewProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 初期の中心座標とズームを計算
  const getInitialView = useCallback(() => {
    // TileJSONから取得
    if (tileJSON?.center && tileJSON.center.length >= 2) {
      return {
        center: [tileJSON.center[0], tileJSON.center[1]] as [number, number],
        zoom: tileJSON.center[2] ?? 10,
      };
    }

    // タイルセットのcenterから取得
    if (tileset.center) {
      // centerは number[] または string の可能性がある（APIレスポンスによる）
      const centerValue = tileset.center as number[] | string;
      const center = Array.isArray(centerValue)
        ? centerValue
        : typeof centerValue === "string"
          ? centerValue.split(",").map(Number)
          : null;

      if (center && center.length >= 2) {
        return {
          center: [center[0], center[1]] as [number, number],
          zoom: center[2] ?? 10,
        };
      }
    }

    // boundsから中心を計算
    if (tileJSON?.bounds && tileJSON.bounds.length === 4) {
      const [west, south, east, north] = tileJSON.bounds;
      return {
        center: [(west + east) / 2, (south + north) / 2] as [number, number],
        zoom: 8,
      };
    }

    if (tileset.bounds) {
      // boundsは number[] または string の可能性がある（APIレスポンスによる）
      const boundsValue = tileset.bounds as number[] | string;
      const bounds = Array.isArray(boundsValue)
        ? boundsValue
        : typeof boundsValue === "string"
          ? boundsValue.split(",").map(Number)
          : null;

      if (bounds && bounds.length === 4) {
        const [west, south, east, north] = bounds;
        return {
          center: [(west + east) / 2, (south + north) / 2] as [number, number],
          zoom: 8,
        };
      }
    }

    // デフォルト（日本）
    return {
      center: [139.7671, 35.6812] as [number, number],
      zoom: 5,
    };
  }, [tileset, tileJSON]);

  // タイルURLを取得
  const getTileUrl = useCallback(() => {
    // TileJSONからタイルURLを取得
    if (tileJSON?.tiles && tileJSON.tiles.length > 0) {
      return tileJSON.tiles[0];
    }

    // タイルセットタイプに応じてURLを生成
    const apiBaseUrl =
      process.env.NEXT_PUBLIC_API_URL || "https://geo-base-puce.vercel.app";

    switch (tileset.type) {
      case "vector":
        return `${apiBaseUrl}/api/tiles/features/{z}/{x}/{y}.pbf?tileset_id=${tileset.id}`;
      case "pmtiles":
        return `${apiBaseUrl}/api/tiles/pmtiles/${tileset.id}/{z}/{x}/{y}.pbf`;
      case "raster":
        return `${apiBaseUrl}/api/tiles/raster/${tileset.id}/{z}/{x}/{y}.${tileset.format || "png"}`;
      default:
        return null;
    }
  }, [tileset, tileJSON]);

  // 地図の初期化
  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    const tileUrl = getTileUrl();
    if (!tileUrl) {
      setError("タイルURLが設定されていません");
      return;
    }

    const { center, zoom } = getInitialView();

    try {
      // ベースマップのスタイル設定
      const baseStyle: maplibregl.StyleSpecification = {
        version: 8,
        sources: {},
        layers: [],
      };

      // ベースマップを追加（オプション）
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
        // ベースマップなしの場合は背景色を設定
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

        // タイルセットタイプに応じてソースとレイヤーを追加
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
          // TileJSONのvector_layersから取得、またはデフォルト値を使用
          // vector_layersはTileJSON仕様にはあるが、型定義に含まれていない場合がある
          const tileJSONWithLayers = tileJSON as (typeof tileJSON & { vector_layers?: Array<{ id: string }> }) | null;
          const sourceLayer =
            tileJSONWithLayers?.vector_layers?.[0]?.id || "features" || "default";

          // ポリゴンレイヤー
          map.current.addLayer({
            id: "tileset-polygon",
            type: "fill",
            source: "tileset",
            "source-layer": sourceLayer,
            filter: ["==", ["geometry-type"], "Polygon"],
            paint: {
              "fill-color": fillColor,
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
              "line-color": lineColor,
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
              "line-color": lineColor,
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
              "circle-color": pointColor,
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
            if (props.name) {
              content += `<strong>${props.name}</strong><br/>`;
            }
            // その他のプロパティを表示（最大5件）
            const keys = Object.keys(props).filter((k) => k !== "name");
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
    fillColor,
    lineColor,
    pointColor,
    hideBaseMap,
  ]);

  // boundsにフィット
  const fitToBounds = useCallback(() => {
    if (!map.current || !isLoaded) return;

    // boundsは number[] または string の可能性がある（APIレスポンスによる）
    const boundsValue = tileset.bounds as number[] | string | undefined;
    const bounds =
      tileJSON?.bounds ||
      (Array.isArray(boundsValue)
        ? boundsValue
        : typeof boundsValue === "string"
          ? boundsValue.split(",").map(Number)
          : null);

    if (bounds && bounds.length === 4) {
      map.current.fitBounds(
        [
          [bounds[0], bounds[1]],
          [bounds[2], bounds[3]],
        ],
        { padding: 50 }
      );
    }
  }, [tileset, tileJSON, isLoaded]);

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

  return (
    <div className="relative">
      <div
        ref={mapContainer}
        className="w-full rounded-md border"
        style={{ height }}
      />

      {/* コントロールボタン */}
      {isLoaded && (
        <div className="absolute bottom-4 right-4 flex gap-2">
          <button
            onClick={fitToBounds}
            className="rounded bg-white px-2 py-1 text-xs shadow hover:bg-gray-100"
            title="範囲にフィット"
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
