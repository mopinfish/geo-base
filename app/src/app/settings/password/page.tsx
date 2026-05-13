"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { apiFetch } from "@/lib/api";
import { authClient } from "@/lib/auth/client";
import { AdminLayout } from "@/components/layout";
import { SettingsNav } from "@/components/settings/settings-nav";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { KeyRound, Loader2, AlertCircle } from "lucide-react";

export default function PasswordSettingsPage() {
  const t = useTranslations("settings");
  const router = useRouter();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await apiFetch("/api/auth/me/password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ current_password: current, new_password: next }),
      });
      if (res.ok) {
        // 全 device からログアウトされるので /login へ
        await authClient.logout();
        router.push("/login?password_changed=1");
        return;
      }
      let detail = t("password.error_default");
      try {
        const data = await res.json();
        if (data?.detail) detail = String(data.detail);
      } catch {
        // ignore parse errors, use default
      }
      setError(detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AdminLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">{t("header_title")}</h1>
          <p className="text-muted-foreground">{t("header_subtitle")}</p>
        </div>

        <SettingsNav />

        <Card className="max-w-2xl">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <KeyRound className="h-5 w-5" />
              {t("password.card_title")}
            </CardTitle>
            <CardDescription>{t("password.card_description")}</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="current">{t("password.current_label")}</Label>
                <Input
                  id="current"
                  type="password"
                  required
                  value={current}
                  onChange={(e) => setCurrent(e.target.value)}
                  disabled={loading}
                  data-testid="password-current"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="next">{t("password.next_label")}</Label>
                <Input
                  id="next"
                  type="password"
                  required
                  minLength={8}
                  value={next}
                  onChange={(e) => setNext(e.target.value)}
                  disabled={loading}
                  data-testid="password-next"
                />
              </div>

              {error && (
                <div
                  className="flex items-center gap-2 text-sm text-red-600"
                  data-testid="password-error"
                >
                  <AlertCircle className="h-4 w-4" />
                  {error}
                </div>
              )}

              <Button type="submit" disabled={loading} data-testid="password-submit">
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    {t("password.changing")}
                  </>
                ) : (
                  t("password.change_button")
                )}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </AdminLayout>
  );
}
