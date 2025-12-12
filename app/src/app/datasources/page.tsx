"use client";

import { AdminLayout } from "@/components/layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Database, Server, Cloud, HardDrive } from "lucide-react";

export default function DatasourcesPage() {
  const datasources = [
    {
      name: "PostGIS (Supabase)",
      type: "database",
      status: "connected",
      icon: Database,
      description: "PostgreSQL + PostGIS データベース",
    },
    {
      name: "Supabase Storage",
      type: "storage",
      status: "connected",
      icon: Cloud,
      description: "PMTiles ファイルストレージ",
    },
    {
      name: "External COG",
      type: "external",
      status: "available",
      icon: Server,
      description: "外部 Cloud Optimized GeoTIFF",
    },
    {
      name: "Local Files",
      type: "local",
      status: "development",
      icon: HardDrive,
      description: "ローカルファイルストレージ（開発用）",
    },
  ];

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* ヘッダー */}
        <div>
          <h1 className="text-3xl font-bold">データソース</h1>
          <p className="text-muted-foreground">
            接続されているデータソースの管理
          </p>
        </div>

        {/* データソース一覧 */}
        <div className="grid gap-4 md:grid-cols-2">
          {datasources.map((source) => (
            <Card key={source.name}>
              <CardHeader className="flex flex-row items-center gap-4 space-y-0">
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-muted">
                  <source.icon className="h-6 w-6" />
                </div>
                <div className="flex-1">
                  <CardTitle className="flex items-center gap-2">
                    {source.name}
                    <Badge
                      variant={
                        source.status === "connected"
                          ? "default"
                          : source.status === "available"
                          ? "secondary"
                          : "outline"
                      }
                    >
                      {source.status}
                    </Badge>
                  </CardTitle>
                  <CardDescription>{source.description}</CardDescription>
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-sm text-muted-foreground">
                  タイプ: <Badge variant="outline">{source.type}</Badge>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* 注記 */}
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">
              ※ データソースの追加・編集機能は今後のアップデートで実装予定です。
            </p>
          </CardContent>
        </Card>
      </div>
    </AdminLayout>
  );
}
