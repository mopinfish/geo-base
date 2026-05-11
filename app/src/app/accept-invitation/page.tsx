"use client";

import { useTranslations } from "next-intl";
import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { authClient } from "@/lib/auth/client";
import { AuthApiError } from "@/lib/auth/errors";
import { InvitationInfo } from "@/lib/auth/types";


function AcceptInvitationForm() {
  const router = useRouter();
  const params = useSearchParams();
  const token = params.get("token");
  const t = useTranslations("auth.invitation");

  const [info, setInfo] = useState<InvitationInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // token 不在は下の render guard で同期的にエラー表示する。
    // この effect 自体はマウント時に呼ばれるが、network fetch だけスキップする
    // (Copilot PR #131 round 2 指摘: 「effect は呼ばれない」表現は誤解を生む)。
    if (!token) return;
    authClient.getInvitationInfo(token)
      .then(setInfo)
      .catch((err) =>
        setError(err instanceof AuthApiError ? err.detail : t("error_not_found")),
      );
  }, [token, t]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setError(null);
    setLoading(true);
    try {
      await authClient.acceptInvitation(token, password, name);
      if (info) router.push(`/teams/${info.team_id}`);
    } catch (err) {
      setError(err instanceof AuthApiError ? err.detail : t("error_generic"));
    } finally {
      setLoading(false);
    }
  };

  // token が URL に無いケースは初回 render で即エラー表示する。
  // useEffect 経由で setError → 再 render する旧実装だと、最初の 1 paint
  // だけ "Loading..." が見えるフラッシュが発生していた
  // (Copilot PR #131 round 1 指摘)。
  if (!token) {
    return (
      <div className="container py-12">
        <p className="text-red-600" data-testid="invitation-error">
          {t("error_invalid_link")}
        </p>
      </div>
    );
  }

  if (error && !info)
    return (
      <div className="container py-12">
        <p className="text-red-600" data-testid="invitation-error">
          {error}
        </p>
      </div>
    );
  if (!info) return <div className="container py-12">{t("loading")}</div>;

  if (info.has_existing_account) {
    return (
      <div className="container max-w-md mx-auto py-12">
        <h1 className="text-2xl font-bold mb-4">
          {t("title", { team: info.team_name })}
        </h1>
        <p className="mb-4">{t("existing_account_message")}</p>
        <a
          href={`/login?next=${encodeURIComponent(`/accept-invitation?token=${token}&continue=accept`)}`}
          className="block p-2 bg-blue-600 text-white rounded text-center"
          data-testid="invitation-login-link"
        >
          {t("existing_account_login")}
        </a>
      </div>
    );
  }

  return (
    <div className="container max-w-md mx-auto py-12">
      <h1 className="text-2xl font-bold mb-2">
        {t("title", { team: info.team_name })}
      </h1>
      <p className="mb-4">{t("role", { role: info.role })}</p>
      <form onSubmit={handleSubmit} className="space-y-4">
        <input value={info.email} disabled className="w-full p-2 border rounded bg-gray-100" />
        <input
          required value={name} onChange={(e) => setName(e.target.value)}
          placeholder={t("name_placeholder")} className="w-full p-2 border rounded"
          data-testid="invitation-name"
        />
        <input
          type="password" required minLength={8}
          value={password} onChange={(e) => setPassword(e.target.value)}
          placeholder={t("password_placeholder")} className="w-full p-2 border rounded"
          data-testid="invitation-password"
        />
        {error && <p className="text-red-600">{error}</p>}
        <button
          type="submit" disabled={loading}
          className="w-full p-2 bg-blue-600 text-white rounded"
          data-testid="invitation-submit"
        >
          {loading ? t("submitting") : t("submit")}
        </button>
      </form>
    </div>
  );
}


export default function AcceptInvitationPage() {
  return (
    <Suspense fallback={<div className="container py-12">Loading...</div>}>
      <AcceptInvitationForm />
    </Suspense>
  );
}
