"use client";

import { useState } from "react";
import { authClient } from "@/lib/auth/client";


export default function PasswordResetRequestPage() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await authClient.requestPasswordReset(email);
    setSubmitted(true);
  };

  if (submitted) {
    return (
      <div className="container max-w-md mx-auto py-12" data-testid="password-reset-success">
        <h1 className="text-2xl font-bold mb-4">確認</h1>
        <p>該当する email が登録されている場合、リセット手順を記載したメールを送信しました。</p>
      </div>
    );
  }

  return (
    <div className="container max-w-md mx-auto py-12">
      <h1 className="text-2xl font-bold mb-6">パスワードリセット</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
          placeholder="メールアドレス" className="w-full p-2 border rounded"
          data-testid="password-reset-email"
        />
        <button
          type="submit" className="w-full p-2 bg-blue-600 text-white rounded"
          data-testid="password-reset-submit"
        >
          送信
        </button>
      </form>
    </div>
  );
}
