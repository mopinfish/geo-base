"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { useApi } from "@/hooks/use-api";
import { Download, FileJson, FileText, Loader2 } from "lucide-react";

interface ExportFeaturesButtonProps {
  tilesetId: string;
  tilesetName: string;
  variant?: "default" | "outline" | "ghost";
  size?: "default" | "sm" | "lg" | "icon";
}

export function ExportFeaturesButton({
  tilesetId,
  tilesetName,
  variant = "outline",
  size = "sm",
}: ExportFeaturesButtonProps) {
  const { api } = useApi();
  const [open, setOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [exportFormat, setExportFormat] = useState<"geojson" | "csv">("geojson");
  const [error, setError] = useState<string | null>(null);

  const handleExport = async () => {
    setIsExporting(true);
    setError(null);

    try {
      if (exportFormat === "geojson") {
        const result = await api.exportFeatures({
          tileset_id: tilesetId,
        });

        // ダウンロード
        const blob = new Blob([JSON.stringify(result, null, 2)], {
          type: "application/geo+json",
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${tilesetName.replace(/[^a-zA-Z0-9_-]/g, "_")}.geojson`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      } else {
        const blob = await api.exportFeaturesCsv({
          tileset_id: tilesetId,
        });

        // ダウンロード
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${tilesetName.replace(/[^a-zA-Z0-9_-]/g, "_")}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }

      setOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "エクスポートに失敗しました");
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant={variant} size={size}>
          <Download className="mr-2 h-4 w-4" />
          エクスポート
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>フィーチャーをエクスポート</DialogTitle>
          <DialogDescription>
            タイルセット「{tilesetName}」のフィーチャーをエクスポートします。
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label>フォーマット</Label>
            <div className="flex gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  checked={exportFormat === "geojson"}
                  onChange={() => setExportFormat("geojson")}
                  className="h-4 w-4"
                />
                <FileJson className="h-4 w-4" />
                GeoJSON
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  checked={exportFormat === "csv"}
                  onChange={() => setExportFormat("csv")}
                  className="h-4 w-4"
                />
                <FileText className="h-4 w-4" />
                CSV
              </label>
            </div>
          </div>

          {error && (
            <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
              {error}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            キャンセル
          </Button>
          <Button onClick={handleExport} disabled={isExporting}>
            {isExporting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                エクスポート中...
              </>
            ) : (
              <>
                <Download className="mr-2 h-4 w-4" />
                エクスポート
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
