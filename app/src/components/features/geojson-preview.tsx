"use client";

import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { GeoJSONFeatureCollection } from "./geojson-dropzone";

interface GeoJSONPreviewProps {
  data: GeoJSONFeatureCollection | null;
  height?: string;
}

export function GeoJSONPreview({ data, height = "400px" }: GeoJSONPreviewProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const [isMapReady, setIsMapReady] = useState(false);

  // 地図の初期化
  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: {
        version: 8,
        sources: {
          osm: {
            type: "raster",
            tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
            tileSize: 256,
            attribution: "© OpenStreetMap contributors",
          },
        },
        layers: [
          {
            id: "osm",
            type: "raster",
            source: "osm",
          },
        ],
      },
      center: [139.6917, 35.6895], // 東京
      zoom: 10,
    });

    map.current.addControl(new maplibregl.NavigationControl(), "top-right");

    map.current.on("load", () => {
      setIsMapReady(true);
    });

    return () => {
      if (map.current) {
        map.current.remove();
        map.current = null;
      }
    };
  }, []);

  // GeoJSONデータの表示
  useEffect(() => {
    if (!map.current || !isMapReady) return;

    // 既存のソースとレイヤーを削除
    const layerIds = ["preview-fill", "preview-line", "preview-point", "preview-point-label"];
    layerIds.forEach((id) => {
      if (map.current?.getLayer(id)) {
        map.current.removeLayer(id);
      }
    });
    if (map.current.getSource("preview-data")) {
      map.current.removeSource("preview-data");
    }

    if (!data || data.features.length === 0) return;

    // GeoJSONソースを追加
    map.current.addSource("preview-data", {
      type: "geojson",
      data: data as GeoJSON.FeatureCollection,
    });

    // Polygonレイヤー
    map.current.addLayer({
      id: "preview-fill",
      type: "fill",
      source: "preview-data",
      filter: ["==", ["geometry-type"], "Polygon"],
      paint: {
        "fill-color": "#3b82f6",
        "fill-opacity": 0.3,
      },
    });

    // LineStringレイヤー
    map.current.addLayer({
      id: "preview-line",
      type: "line",
      source: "preview-data",
      filter: ["any",
        ["==", ["geometry-type"], "LineString"],
        ["==", ["geometry-type"], "Polygon"],
        ["==", ["geometry-type"], "MultiLineString"],
        ["==", ["geometry-type"], "MultiPolygon"],
      ],
      paint: {
        "line-color": "#2563eb",
        "line-width": 2,
      },
    });

    // Pointレイヤー
    map.current.addLayer({
      id: "preview-point",
      type: "circle",
      source: "preview-data",
      filter: ["any",
        ["==", ["geometry-type"], "Point"],
        ["==", ["geometry-type"], "MultiPoint"],
      ],
      paint: {
        "circle-radius": 8,
        "circle-color": "#ef4444",
        "circle-stroke-width": 2,
        "circle-stroke-color": "#ffffff",
      },
    });

    // バウンディングボックスを計算してフィット
    const bounds = new maplibregl.LngLatBounds();
    let hasValidCoords = false;

    const addCoordinatesToBounds = (coords: unknown): void => {
      if (!Array.isArray(coords)) return;
      
      if (typeof coords[0] === "number" && typeof coords[1] === "number") {
        // [lng, lat] 形式
        bounds.extend([coords[0], coords[1]] as [number, number]);
        hasValidCoords = true;
      } else {
        // ネストされた配列
        coords.forEach((c) => addCoordinatesToBounds(c));
      }
    };

    data.features.forEach((feature) => {
      if (feature.geometry) {
        // GeometryCollectionの場合は個別にジオメトリを処理
        if (feature.geometry.type === "GeometryCollection") {
          feature.geometry.geometries.forEach((geom) => {
            if ("coordinates" in geom) {
              addCoordinatesToBounds(geom.coordinates);
            }
          });
        } else if ("coordinates" in feature.geometry) {
          addCoordinatesToBounds(feature.geometry.coordinates);
        }
      }
    });

    if (hasValidCoords && !bounds.isEmpty()) {
      map.current.fitBounds(bounds, {
        padding: 50,
        maxZoom: 15,
        duration: 500,
      });
    }

  }, [data, isMapReady]);

  return (
    <div className="relative rounded-lg overflow-hidden border">
      <div
        ref={mapContainer}
        style={{ height }}
        className="w-full"
      />
      {!data && (
        <div className="absolute inset-0 flex items-center justify-center bg-muted/50">
          <p className="text-muted-foreground">
            GeoJSONファイルを読み込むとプレビューが表示されます
          </p>
        </div>
      )}
      {data && data.features.length > 0 && (
        <div className="absolute bottom-2 left-2 bg-background/90 px-2 py-1 rounded text-xs">
          {data.features.length}件のフィーチャー
        </div>
      )}
    </div>
  );
}
