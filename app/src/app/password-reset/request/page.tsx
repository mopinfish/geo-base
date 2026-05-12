"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { authClient } from "@/lib/auth/client";


export default function PasswordResetRequestPage() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const t = useTranslations("auth.passwordReset.request");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await authClient.requestPasswordReset(email);
    setSubmitted(true);
  };

  if (submitted) {
    return (
      <div className="container max-w-md mx-auto py-12" data-testid="password-reset-success">
        <h1 className="text-2xl font-bold mb-4">{t("success_title")}</h1>
        <p>{t("success_message")}</p>
      </div>
    );
  }

  return (
    <div className="container max-w-md mx-auto py-12">
      <h1 className="text-2xl font-bold mb-6">{t("title")}</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
          placeholder={t("email_placeholder")} className="w-full p-2 border rounded"
          data-testid="password-reset-email"
        />
        <button
          type="submit" className="w-full p-2 bg-blue-600 text-white rounded"
          data-testid="password-reset-submit"
        >
          {t("submit")}
        </button>
      </form>
    </div>
  );
}
