"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { AdminLayout } from "@/components/layout";
import { ProfileForm, PasswordForm } from "@/components/settings";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { useAuth } from "@/contexts";
import { createClient } from "@/lib/supabase/client";
import { 
  Key, 
  Bell, 
  Globe, 
  LogOut, 
  Loader2, 
  Server,
  ExternalLink,
  Copy,
  Check
} from "lucide-react";

// 環境変数からAPI URLを取得（クライアントサイドで参照可能なもののみ）
const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://geo-base-api.fly.dev";
const MCP_URL = "https://geo-base-mcp.fly.dev";

// バージョン情報
const VERSIONS = {
  adminUi: "0.5.0",
  api: "0.3.0",
  mcp: "0.2.0",
};

export default function SettingsPage() {
  const { user, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [copiedUrl, setCopiedUrl] = useState<string | null>(null);

  const handleLogout = async () => {
    setIsLoggingOut(true);
    try {
      const supabase = createClient();
      await supabase.auth.signOut();
      router.push("/login");
    } catch (error) {
      console.error("Logout error:", error);
      setIsLoggingOut(false);
    }
  };

  const copyToClipboard = async (text: string, label: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedUrl(label);
      setTimeout(() => setCopiedUrl(null), 2000);
    } catch (error) {
      console.error("Copy failed:", error);
    }
  };

  if (authLoading) {
    return (
      <AdminLayout>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </AdminLayout>
    );
  }

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
        <ProfileForm user={user} />

        {/* パスワード変更 */}
        <PasswordForm />

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
            {/* API URL */}
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <p className="font-medium">API URL</p>
                <code className="text-sm text-muted-foreground break-all">
                  {API_URL}
                </code>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => copyToClipboard(API_URL, "api")}
                >
                  {copiedUrl === "api" ? (
                    <Check className="h-4 w-4 text-green-600" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                </Button>
                <a
                  href={`${API_URL}/api/health`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <Button variant="ghost" size="sm">
                    <ExternalLink className="h-4 w-4" />
                  </Button>
                </a>
                <Badge>Production</Badge>
              </div>
            </div>
            
            <Separator />
            
            {/* MCP Server URL */}
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <p className="font-medium">MCP Server URL</p>
                <code className="text-sm text-muted-foreground break-all">
                  {MCP_URL}
                </code>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => copyToClipboard(MCP_URL, "mcp")}
                >
                  {copiedUrl === "mcp" ? (
                    <Check className="h-4 w-4 text-green-600" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                </Button>
                <a
                  href={`${MCP_URL}/health`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <Button variant="ghost" size="sm">
                    <ExternalLink className="h-4 w-4" />
                  </Button>
                </a>
                <Badge>Production</Badge>
              </div>
            </div>
            
            <Separator />
            
            {/* SSE エンドポイント */}
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <p className="font-medium">MCP SSE Endpoint</p>
                <code className="text-sm text-muted-foreground break-all">
                  {MCP_URL}/sse
                </code>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => copyToClipboard(`${MCP_URL}/sse`, "sse")}
                >
                  {copiedUrl === "sse" ? (
                    <Check className="h-4 w-4 text-green-600" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                </Button>
                <Badge variant="outline">SSE</Badge>
              </div>
            </div>

            <Separator />

            {/* APIトークン（将来実装） */}
            <div className="space-y-2">
              <p className="font-medium">APIトークン</p>
              <p className="text-sm text-muted-foreground">
                現在、認証にはSupabase Authのアクセストークンを使用しています。
                カスタムAPIトークンの生成・管理機能は今後のアップデートで実装予定です。
              </p>
            </div>
          </CardContent>
        </Card>

        {/* 通知設定（将来実装） */}
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
              通知設定は今後のアップデートで実装予定です。
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
              <Server className="h-5 w-5" />
              システム情報
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span>Admin UI バージョン</span>
              <Badge variant="secondary">v{VERSIONS.adminUi}</Badge>
            </div>
            <div className="flex justify-between">
              <span>API バージョン</span>
              <Badge variant="secondary">v{VERSIONS.api}</Badge>
            </div>
            <div className="flex justify-between">
              <span>MCP サーバー バージョン</span>
              <Badge variant="secondary">v{VERSIONS.mcp}</Badge>
            </div>
          </CardContent>
        </Card>

        {/* ログアウト */}
        <Card className="border-red-200">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-red-600">
              <LogOut className="h-5 w-5" />
              ログアウト
            </CardTitle>
            <CardDescription>
              このデバイスからログアウトします
            </CardDescription>
          </CardHeader>
          <CardContent>
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="destructive" disabled={isLoggingOut}>
                  {isLoggingOut ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      ログアウト中...
                    </>
                  ) : (
                    <>
                      <LogOut className="mr-2 h-4 w-4" />
                      ログアウト
                    </>
                  )}
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>ログアウトしますか？</AlertDialogTitle>
                  <AlertDialogDescription>
                    ログアウトすると、再度ログインするまで管理画面にアクセスできなくなります。
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>キャンセル</AlertDialogCancel>
                  <AlertDialogAction onClick={handleLogout}>
                    ログアウト
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </CardContent>
        </Card>
      </div>
    </AdminLayout>
  );
}
