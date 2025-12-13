"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { KeyRound, Loader2, Check, AlertCircle, Eye, EyeOff } from "lucide-react";

interface PasswordFormProps {
  onUpdate?: () => void;
}

interface FormState {
  newPassword: string;
  confirmPassword: string;
}

type Status = "idle" | "loading" | "success" | "error";

export function PasswordForm({ onUpdate }: PasswordFormProps) {
  const [formData, setFormData] = useState<FormState>({
    newPassword: "",
    confirmPassword: "",
  });
  const [status, setStatus] = useState<Status>("idle");
  const [message, setMessage] = useState("");
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isEditing, setIsEditing] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const validateForm = (): string | null => {
    if (formData.newPassword.length < 6) {
      return "パスワードは6文字以上で入力してください";
    }
    if (formData.newPassword !== formData.confirmPassword) {
      return "パスワードが一致しません";
    }
    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const validationError = validateForm();
    if (validationError) {
      setStatus("error");
      setMessage(validationError);
      return;
    }

    setStatus("loading");
    setMessage("");

    try {
      const supabase = createClient();
      
      const { error } = await supabase.auth.updateUser({
        password: formData.newPassword,
      });

      if (error) {
        throw error;
      }

      setStatus("success");
      setMessage("パスワードを変更しました");
      setFormData({ newPassword: "", confirmPassword: "" });
      setIsEditing(false);
      onUpdate?.();

      // 3秒後にステータスをリセット
      setTimeout(() => {
        setStatus("idle");
        setMessage("");
      }, 3000);
    } catch (error) {
      console.error("Password update error:", error);
      setStatus("error");
      if (error instanceof Error) {
        // Supabaseのエラーメッセージを日本語化
        if (error.message.includes("should be at least")) {
          setMessage("パスワードは6文字以上で入力してください");
        } else if (error.message.includes("same as")) {
          setMessage("新しいパスワードは現在のパスワードと異なるものにしてください");
        } else {
          setMessage(error.message);
        }
      } else {
        setMessage("パスワードの変更に失敗しました");
      }
    }
  };

  const handleCancel = () => {
    setFormData({ newPassword: "", confirmPassword: "" });
    setIsEditing(false);
    setStatus("idle");
    setMessage("");
    setShowNewPassword(false);
    setShowConfirmPassword(false);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <KeyRound className="h-5 w-5" />
          パスワード変更
        </CardTitle>
        <CardDescription>
          アカウントのパスワードを変更
        </CardDescription>
      </CardHeader>
      <CardContent>
        {!isEditing ? (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>現在のパスワード</Label>
              <Input
                type="password"
                value="••••••••••••"
                disabled
                className="bg-muted"
              />
            </div>
            <Button
              type="button"
              variant="outline"
              onClick={() => setIsEditing(true)}
            >
              パスワードを変更
            </Button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="newPassword">新しいパスワード</Label>
              <div className="relative">
                <Input
                  id="newPassword"
                  name="newPassword"
                  type={showNewPassword ? "text" : "password"}
                  value={formData.newPassword}
                  onChange={handleChange}
                  placeholder="6文字以上で入力"
                  disabled={status === "loading"}
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowNewPassword(!showNewPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {showNewPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="confirmPassword">新しいパスワード（確認）</Label>
              <div className="relative">
                <Input
                  id="confirmPassword"
                  name="confirmPassword"
                  type={showConfirmPassword ? "text" : "password"}
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  placeholder="パスワードを再入力"
                  disabled={status === "loading"}
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {showConfirmPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>

            {/* パスワード一致チェック表示 */}
            {formData.newPassword && formData.confirmPassword && (
              <div
                className={`flex items-center gap-2 text-sm ${
                  formData.newPassword === formData.confirmPassword
                    ? "text-green-600"
                    : "text-red-600"
                }`}
              >
                {formData.newPassword === formData.confirmPassword ? (
                  <>
                    <Check className="h-4 w-4" />
                    パスワードが一致しています
                  </>
                ) : (
                  <>
                    <AlertCircle className="h-4 w-4" />
                    パスワードが一致しません
                  </>
                )}
              </div>
            )}

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
              <Button
                type="submit"
                disabled={status === "loading" || !formData.newPassword || !formData.confirmPassword}
              >
                {status === "loading" ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    変更中...
                  </>
                ) : (
                  "パスワードを変更"
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
            </div>
          </form>
        )}
      </CardContent>
    </Card>
  );
}
