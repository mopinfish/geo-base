"use client";

import { useTranslations } from "next-intl";
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
  const t = useTranslations("auth.login");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await authClient.login(email, password);
      const next = params.get("next") || "/";
      router.push(next);
    } catch (err) {
      const msg = err instanceof AuthApiError ? err.detail : t("error_generic");
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container max-w-md mx-auto py-12">
      <h1 className="text-2xl font-bold mb-6">{t("title")}</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
          placeholder={t("email_placeholder")} className="w-full p-2 border rounded"
          data-testid="login-email"
        />
        <input
          type="password" required value={password} onChange={(e) => setPassword(e.target.value)}
          placeholder={t("password_placeholder")} className="w-full p-2 border rounded"
          data-testid="login-password"
        />
        {error && <p className="text-red-600" data-testid="login-error">{error}</p>}
        <button
          type="submit" disabled={loading} className="w-full p-2 bg-blue-600 text-white rounded"
          data-testid="login-submit"
        >
          {loading ? t("submitting") : t("submit")}
        </button>
        <a href="/password-reset/request" className="block text-center text-sm">
          {t("forgot_password")}
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
