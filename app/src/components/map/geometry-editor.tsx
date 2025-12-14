"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { Button } from "@/components/ui/button";
import { Plus, Trash2, RotateCcw, MousePointer } from "lucide-react";

export interface GeometryEditorProps {
  /** ジオメトリタイプ */
  geometryType: "Point" | "LineString" | "Polygon";
  /** 現在の座標 */
  coordinates: [number, number][] | [number, number] | null;
  /** 座標が変更されたときのコールバック */
  onChange: (coordinates: [number, number][] | [number, number] | null) => void;
  /** 地図の高さ */
  height?: string;
  /** 初期表示の中心座標 */
  center?: [number, number];
  /** 初期ズームレベル */
  zoom?: number;
}

/**
 * インタラクティブなジオメトリエディタ
 * 
 * - Point: クリックまたはマーカードラッグで座標を設定
 * - LineString: クリックで頂点を追加、ドラッグで移動
 * - Polygon: クリックで頂点を追加、ドラッグで移動
 */
export function GeometryEditor({
  geometryType,
  coordinates,
  onChange,
  height = "400px",
  center = [139.7671, 35.6812],
  zoom = 12,
}: GeometryEditorProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const markersRef = useRef<maplibregl.Marker[]>([]);
  const [isLoaded, setIsLoaded] = useState(false);
  const [isEditing, setIsEditing] = useState(true);

  // 座標を配列形式に正規化
  const normalizeCoordinates = useCallback((): [number, number][] => {
    if (!coordinates) return [];
    if (geometryType === "Point") {
      return Array.isArray(coordinates) && typeof coordinates[0] === "number" 
        ? [coordinates as [number, number]] 
        : [];
    }
    return coordinates as [number, number][];
  }, [coordinates, geometryType]);

  // マーカーをすべて削除
  const clearMarkers = useCallback(() => {
    markersRef.current.forEach(marker => marker.remove());
    markersRef.current = [];
  }, []);

  // ソースとレイヤーを更新
  const updateMapLayers = useCallback(() => {
    if (!map.current || !isLoaded) return;

    const coords = normalizeCoordinates();
    const sourceId = "editor-source";
    const lineLayerId = "editor-line";
    const fillLayerId = "editor-fill";

    // 既存のレイヤーを削除
    if (map.current.getLayer(lineLayerId)) {
      map.current.removeLayer(lineLayerId);
    }
    if (map.current.getLayer(fillLayerId)) {
      map.current.removeLayer(fillLayerId);
    }
    if (map.current.getSource(sourceId)) {
      map.current.removeSource(sourceId);
    }

    if (coords.length === 0) return;

    // GeoJSONデータを作成
    let geojson: GeoJSON.Feature;
    
    if (geometryType === "Point" && coords.length === 1) {
      geojson = {
        type: "Feature",
        properties: {},
        geometry: {
          type: "Point",
          coordinates: coords[0],
        },
      };
    } else if (geometryType === "LineString" && coords.length >= 2) {
      geojson = {
        type: "Feature",
        properties: {},
        geometry: {
          type: "LineString",
          coordinates: coords,
        },
      };
    } else if (geometryType === "Polygon" && coords.length >= 3) {
      // ポリゴンは閉じたリングにする
      const ring = [...coords];
      if (ring[0][0] !== ring[ring.length - 1][0] || ring[0][1] !== ring[ring.length - 1][1]) {
        ring.push(ring[0]);
      }
      geojson = {
        type: "Feature",
        properties: {},
        geometry: {
          type: "Polygon",
          coordinates: [ring],
        },
      };
    } else {
      // 点が足りない場合はLineStringとして表示
      geojson = {
        type: "Feature",
        properties: {},
        geometry: {
          type: "LineString",
          coordinates: coords,
        },
      };
    }

    // ソースを追加
    map.current.addSource(sourceId, {
      type: "geojson",
      data: geojson,
    });

    // Polygon用の塗りつぶしレイヤー
    if (geometryType === "Polygon" && coords.length >= 3) {
      map.current.addLayer({
        id: fillLayerId,
        type: "fill",
        source: sourceId,
        paint: {
          "fill-color": "#3b82f6",
          "fill-opacity": 0.2,
        },
      });
    }

    // 線レイヤー
    if ((geometryType === "LineString" || geometryType === "Polygon") && coords.length >= 1) {
      map.current.addLayer({
        id: lineLayerId,
        type: "line",
        source: sourceId,
        paint: {
          "line-color": geometryType === "Polygon" ? "#2563eb" : "#ef4444",
          "line-width": 3,
          "line-dasharray": coords.length < (geometryType === "Polygon" ? 3 : 2) ? [2, 2] : [1],
        },
      });
    }
  }, [normalizeCoordinates, geometryType, isLoaded]);

  // マーカーを配置
  const placeMarkers = useCallback(() => {
    if (!map.current || !isLoaded) return;

    clearMarkers();
    const coords = normalizeCoordinates();

    coords.forEach((coord, index) => {
      const el = document.createElement("div");
      el.className = "geometry-editor-marker";
      el.style.cssText = `
        width: 20px;
        height: 20px;
        background-color: ${geometryType === "Point" ? "#22c55e" : "#3b82f6"};
        border: 3px solid white;
        border-radius: 50%;
        cursor: ${isEditing ? "move" : "default"};
        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
      `;
      
      // 頂点番号を表示（Point以外）
      if (geometryType !== "Point") {
        el.innerHTML = `<span style="
          position: absolute;
          top: -20px;
          left: 50%;
          transform: translateX(-50%);
          background: white;
          padding: 1px 4px;
          border-radius: 4px;
          font-size: 10px;
          font-weight: bold;
          box-shadow: 0 1px 2px rgba(0,0,0,0.2);
        ">${index + 1}</span>`;
      }

      const marker = new maplibregl.Marker({
        element: el,
        draggable: isEditing,
      })
        .setLngLat(coord)
        .addTo(map.current!);

      // ドラッグ終了時に座標を更新
      marker.on("dragend", () => {
        const lngLat = marker.getLngLat();
        const newCoords = [...normalizeCoordinates()];
        newCoords[index] = [lngLat.lng, lngLat.lat];
        
        if (geometryType === "Point") {
          onChange(newCoords[0]);
        } else {
          onChange(newCoords);
        }
      });

      markersRef.current.push(marker);
    });
  }, [normalizeCoordinates, onChange, isEditing, clearMarkers, isLoaded, geometryType]);

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
    });

    map.current.addControl(new maplibregl.NavigationControl(), "top-right");
    map.current.addControl(new maplibregl.ScaleControl(), "bottom-left");

    map.current.on("load", () => {
      setIsLoaded(true);
    });

    return () => {
      clearMarkers();
      if (map.current) {
        map.current.remove();
        map.current = null;
      }
    };
  }, []);

  // クリックハンドラ
  useEffect(() => {
    if (!map.current || !isLoaded || !isEditing) return;

    const handleClick = (e: maplibregl.MapMouseEvent) => {
      const newCoord: [number, number] = [e.lngLat.lng, e.lngLat.lat];
      
      if (geometryType === "Point") {
        onChange(newCoord);
      } else {
        const currentCoords = normalizeCoordinates();
        onChange([...currentCoords, newCoord]);
      }
    };

    map.current.on("click", handleClick);

    return () => {
      if (map.current) {
        map.current.off("click", handleClick);
      }
    };
  }, [isLoaded, isEditing, geometryType, normalizeCoordinates, onChange]);

  // 座標が変更されたらマップを更新
  useEffect(() => {
    if (!isLoaded) return;
    updateMapLayers();
    placeMarkers();
  }, [coordinates, isLoaded, updateMapLayers, placeMarkers]);

  // 座標変更時に地図をフィット
  useEffect(() => {
    if (!map.current || !isLoaded) return;
    
    const coords = normalizeCoordinates();
    if (coords.length === 0) return;

    if (coords.length === 1) {
      map.current.flyTo({
        center: coords[0],
        zoom: Math.max(map.current.getZoom(), 14),
      });
    } else if (coords.length >= 2) {
      const bounds = coords.reduce(
        (bounds, coord) => bounds.extend(coord),
        new maplibregl.LngLatBounds(coords[0], coords[0])
      );
      map.current.fitBounds(bounds, { padding: 50, maxZoom: 15 });
    }
  }, [coordinates, isLoaded, normalizeCoordinates]);

  // 頂点を削除
  const removeLastVertex = () => {
    if (geometryType === "Point") {
      onChange(null);
    } else {
      const coords = normalizeCoordinates();
      if (coords.length > 0) {
        const newCoords = coords.slice(0, -1);
        onChange(newCoords.length > 0 ? newCoords : null);
      }
    }
  };

  // すべてクリア
  const clearAll = () => {
    onChange(null);
  };

  const coords = normalizeCoordinates();

  return (
    <div className="space-y-2">
      {/* ツールバー */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant={isEditing ? "default" : "outline"}
            size="sm"
            onClick={() => setIsEditing(!isEditing)}
          >
            <MousePointer className="mr-1 h-4 w-4" />
            {isEditing ? "編集中" : "編集"}
          </Button>
          <span className="text-sm text-muted-foreground">
            {geometryType === "Point" 
              ? "地図をクリックして座標を設定" 
              : "地図をクリックして頂点を追加"}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={removeLastVertex}
            disabled={coords.length === 0}
          >
            <Trash2 className="mr-1 h-4 w-4" />
            {geometryType === "Point" ? "削除" : "最後を削除"}
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={clearAll}
            disabled={coords.length === 0}
          >
            <RotateCcw className="mr-1 h-4 w-4" />
            クリア
          </Button>
        </div>
      </div>

      {/* 地図 */}
      <div
        ref={mapContainer}
        className="w-full rounded-md border"
        style={{ height }}
      />

      {/* 座標一覧 */}
      <div className="text-xs text-muted-foreground">
        {geometryType === "Point" ? (
          coords.length > 0 ? (
            <span>座標: [{coords[0][0].toFixed(6)}, {coords[0][1].toFixed(6)}]</span>
          ) : (
            <span>座標未設定</span>
          )
        ) : (
          <span>
            {coords.length}点{" "}
            {geometryType === "LineString" && coords.length < 2 && "(2点以上必要)"}
            {geometryType === "Polygon" && coords.length < 3 && "(3点以上必要)"}
          </span>
        )}
      </div>
    </div>
  );
}
