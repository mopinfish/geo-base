"use client";

import { useEffect, useState } from "react";
import {
  Key,
  Plus,
  Copy,
  Trash2,
  MoreHorizontal,
  AlertTriangle,
  CheckCircle,
  XCircle,
  BarChart3,
} from "lucide-react";
import { AdminLayout } from "@/components/layout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { useApi } from "@/hooks/use-api";
import {
  ApiKey,
  ApiKeyCreate,
  ApiKeyCreated,
  ApiKeyScope,
  Team,
} from "@/lib/api";

const scopeLabels: Record<ApiKeyScope, string> = {
  read: "読み取り",
  write: "書き込み",
  delete: "削除",
  admin: "管理者",
};

const scopeDescriptions: Record<ApiKeyScope, string> = {
  read: "データの読み取りのみ",
  write: "データの作成・更新",
  delete: "データの削除",
  admin: "すべての操作",
};

export default function ApiKeysPage() {
  const { api, isReady } = useApi();

  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create dialog
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [createForm, setCreateForm] = useState<ApiKeyCreate>({
    name: "",
    scopes: ["read"],
  });
  const [isCreating, setIsCreating] = useState(false);

  // Key created dialog (shows the key once)
  const [createdKey, setCreatedKey] = useState<ApiKeyCreated | null>(null);
  const [showKeyDialog, setShowKeyDialog] = useState(false);
  const [keyCopied, setKeyCopied] = useState(false);

  // Revoke dialog
  const [showRevokeDialog, setShowRevokeDialog] = useState(false);
  const [keyToRevoke, setKeyToRevoke] = useState<ApiKey | null>(null);
  const [revokeReason, setRevokeReason] = useState("");
  const [isRevoking, setIsRevoking] = useState(false);

  // Delete dialog
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [keyToDelete, setKeyToDelete] = useState<ApiKey | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    if (isReady) {
      loadData();
    }
  }, [isReady]);

  const loadData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [keysResponse, teamsResponse] = await Promise.all([
        api.listApiKeys({ include_revoked: true }),
        api.listTeams(),
      ]);
      setKeys(keysResponse.keys);
      setTeams(teamsResponse.teams);
    } catch (err) {
      console.error("Failed to load data:", err);
      setError(err instanceof Error ? err.message : "データの読み込みに失敗しました");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateKey = async () => {
    if (!createForm.name.trim()) return;

    setIsCreating(true);
    try {
      const newKey = await api.createApiKey(createForm);
      setCreatedKey(newKey);
      setShowCreateDialog(false);
      setShowKeyDialog(true);
      setKeys((prev) => [newKey, ...prev]);
      setCreateForm({ name: "", scopes: ["read"] });
    } catch (err) {
      console.error("Failed to create API key:", err);
      setError(err instanceof Error ? err.message : "APIキーの作成に失敗しました");
    } finally {
      setIsCreating(false);
    }
  };

  const handleRevokeKey = async () => {
    if (!keyToRevoke) return;

    setIsRevoking(true);
    try {
      const revoked = await api.revokeApiKey(keyToRevoke.id, revokeReason || undefined);
      setKeys((prev) =>
        prev.map((k) => (k.id === revoked.id ? revoked : k))
      );
      setShowRevokeDialog(false);
      setKeyToRevoke(null);
      setRevokeReason("");
    } catch (err) {
      console.error("Failed to revoke API key:", err);
      setError(err instanceof Error ? err.message : "APIキーの無効化に失敗しました");
    } finally {
      setIsRevoking(false);
    }
  };

  const handleDeleteKey = async () => {
    if (!keyToDelete) return;

    setIsDeleting(true);
    try {
      await api.deleteApiKey(keyToDelete.id);
      setKeys((prev) => prev.filter((k) => k.id !== keyToDelete.id));
      setShowDeleteDialog(false);
      setKeyToDelete(null);
    } catch (err) {
      console.error("Failed to delete API key:", err);
      setError(err instanceof Error ? err.message : "APIキーの削除に失敗しました");
    } finally {
      setIsDeleting(false);
    }
  };

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setKeyCopied(true);
      setTimeout(() => setKeyCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  const toggleScope = (scope: ApiKeyScope) => {
    setCreateForm((prev) => {
      const currentScopes = prev.scopes ?? [];
      if (currentScopes.includes(scope)) {
        return {
          ...prev,
          scopes: currentScopes.filter((s) => s !== scope),
        };
      } else {
        return {
          ...prev,
          scopes: [...currentScopes, scope],
        };
      }
    });
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return "なし";
    return new Date(dateString).toLocaleDateString("ja-JP", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  if (!isReady) {
    return (
      <AdminLayout>
        <div className="flex items-center justify-center h-64">
          <div className="text-muted-foreground">読み込み中...</div>
        </div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">APIキー管理</h1>
            <p className="text-muted-foreground">
              外部アプリケーションからのアクセス用APIキーを管理します
            </p>
          </div>
          <Button
            onClick={() => setShowCreateDialog(true)}
            data-testid="api-key-create-button"
          >
            <Plus className="w-4 h-4 mr-2" />
            新規APIキー
          </Button>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-destructive/10 text-destructive px-4 py-3 rounded-md">
            {error}
          </div>
        )}

        {/* Keys List */}
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-muted-foreground">読み込み中...</div>
          </div>
        ) : keys.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <Key className="w-12 h-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium mb-2">APIキーがありません</h3>
              <p className="text-muted-foreground text-center mb-4">
                APIキーを作成して外部アプリケーションからアクセスしましょう
              </p>
              <Button onClick={() => setShowCreateDialog(true)}>
                <Plus className="w-4 h-4 mr-2" />
                最初のAPIキーを作成
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {keys.map((key) => (
              <Card
                key={key.id}
                className={key.revoked_at ? "opacity-60" : undefined}
                data-testid="api-key-row"
                data-key-id={key.id}
                data-key-status={key.revoked_at ? "revoked" : key.is_expired ? "expired" : "active"}
                data-key-scopes={key.scopes.join(",")}
              >
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <CardTitle className="text-lg">{key.name}</CardTitle>
                        {key.revoked_at ? (
                          <Badge variant="destructive">無効化済み</Badge>
                        ) : key.is_expired ? (
                          <Badge variant="outline" className="text-orange-600">
                            期限切れ
                          </Badge>
                        ) : key.is_active ? (
                          <Badge variant="secondary" className="text-green-800">
                            有効
                          </Badge>
                        ) : (
                          <Badge variant="outline">無効</Badge>
                        )}
                      </div>
                      <CardDescription
                        className="font-mono text-xs"
                        data-testid="api-key-masked"
                      >
                        {key.masked_key || key.prefix + "**********"}
                      </CardDescription>
                    </div>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          aria-label="アクションメニューを開く"
                        >
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem disabled>
                          <BarChart3 className="w-4 h-4 mr-2" />
                          使用状況を見る
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        {!key.revoked_at && (
                          <DropdownMenuItem
                            onClick={() => {
                              setKeyToRevoke(key);
                              setShowRevokeDialog(true);
                            }}
                            data-testid="api-key-revoke-menuitem"
                          >
                            <XCircle className="w-4 h-4 mr-2" />
                            無効化
                          </DropdownMenuItem>
                        )}
                        <DropdownMenuItem
                          className="text-destructive"
                          onClick={() => {
                            setKeyToDelete(key);
                            setShowDeleteDialog(true);
                          }}
                          data-testid="api-key-delete-menuitem"
                        >
                          <Trash2 className="w-4 h-4 mr-2" />
                          削除
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 text-sm">
                    <div>
                      <div className="text-muted-foreground mb-1">スコープ</div>
                      <div className="flex flex-wrap gap-1">
                        {key.scopes.map((scope) => (
                          <Badge key={scope} variant="outline" className="text-xs">
                            {scopeLabels[scope as ApiKeyScope] || scope}
                          </Badge>
                        ))}
                      </div>
                    </div>
                    <div>
                      <div className="text-muted-foreground mb-1">レート制限</div>
                      <div>
                        {key.rate_limit_per_minute}/分 • {key.rate_limit_per_day}/日
                      </div>
                    </div>
                    <div>
                      <div className="text-muted-foreground mb-1">最終使用</div>
                      <div>{formatDate(key.last_used_at)}</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground mb-1">作成日</div>
                      <div>{formatDate(key.created_at)}</div>
                    </div>
                  </div>
                  {key.team_name && (
                    <div className="mt-3 pt-3 border-t">
                      <span className="text-sm text-muted-foreground">
                        チーム: {key.team_name}
                      </span>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Create Key Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>新規APIキー作成</DialogTitle>
            <DialogDescription>
              外部アプリケーションからのアクセス用APIキーを作成します
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="key-name">キー名 *</Label>
              <Input
                id="key-name"
                value={createForm.name}
                onChange={(e) =>
                  setCreateForm((prev) => ({ ...prev, name: e.target.value }))
                }
                placeholder="本番環境用APIキー"
                data-testid="api-key-form-name"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="key-description">説明</Label>
              <Textarea
                id="key-description"
                value={createForm.description ?? ""}
                onChange={(e) =>
                  setCreateForm((prev) => ({ ...prev, description: e.target.value }))
                }
                placeholder="このキーの用途を入力..."
                rows={2}
              />
            </div>
            <div className="space-y-2">
              <Label>権限スコープ</Label>
              <div className="space-y-2">
                {(["read", "write", "delete", "admin"] as ApiKeyScope[]).map(
                  (scope) => (
                    <div key={scope} className="flex items-center space-x-2">
                      <Checkbox
                        id={`scope-${scope}`}
                        checked={createForm.scopes?.includes(scope)}
                        onCheckedChange={() => toggleScope(scope)}
                        data-testid={`api-key-form-scope-${scope}`}
                      />
                      <label
                        htmlFor={`scope-${scope}`}
                        className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                      >
                        {scopeLabels[scope]}
                        <span className="text-muted-foreground ml-2">
                          - {scopeDescriptions[scope]}
                        </span>
                      </label>
                    </div>
                  )
                )}
              </div>
            </div>
            {teams.length > 0 && (
              <div className="space-y-2">
                <Label>チーム（オプション）</Label>
                <Select
                  // Radix UI の SelectItem は空文字 value を許容しないため、
                  // 「個人キー」を表す sentinel `__personal__` を使い、
                  // onValueChange で undefined に変換する。
                  value={createForm.team_id ?? "__personal__"}
                  onValueChange={(value) =>
                    setCreateForm((prev) => ({
                      ...prev,
                      team_id: value === "__personal__" ? undefined : value,
                    }))
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="チームを選択（個人キーの場合は空）" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__personal__">個人キー</SelectItem>
                    {teams.map((team) => (
                      <SelectItem key={team.id} value={team.id}>
                        {team.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
            <div className="space-y-2">
              <Label>有効期限（オプション）</Label>
              <Select
                // 同上: 「無期限」を表す sentinel を使う。
                value={createForm.expires_in_days?.toString() ?? "__never__"}
                onValueChange={(value) =>
                  setCreateForm((prev) => ({
                    ...prev,
                    expires_in_days:
                      value === "__never__" ? undefined : parseInt(value),
                  }))
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="無期限" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__never__">無期限</SelectItem>
                  <SelectItem value="7">7日</SelectItem>
                  <SelectItem value="30">30日</SelectItem>
                  <SelectItem value="90">90日</SelectItem>
                  <SelectItem value="365">1年</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowCreateDialog(false)}
              disabled={isCreating}
            >
              キャンセル
            </Button>
            <Button
              onClick={handleCreateKey}
              disabled={!createForm.name.trim() || isCreating}
              data-testid="api-key-form-submit"
            >
              {isCreating ? "作成中..." : "作成"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Key Created Dialog */}
      <Dialog open={showKeyDialog} onOpenChange={setShowKeyDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-green-500" />
              APIキーが作成されました
            </DialogTitle>
            <DialogDescription>
              このキーは一度しか表示されません。必ずコピーして安全な場所に保存してください。
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <div
              className="bg-muted p-4 rounded-md font-mono text-sm break-all"
              data-testid="api-key-plaintext"
            >
              {createdKey?.key}
            </div>
            <Button
              variant="outline"
              className="w-full mt-3"
              onClick={() => createdKey && copyToClipboard(createdKey.key)}
              data-testid="api-key-copy-button"
              data-copied={keyCopied ? "1" : "0"}
            >
              {keyCopied ? (
                <>
                  <CheckCircle className="w-4 h-4 mr-2 text-green-500" />
                  コピーしました
                </>
              ) : (
                <>
                  <Copy className="w-4 h-4 mr-2" />
                  クリップボードにコピー
                </>
              )}
            </Button>
          </div>
          <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-md p-3 flex items-start gap-2">
            <AlertTriangle className="w-5 h-5 text-yellow-600 shrink-0 mt-0.5" />
            <div className="text-sm text-yellow-800 dark:text-yellow-200">
              <strong>重要:</strong> このAPIキーを他の人と共有しないでください。
              キーが漏洩した場合は、すぐに無効化してください。
            </div>
          </div>
          <DialogFooter>
            <Button onClick={() => setShowKeyDialog(false)}>閉じる</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Revoke Key Dialog */}
      <Dialog open={showRevokeDialog} onOpenChange={setShowRevokeDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>APIキーを無効化</DialogTitle>
            <DialogDescription>
              「{keyToRevoke?.name}」を無効化しますか？
              無効化されたキーは使用できなくなります。
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Label htmlFor="revoke-reason">無効化の理由（オプション）</Label>
            <Textarea
              id="revoke-reason"
              value={revokeReason}
              onChange={(e) => setRevokeReason(e.target.value)}
              placeholder="セキュリティ上の理由など..."
              rows={2}
              className="mt-2"
              data-testid="api-key-revoke-reason"
            />
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowRevokeDialog(false)}
              disabled={isRevoking}
            >
              キャンセル
            </Button>
            <Button
              variant="destructive"
              onClick={handleRevokeKey}
              disabled={isRevoking}
              data-testid="api-key-revoke-confirm"
            >
              {isRevoking ? "無効化中..." : "無効化"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Key Dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>APIキーを削除</DialogTitle>
            <DialogDescription>
              「{keyToDelete?.name}」を完全に削除しますか？
              この操作は取り消せません。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowDeleteDialog(false)}
              disabled={isDeleting}
            >
              キャンセル
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteKey}
              disabled={isDeleting}
              data-testid="api-key-delete-confirm"
            >
              {isDeleting ? "削除中..." : "削除"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AdminLayout>
  );
}
