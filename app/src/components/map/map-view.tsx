"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

export interface MapViewProps {
  /** 初期表示の中心座標 [lng, lat] */
  center?: [number, number];
  /** 初期表示のズームレベル */
  zoom?: number;
  /** 地図の高さ */
  height?: string;
  /** クリックイベントハンドラー（座標を受け取る） */
  onMapClick?: (lngLat: { lng: number; lat: number }) => void;
  /** 表示するGeoJSONデータ */
  geoJson?: GeoJSON.FeatureCollection | GeoJSON.Feature | null;
  /** インタラクティブかどうか */
  interactive?: boolean;
  /** マーカーの座標 [lng, lat] */
  marker?: [number, number] | null;
  /** マーカーがドラッグ可能かどうか */
  markerDraggable?: boolean;
  /** マーカーのドラッグ終了時のハンドラー */
  onMarkerDragEnd?: (lngLat: { lng: number; lat: number }) => void;
}

/**
 * MapLibre GL JS を使った地図コンポーネント
 * 
 * 主な機能:
 * - GeoJSONデータの表示
 * - クリックによる座標取得
 * - ドラッグ可能なマーカー
 */
export function MapView({
  center = [139.7671, 35.6812], // 東京駅
  zoom = 12,
  height = "400px",
  onMapClick,
  geoJson,
  interactive = true,
  marker,
  markerDraggable = false,
  onMarkerDragEnd,
}: MapViewProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const markerRef = useRef<maplibregl.Marker | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);

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
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
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
      center: center,
      zoom: zoom,
      interactive: interactive,
    });

    map.current.addControl(new maplibregl.NavigationControl(), "top-right");
    map.current.addControl(new maplibregl.ScaleControl(), "bottom-left");

    map.current.on("load", () => {
      setIsLoaded(true);
    });

    // クリックイベント
    if (onMapClick) {
      map.current.on("click", (e) => {
        onMapClick({ lng: e.lngLat.lng, lat: e.lngLat.lat });
      });
    }

    return () => {
      if (map.current) {
        map.current.remove();
        map.current = null;
      }
    };
  }, []);

  // GeoJSONデータの表示
  useEffect(() => {
    if (!map.current || !isLoaded) return;

    const sourceId = "geojson-source";
    const pointLayerId = "geojson-points";
    const lineLayerId = "geojson-lines";
    const polygonLayerId = "geojson-polygons";

    // 既存のレイヤーとソースを削除
    if (map.current.getLayer(pointLayerId)) {
      map.current.removeLayer(pointLayerId);
    }
    if (map.current.getLayer(lineLayerId)) {
      map.current.removeLayer(lineLayerId);
    }
    if (map.current.getLayer(polygonLayerId)) {
      map.current.removeLayer(polygonLayerId);
    }
    if (map.current.getLayer(`${polygonLayerId}-outline`)) {
      map.current.removeLayer(`${polygonLayerId}-outline`);
    }
    if (map.current.getSource(sourceId)) {
      map.current.removeSource(sourceId);
    }

    if (!geoJson) return;

    // GeoJSONソースを追加
    const featureCollection: GeoJSON.FeatureCollection = 
      geoJson.type === "FeatureCollection" 
        ? geoJson 
        : { type: "FeatureCollection", features: [geoJson as GeoJSON.Feature] };

    map.current.addSource(sourceId, {
      type: "geojson",
      data: featureCollection,
    });

    // ポリゴンレイヤー
    map.current.addLayer({
      id: polygonLayerId,
      type: "fill",
      source: sourceId,
      filter: ["==", ["geometry-type"], "Polygon"],
      paint: {
        "fill-color": "#3b82f6",
        "fill-opacity": 0.3,
      },
    });

    // ポリゴンの境界線
    map.current.addLayer({
      id: `${polygonLayerId}-outline`,
      type: "line",
      source: sourceId,
      filter: ["==", ["geometry-type"], "Polygon"],
      paint: {
        "line-color": "#2563eb",
        "line-width": 2,
      },
    });

    // ラインレイヤー
    map.current.addLayer({
      id: lineLayerId,
      type: "line",
      source: sourceId,
      filter: ["==", ["geometry-type"], "LineString"],
      paint: {
        "line-color": "#ef4444",
        "line-width": 3,
      },
    });

    // ポイントレイヤー
    map.current.addLayer({
      id: pointLayerId,
      type: "circle",
      source: sourceId,
      filter: ["==", ["geometry-type"], "Point"],
      paint: {
        "circle-radius": 10,
        "circle-color": "#22c55e",
        "circle-stroke-width": 2,
        "circle-stroke-color": "#ffffff",
      },
    });

    // GeoJSONの範囲にフィット
    try {
      const coordinates: [number, number][] = [];
      featureCollection.features.forEach((feature) => {
        if (feature.geometry.type === "Point") {
          coordinates.push(feature.geometry.coordinates as [number, number]);
        } else if (feature.geometry.type === "LineString") {
          coordinates.push(...(feature.geometry.coordinates as [number, number][]));
        } else if (feature.geometry.type === "Polygon") {
          feature.geometry.coordinates.forEach((ring) => {
            coordinates.push(...(ring as [number, number][]));
          });
        } else if (feature.geometry.type === "MultiPoint") {
          coordinates.push(...(feature.geometry.coordinates as [number, number][]));
        } else if (feature.geometry.type === "MultiLineString") {
          feature.geometry.coordinates.forEach((line) => {
            coordinates.push(...(line as [number, number][]));
          });
        } else if (feature.geometry.type === "MultiPolygon") {
          feature.geometry.coordinates.forEach((polygon) => {
            polygon.forEach((ring) => {
              coordinates.push(...(ring as [number, number][]));
            });
          });
        }
      });

      if (coordinates.length > 0) {
        const bounds = coordinates.reduce(
          (bounds, coord) => bounds.extend(coord),
          new maplibregl.LngLatBounds(coordinates[0], coordinates[0])
        );
        map.current.fitBounds(bounds, { padding: 50, maxZoom: 15 });
      }
    } catch (error) {
      console.error("Failed to fit bounds:", error);
    }
  }, [geoJson, isLoaded]);

  // マーカーの管理
  useEffect(() => {
    if (!map.current || !isLoaded) return;

    // 既存のマーカーを削除
    if (markerRef.current) {
      markerRef.current.remove();
      markerRef.current = null;
    }

    if (!marker) return;

    // 新しいマーカーを作成
    markerRef.current = new maplibregl.Marker({
      draggable: markerDraggable,
      color: "#ef4444",
    })
      .setLngLat(marker)
      .addTo(map.current);

    // ドラッグ終了イベント
    if (markerDraggable && onMarkerDragEnd) {
      markerRef.current.on("dragend", () => {
        const lngLat = markerRef.current?.getLngLat();
        if (lngLat) {
          onMarkerDragEnd({ lng: lngLat.lng, lat: lngLat.lat });
        }
      });
    }

    return () => {
      if (markerRef.current) {
        markerRef.current.remove();
        markerRef.current = null;
      }
    };
  }, [marker, markerDraggable, onMarkerDragEnd, isLoaded]);

  return (
    <div
      ref={mapContainer}
      className="w-full rounded-md border"
      style={{ height }}
    />
  );
}

/**
 * 座標入力用の地図コンポーネント
 * クリックまたはマーカードラッグで座標を設定できる
 */
export interface CoordinatePickerProps {
  /** 現在の座標 [lng, lat] */
  value?: [number, number] | null;
  /** 座標が変更されたときのハンドラー */
  onChange: (coords: [number, number] | null) => void;
  /** 地図の高さ */
  height?: string;
}

export function CoordinatePicker({
  value,
  onChange,
  height = "300px",
}: CoordinatePickerProps) {
  const handleMapClick = useCallback(
    (lngLat: { lng: number; lat: number }) => {
      onChange([lngLat.lng, lngLat.lat]);
    },
    [onChange]
  );

  const handleMarkerDragEnd = useCallback(
    (lngLat: { lng: number; lat: number }) => {
      onChange([lngLat.lng, lngLat.lat]);
    },
    [onChange]
  );

  return (
    <MapView
      center={value || [139.7671, 35.6812]}
      zoom={value ? 14 : 10}
      height={height}
      onMapClick={handleMapClick}
      marker={value}
      markerDraggable={true}
      onMarkerDragEnd={handleMarkerDragEnd}
    />
  );
}

/**
 * ジオメトリ編集用の地図コンポーネント
 * 
 * 機能:
 * - ジオメトリのプレビュー表示
 * - クリックで座標を追加（LineString/Polygon）
 * - 全てのジオメトリタイプに対応
 */
export interface GeometryPickerProps {
  /** ジオメトリタイプ */
  geometryType: "Point" | "LineString" | "Polygon";
  /** Pointの座標 */
  pointCoords?: [number, number] | null;
  /** LineStringの座標配列 */
  lineCoords?: [number, number][];
  /** Polygonの座標配列（外周のみ） */
  polygonCoords?: [number, number][];
  /** 座標が追加されたときのハンドラー */
  onCoordAdd?: (coord: [number, number]) => void;
  /** Pointの座標が変更されたときのハンドラー */
  onPointChange?: (coord: [number, number] | null) => void;
  /** 地図の高さ */
  height?: string;
  /** クリックで座標追加を有効にするか */
  enableClickAdd?: boolean;
}

export function GeometryPicker({
  geometryType,
  pointCoords,
  lineCoords = [],
  polygonCoords = [],
  onCoordAdd,
  onPointChange,
  height = "350px",
  enableClickAdd = true,
}: GeometryPickerProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const markerRef = useRef<maplibregl.Marker | null>(null);
  const vertexMarkersRef = useRef<maplibregl.Marker[]>([]);
  const [isLoaded, setIsLoaded] = useState(false);

  // 現在の座標を取得
  const getCurrentCoords = useCallback(() => {
    switch (geometryType) {
      case "Point":
        return pointCoords ? [pointCoords] : [];
      case "LineString":
        return lineCoords;
      case "Polygon":
        return polygonCoords;
      default:
        return [];
    }
  }, [geometryType, pointCoords, lineCoords, polygonCoords]);

  // GeoJSONを構築
  const buildGeoJson = useCallback((): GeoJSON.Feature | null => {
    switch (geometryType) {
      case "Point":
        if (!pointCoords) return null;
        return {
          type: "Feature",
          properties: {},
          geometry: {
            type: "Point",
            coordinates: pointCoords,
          },
        };
      case "LineString":
        if (lineCoords.length < 2) return null;
        return {
          type: "Feature",
          properties: {},
          geometry: {
            type: "LineString",
            coordinates: lineCoords,
          },
        };
      case "Polygon":
        if (polygonCoords.length < 3) return null;
        const ring = [...polygonCoords];
        // ポリゴンを閉じる
        if (
          ring[0][0] !== ring[ring.length - 1][0] ||
          ring[0][1] !== ring[ring.length - 1][1]
        ) {
          ring.push(ring[0]);
        }
        return {
          type: "Feature",
          properties: {},
          geometry: {
            type: "Polygon",
            coordinates: [ring],
          },
        };
      default:
        return null;
    }
  }, [geometryType, pointCoords, lineCoords, polygonCoords]);

  // 地図の初期化
  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    const coords = getCurrentCoords();
    const defaultCenter: [number, number] = coords.length > 0 ? coords[0] : [139.7671, 35.6812];

    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: {
        version: 8,
        sources: {
          osm: {
            type: "raster",
            tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
            tileSize: 256,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
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
      center: defaultCenter,
      zoom: coords.length > 0 ? 14 : 10,
    });

    map.current.addControl(new maplibregl.NavigationControl(), "top-right");
    map.current.addControl(new maplibregl.ScaleControl(), "bottom-left");

    map.current.on("load", () => {
      setIsLoaded(true);
    });

    // クリックイベント
    map.current.on("click", (e) => {
      if (!enableClickAdd) return;
      
      const coord: [number, number] = [e.lngLat.lng, e.lngLat.lat];
      
      if (geometryType === "Point" && onPointChange) {
        onPointChange(coord);
      } else if ((geometryType === "LineString" || geometryType === "Polygon") && onCoordAdd) {
        onCoordAdd(coord);
      }
    });

    return () => {
      // マーカーをクリーンアップ
      if (markerRef.current) {
        markerRef.current.remove();
        markerRef.current = null;
      }
      vertexMarkersRef.current.forEach(m => m.remove());
      vertexMarkersRef.current = [];
      
      if (map.current) {
        map.current.remove();
        map.current = null;
      }
    };
  }, []);

  // ジオメトリの表示を更新
  useEffect(() => {
    if (!map.current || !isLoaded) return;

    const sourceId = "geometry-source";
    const lineLayerId = "geometry-line";
    const polygonLayerId = "geometry-polygon";
    const vertexLayerId = "geometry-vertices";

    // 既存のレイヤーとソースを削除
    [lineLayerId, polygonLayerId, `${polygonLayerId}-outline`, vertexLayerId].forEach(layerId => {
      if (map.current?.getLayer(layerId)) {
        map.current.removeLayer(layerId);
      }
    });
    if (map.current.getSource(sourceId)) {
      map.current.removeSource(sourceId);
    }

    // 既存の頂点マーカーを削除
    vertexMarkersRef.current.forEach(m => m.remove());
    vertexMarkersRef.current = [];

    // Pointの場合はマーカーで表示
    if (geometryType === "Point") {
      if (markerRef.current) {
        markerRef.current.remove();
        markerRef.current = null;
      }
      
      if (pointCoords) {
        markerRef.current = new maplibregl.Marker({
          draggable: true,
          color: "#22c55e",
        })
          .setLngLat(pointCoords)
          .addTo(map.current);

        markerRef.current.on("dragend", () => {
          const lngLat = markerRef.current?.getLngLat();
          if (lngLat && onPointChange) {
            onPointChange([lngLat.lng, lngLat.lat]);
          }
        });
      }
      return;
    }

    // LineString/Polygonの場合
    if (markerRef.current) {
      markerRef.current.remove();
      markerRef.current = null;
    }

    const geoJson = buildGeoJson();
    if (!geoJson) {
      // ジオメトリが完成していない場合でも頂点は表示
      const coords = geometryType === "LineString" ? lineCoords : polygonCoords;
      coords.forEach((coord, index) => {
        const marker = new maplibregl.Marker({
          color: index === 0 ? "#22c55e" : "#3b82f6",
          scale: 0.7,
        })
          .setLngLat(coord)
          .addTo(map.current!);
        vertexMarkersRef.current.push(marker);
      });
      return;
    }

    // GeoJSONソースを追加
    map.current.addSource(sourceId, {
      type: "geojson",
      data: geoJson,
    });

    if (geometryType === "LineString") {
      map.current.addLayer({
        id: lineLayerId,
        type: "line",
        source: sourceId,
        paint: {
          "line-color": "#ef4444",
          "line-width": 3,
        },
      });
    } else if (geometryType === "Polygon") {
      map.current.addLayer({
        id: polygonLayerId,
        type: "fill",
        source: sourceId,
        paint: {
          "fill-color": "#3b82f6",
          "fill-opacity": 0.3,
        },
      });
      map.current.addLayer({
        id: `${polygonLayerId}-outline`,
        type: "line",
        source: sourceId,
        paint: {
          "line-color": "#2563eb",
          "line-width": 2,
        },
      });
    }

    // 頂点マーカーを追加
    const coords = geometryType === "LineString" ? lineCoords : polygonCoords;
    coords.forEach((coord, index) => {
      const marker = new maplibregl.Marker({
        color: index === 0 ? "#22c55e" : "#3b82f6",
        scale: 0.7,
      })
        .setLngLat(coord)
        .addTo(map.current!);
      vertexMarkersRef.current.push(marker);
    });
  }, [geometryType, pointCoords, lineCoords, polygonCoords, isLoaded, buildGeoJson, onPointChange]);

  // 座標が変更されたときに地図をフィット
  useEffect(() => {
    if (!map.current || !isLoaded) return;

    const coords = getCurrentCoords();
    if (coords.length === 0) return;

    if (coords.length === 1) {
      map.current.flyTo({
        center: coords[0],
        zoom: 14,
      });
    } else {
      const bounds = coords.reduce(
        (bounds, coord) => bounds.extend(coord),
        new maplibregl.LngLatBounds(coords[0], coords[0])
      );
      map.current.fitBounds(bounds, { padding: 50, maxZoom: 15 });
    }
  }, [geometryType, isLoaded]);

  // ヘルプテキスト
  const getHelpText = () => {
    if (!enableClickAdd) return null;
    switch (geometryType) {
      case "Point":
        return "地図をクリックしてポイントを設定、またはマーカーをドラッグして移動";
      case "LineString":
        return "地図をクリックして頂点を追加（2点以上必要）";
      case "Polygon":
        return "地図をクリックして頂点を追加（3点以上必要）";
      default:
        return null;
    }
  };

  return (
    <div className="space-y-2">
      <div
        ref={mapContainer}
        className="w-full rounded-md border"
        style={{ height }}
      />
      {enableClickAdd && (
        <p className="text-xs text-muted-foreground">{getHelpText()}</p>
      )}
    </div>
  );
}
