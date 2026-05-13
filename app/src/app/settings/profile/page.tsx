"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { useAuth } from "@/lib/auth/context";
import { apiFetch } from "@/lib/api";
import { AdminLayout } from "@/components/layout";
import { SettingsNav } from "@/components/settings/settings-nav";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { User as UserIcon, Loader2, Check, AlertCircle } from "lucide-react";

export default function ProfileSettingsPage() {
  const t = useTranslations("settings");
  const { user } = useAuth();

  const humanizeDetail = (detail: string): string => {
    // UUID 単体（DB 由来の UserNotFound）など、ユーザに不親切な値を整形
    const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (uuidPattern.test(detail)) {
      return t("profile.error_user_not_found");
    }
    return detail;
  };
  const [name, setName] = useState(user?.name || "");
  const [email, setEmail] = useState(user?.email || "");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // `useAuth()` は authClient.refresh() 経由で非同期に user をセットするため、
  // 初回マウント時 (user=null) に確定した useState の値は空のままになる。
  // user が確定したタイミングで一度だけフォームに転写する。
  useEffect(() => {
    if (user) {
      setName((prev) => (prev === "" ? user.name || "" : prev));
      setEmail((prev) => (prev === "" ? user.email || "" : prev));
    }
  }, [user]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setMessage("");
    setLoading(true);
    try {
      const res = await apiFetch("/api/auth/me", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email }),
      });
      if (res.ok) {
        setMessage(t("profile.success_message"));
      } else {
        let detail = t("profile.error_default");
        try {
          const data = await res.json();
          if (data?.detail) detail = humanizeDetail(String(data.detail));
        } catch {
          // ignore parse errors, use default
        }
        setError(detail);
      }
    } finally {
      setLoading(false);
    }
  };

  if (!user) {
    return (
      <AdminLayout>
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      </AdminLayout>
    );
  }

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
              <UserIcon className="h-5 w-5" />
              {t("profile.card_title")}
            </CardTitle>
            <CardDescription>{t("profile.card_description")}</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">{t("profile.name_label")}</Label>
                <Input
                  id="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder={t("profile.name_placeholder")}
                  disabled={loading}
                  data-testid="profile-name"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="email">{t("profile.email_label")}</Label>
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="email@example.com"
                  disabled={loading}
                  data-testid="profile-email"
                />
              </div>

              {message && (
                <div
                  className="flex items-center gap-2 text-sm text-green-600"
                  data-testid="profile-success"
                >
                  <Check className="h-4 w-4" />
                  {message}
                </div>
              )}
              {error && (
                <div className="flex items-center gap-2 text-sm text-red-600">
                  <AlertCircle className="h-4 w-4" />
                  {error}
                </div>
              )}

              <Button type="submit" disabled={loading} data-testid="profile-submit">
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    {t("profile.updating")}
                  </>
                ) : (
                  t("profile.update_button")
                )}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </AdminLayout>
  );
}
