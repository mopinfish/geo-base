"use client";

import { useState, useEffect } from "react";
import { User } from "@supabase/supabase-js";
import { createClient } from "@/lib/supabase/client";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { User as UserIcon, Loader2, Check, AlertCircle } from "lucide-react";

interface ProfileFormProps {
  user: User | null;
  onUpdate?: () => void;
}

interface FormState {
  displayName: string;
  email: string;
}

type Status = "idle" | "loading" | "success" | "error";

export function ProfileForm({ user, onUpdate }: ProfileFormProps) {
  const [formData, setFormData] = useState<FormState>({
    displayName: "",
    email: "",
  });
  const [status, setStatus] = useState<Status>("idle");
  const [message, setMessage] = useState("");
  const [isEditing, setIsEditing] = useState(false);

  // ユーザー情報をフォームに反映
  useEffect(() => {
    if (user) {
      setFormData({
        displayName: user.user_metadata?.display_name || user.user_metadata?.full_name || "",
        email: user.email || "",
      });
    }
  }, [user]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("loading");
    setMessage("");

    try {
      const supabase = createClient();
      
      // ユーザーメタデータを更新
      const { error: updateError } = await supabase.auth.updateUser({
        data: {
          display_name: formData.displayName,
          full_name: formData.displayName,
        },
      });

      if (updateError) {
        throw updateError;
      }

      setStatus("success");
      setMessage("プロフィールを更新しました");
      setIsEditing(false);
      onUpdate?.();

      // 3秒後にステータスをリセット
      setTimeout(() => {
        setStatus("idle");
        setMessage("");
      }, 3000);
    } catch (error) {
      console.error("Profile update error:", error);
      setStatus("error");
      setMessage(error instanceof Error ? error.message : "更新に失敗しました");
    }
  };

  const handleCancel = () => {
    // 元の値に戻す
    if (user) {
      setFormData({
        displayName: user.user_metadata?.display_name || user.user_metadata?.full_name || "",
        email: user.email || "",
      });
    }
    setIsEditing(false);
    setStatus("idle");
    setMessage("");
  };

  if (!user) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <UserIcon className="h-5 w-5" />
            プロフィール
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            ログインしてください
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <UserIcon className="h-5 w-5" />
          プロフィール
        </CardTitle>
        <CardDescription>
          アカウント情報の確認と編集
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="displayName">表示名</Label>
            <Input
              id="displayName"
              name="displayName"
              value={formData.displayName}
              onChange={handleChange}
              placeholder="表示名を入力"
              disabled={!isEditing || status === "loading"}
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="email">メールアドレス</Label>
            <Input
              id="email"
              name="email"
              type="email"
              value={formData.email}
              disabled
              className="bg-muted"
            />
            <p className="text-xs text-muted-foreground">
              ※ メールアドレスの変更はサポートされていません
            </p>
          </div>

          <div className="space-y-2">
            <Label>ユーザーID</Label>
            <Input
              value={user.id}
              disabled
              className="bg-muted font-mono text-xs"
            />
          </div>

          <div className="space-y-2">
            <Label>作成日時</Label>
            <Input
              value={user.created_at ? new Date(user.created_at).toLocaleString("ja-JP") : "-"}
              disabled
              className="bg-muted"
            />
          </div>

          {/* ステータスメッセージ */}
          {message && (
            <div
              className={`flex items-center gap-2 text-sm ${
                status === "success" ? "text-green-600" : "text-red-600"
              }`}
            >
              {status === "success" ? (
                <Check className="h-4 w-4" />
              ) : (
                <AlertCircle className="h-4 w-4" />
              )}
              {message}
            </div>
          )}

          {/* ボタン */}
          <div className="flex gap-2">
            {isEditing ? (
              <>
                <Button
                  type="submit"
                  disabled={status === "loading"}
                >
                  {status === "loading" ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      保存中...
                    </>
                  ) : (
                    "保存"
                  )}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleCancel}
                  disabled={status === "loading"}
                >
                  キャンセル
                </Button>
              </>
            ) : (
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsEditing(true)}
              >
                編集
              </Button>
            )}
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
