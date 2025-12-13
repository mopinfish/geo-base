"use client";

import { AdminLayout } from "@/components/layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { Settings, User, Key, Bell, Globe } from "lucide-react";

export default function SettingsPage() {
  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* ヘッダー */}
        <div>
          <h1 className="text-3xl font-bold">設定</h1>
          <p className="text-muted-foreground">
            アカウントとアプリケーションの設定
          </p>
        </div>

        {/* プロフィール設定 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5" />
              プロフィール
            </CardTitle>
            <CardDescription>
              アカウント情報の確認と編集
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">名前</Label>
              <Input id="name" placeholder="名前を入力" disabled />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">メールアドレス</Label>
              <Input id="email" type="email" placeholder="email@example.com" disabled />
            </div>
            <p className="text-sm text-muted-foreground">
              ※ プロフィール編集は Step 3.2 で実装予定です
            </p>
          </CardContent>
        </Card>

        {/* API設定 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Key className="h-5 w-5" />
              API設定
            </CardTitle>
            <CardDescription>
              APIアクセスの設定
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">API URL</p>
                <code className="text-sm text-muted-foreground">
                  https://geo-base-puce.vercel.app
                </code>
              </div>
              <Badge>Production</Badge>
            </div>
            <Separator />
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">MCP Server URL</p>
                <code className="text-sm text-muted-foreground">
                  https://geo-base-mcp.fly.dev
                </code>
              </div>
              <Badge>Production</Badge>
            </div>
            <Separator />
            <div className="space-y-2">
              <Label htmlFor="api-token">APIトークン</Label>
              <div className="flex gap-2">
                <Input
                  id="api-token"
                  type="password"
                  value="••••••••••••••••"
                  disabled
                />
                <Button variant="outline" disabled>
                  再生成
                </Button>
              </div>
              <p className="text-sm text-muted-foreground">
                ※ APIトークン管理は Step 3.2 で実装予定です
              </p>
            </div>
          </CardContent>
        </Card>

        {/* 通知設定 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bell className="h-5 w-5" />
              通知設定
            </CardTitle>
            <CardDescription>
              通知の受信設定
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              ※ 通知設定は今後のアップデートで実装予定です
            </p>
          </CardContent>
        </Card>

        {/* 言語・地域設定 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Globe className="h-5 w-5" />
              言語・地域
            </CardTitle>
            <CardDescription>
              言語と地域の設定
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">言語</p>
                <p className="text-sm text-muted-foreground">日本語</p>
              </div>
              <Badge variant="outline">ja-JP</Badge>
            </div>
            <Separator />
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">タイムゾーン</p>
                <p className="text-sm text-muted-foreground">Asia/Tokyo</p>
              </div>
              <Badge variant="outline">UTC+9</Badge>
            </div>
          </CardContent>
        </Card>

        {/* バージョン情報 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings className="h-5 w-5" />
              システム情報
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span>Admin UI バージョン</span>
              <Badge variant="secondary">v0.1.0</Badge>
            </div>
            <div className="flex justify-between">
              <span>API バージョン</span>
              <Badge variant="secondary">v0.3.0</Badge>
            </div>
            <div className="flex justify-between">
              <span>MCP サーバー バージョン</span>
              <Badge variant="secondary">v0.2.0</Badge>
            </div>
          </CardContent>
        </Card>
      </div>
    </AdminLayout>
  );
}
