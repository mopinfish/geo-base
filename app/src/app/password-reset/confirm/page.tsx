"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { authClient } from "@/lib/auth/client";
import { AuthApiError } from "@/lib/auth/errors";


function PasswordResetConfirmForm() {
  const router = useRouter();
  const params = useSearchParams();
  const token = params.get("token");

  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setError(null);
    setLoading(true);
    try {
      await authClient.confirmPasswordReset(token, password);
      // 成功を一旦 UI に表示してから /login に遷移する。
      // E2E (AUTH-08) は `password-reset-confirm-success` testid を観測する。
      setSuccess(true);
    } catch (err) {
      setError(err instanceof AuthApiError ? err.detail : "Failed");
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <div className="container py-12">
        <p className="text-red-600" data-testid="password-reset-error">
          無効なリンクです。
        </p>
      </div>
    );
  }

  if (success) {
    return (
      <div className="container max-w-md mx-auto py-12">
        <p
          className="text-green-700"
          data-testid="password-reset-confirm-success"
        >
          パスワードを更新しました。
        </p>
        <button
          type="button"
          onClick={() => router.push("/login?reset=success")}
          className="mt-4 w-full p-2 bg-blue-600 text-white rounded"
          data-testid="password-reset-confirm-success-login"
        >
          ログインへ
        </button>
      </div>
    );
  }

  return (
    <div className="container max-w-md mx-auto py-12">
      <h1 className="text-2xl font-bold mb-6">新しいパスワードを設定</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          type="password" required minLength={8}
          value={password} onChange={(e) => setPassword(e.target.value)}
          placeholder="新しいパスワード（8文字以上）" className="w-full p-2 border rounded"
          data-testid="password-reset-confirm-password"
        />
        {error && (
          <p className="text-red-600" data-testid="password-reset-error">
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={loading}
          className="w-full p-2 bg-blue-600 text-white rounded"
          data-testid="password-reset-confirm-submit"
        >
          {loading ? "..." : "更新"}
        </button>
      </form>
    </div>
  );
}


export default function PasswordResetConfirmPage() {
  return (
    <Suspense fallback={<div className="container py-12">Loading...</div>}>
      <PasswordResetConfirmForm />
    </Suspense>
  );
}
