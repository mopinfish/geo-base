"use client";

import { useState } from "react";
import { useAuth } from "@/lib/auth/context";
import { apiFetch } from "@/lib/api";


export default function ProfileSettingsPage() {
  const { user } = useAuth();
  const [name, setName] = useState(user?.name || "");
  const [email, setEmail] = useState(user?.email || "");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(""); setMessage("");
    const res = await apiFetch("/api/auth/me", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email }),
    });
    if (res.ok) {
      setMessage("更新しました");
    } else {
      let detail = "更新に失敗しました";
      try {
        const data = await res.json();
        if (data?.detail) detail = data.detail;
      } catch {
        // ignore parse errors, use default
      }
      setError(detail);
    }
  };

  if (!user) return null;

  return (
    <div className="container max-w-md py-8">
      <h1 className="text-2xl font-bold mb-6">プロフィール設定</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          value={name} onChange={(e) => setName(e.target.value)}
          placeholder="お名前" className="w-full p-2 border rounded"
        />
        <input
          type="email" value={email} onChange={(e) => setEmail(e.target.value)}
          placeholder="メールアドレス" className="w-full p-2 border rounded"
        />
        {message && <p className="text-green-600">{message}</p>}
        {error && <p className="text-red-600">{error}</p>}
        <button type="submit" className="w-full p-2 bg-blue-600 text-white rounded">更新</button>
      </form>
    </div>
  );
}
