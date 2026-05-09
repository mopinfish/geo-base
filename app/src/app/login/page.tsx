"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { authClient } from "@/lib/auth/client";
import { AuthApiError } from "@/lib/auth/errors";


function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await authClient.login(email, password);
      const next = params.get("next") || "/";
      router.push(next);
    } catch (err) {
      const msg = err instanceof AuthApiError ? err.detail : "Login failed";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container max-w-md mx-auto py-12">
      <h1 className="text-2xl font-bold mb-6">ログイン</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
          placeholder="メールアドレス" className="w-full p-2 border rounded"
        />
        <input
          type="password" required value={password} onChange={(e) => setPassword(e.target.value)}
          placeholder="パスワード" className="w-full p-2 border rounded"
        />
        {error && <p className="text-red-600">{error}</p>}
        <button type="submit" disabled={loading} className="w-full p-2 bg-blue-600 text-white rounded">
          {loading ? "..." : "ログイン"}
        </button>
        <a href="/password-reset/request" className="block text-center text-sm">
          パスワードをお忘れですか？
        </a>
      </form>
    </div>
  );
}


export default function LoginPage() {
  return (
    <Suspense fallback={<div className="container max-w-md mx-auto py-12">Loading...</div>}>
      <LoginForm />
    </Suspense>
  );
}
