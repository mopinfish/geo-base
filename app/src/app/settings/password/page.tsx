"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { authClient } from "@/lib/auth/client";


export default function PasswordSettingsPage() {
  const router = useRouter();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(""); setLoading(true);
    const res = await apiFetch("/api/auth/me/password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ current_password: current, new_password: next }),
    });
    if (res.ok) {
      // 全 device からログアウトされるので /login へ
      await authClient.logout();
      router.push("/login?password_changed=1");
    } else {
      const data = await res.json();
      setError(data.detail || "更新に失敗しました");
    }
    setLoading(false);
  };

  return (
    <div className="container max-w-md py-8">
      <h1 className="text-2xl font-bold mb-6">パスワード変更</h1>
      <p className="text-sm text-gray-600 mb-4">
        パスワードを変更すると、全デバイスからログアウトされます。
      </p>
      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          type="password" required
          value={current} onChange={(e) => setCurrent(e.target.value)}
          placeholder="現在のパスワード" className="w-full p-2 border rounded"
        />
        <input
          type="password" required minLength={8}
          value={next} onChange={(e) => setNext(e.target.value)}
          placeholder="新しいパスワード" className="w-full p-2 border rounded"
        />
        {error && <p className="text-red-600">{error}</p>}
        <button type="submit" disabled={loading} className="w-full p-2 bg-blue-600 text-white rounded">
          {loading ? "..." : "変更"}
        </button>
      </form>
    </div>
  );
}
