"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Users,
  Mail,
  Trash2,
  MoreHorizontal,
  MapPin,
  Plus,
  Shield,
  Crown,
  User,
  Eye,
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
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useApi } from "@/hooks/use-api";
import {
  Team,
  TeamUpdate,
  TeamMember,
  TeamInvitation,
  TeamTileset,
  TeamRole,
  TeamInvitationCreate,
  Tileset,
} from "@/lib/api";

const roleLabels: Record<TeamRole, string> = {
  owner: "オーナー",
  administrator: "管理者",
  member: "メンバー",
  guest: "ゲスト",
};

const roleIcons: Record<TeamRole, React.ReactNode> = {
  owner: <Crown className="w-4 h-4 text-yellow-500" />,
  administrator: <Shield className="w-4 h-4 text-blue-500" />,
  member: <User className="w-4 h-4 text-gray-500" />,
  guest: <Eye className="w-4 h-4 text-gray-400" />,
};

export default function TeamDetailPage() {
  const params = useParams();
  const router = useRouter();
  const teamId = params.id as string;
  const { api, isReady } = useApi();

  const [team, setTeam] = useState<Team | null>(null);
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [invitations, setInvitations] = useState<TeamInvitation[]>([]);
  const [teamTilesets, setTeamTilesets] = useState<TeamTileset[]>([]);
  const [availableTilesets, setAvailableTilesets] = useState<Tileset[]>([]);
  
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Edit team
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [editForm, setEditForm] = useState<TeamUpdate>({});
  const [isSaving, setIsSaving] = useState(false);

  // Invite member
  const [showInviteDialog, setShowInviteDialog] = useState(false);
  const [inviteForm, setInviteForm] = useState<TeamInvitationCreate>({ email: "" });
  const [isInviting, setIsInviting] = useState(false);

  // Add tileset
  const [showAddTilesetDialog, setShowAddTilesetDialog] = useState(false);
  const [selectedTilesetId, setSelectedTilesetId] = useState<string>("");
  const [isAddingTileset, setIsAddingTileset] = useState(false);

  // Delete team
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    if (isReady && teamId) {
      loadTeamData();
    }
  }, [isReady, teamId]);

  const loadTeamData = async () => {
    setIsLoading(true);
    setError(null);

    // チーム取得は必須。失敗したら「見つかりません」表示。
    let teamData: Team;
    try {
      teamData = await api.getTeam(teamId);
    } catch (err) {
      console.error("Failed to load team:", err);
      setError(err instanceof Error ? err.message : "チームの取得に失敗しました");
      setIsLoading(false);
      return;
    }
    setTeam(teamData);
    setEditForm({ name: teamData.name, description: teamData.description });

    // 残りは Promise.allSettled で並行取得 — owner/admin 限定の API
    // (listTeamInvitations 等) が 403 でも他のセクションは表示する。
    const [membersRes, invitationsRes, tilesetsRes, allTilesetsRes] =
      await Promise.allSettled([
        api.listTeamMembers(teamId),
        api.listTeamInvitations(teamId),
        api.listTeamTilesets(teamId),
        // チームに追加可能なタイルセットの候補。自分が所有する非公開タイルセットも
        // 候補に出すべきなので include_private: true を渡す（Issue #115）。
        api.listTilesets({ include_private: true }),
      ]);

    if (membersRes.status === "fulfilled") {
      setMembers(membersRes.value.members);
    } else {
      console.warn("Failed to load members:", membersRes.reason);
    }

    if (invitationsRes.status === "fulfilled") {
      setInvitations(invitationsRes.value.invitations);
    } else {
      // member role では 403 になり得るため警告のみ
      console.info("Skipping invitations (insufficient role):", invitationsRes.reason);
    }

    if (tilesetsRes.status === "fulfilled") {
      setTeamTilesets(tilesetsRes.value.tilesets);
    } else {
      console.warn("Failed to load team tilesets:", tilesetsRes.reason);
    }

    if (allTilesetsRes.status === "fulfilled") {
      const v = allTilesetsRes.value;
      const arr = Array.isArray(v) ? v : v.tilesets;
      setAvailableTilesets(arr);
    } else {
      console.warn("Failed to load available tilesets:", allTilesetsRes.reason);
    }

    setIsLoading(false);
  };

  const handleUpdateTeam = async () => {
    if (!team) return;
    setIsSaving(true);
    try {
      const updated = await api.updateTeam(teamId, editForm);
      setTeam(updated);
      setShowEditDialog(false);
    } catch (err) {
      console.error("Failed to update team:", err);
      setError(err instanceof Error ? err.message : "チームの更新に失敗しました");
    } finally {
      setIsSaving(false);
    }
  };

  const handleInviteMember = async () => {
    if (!inviteForm.email.trim()) return;
    setIsInviting(true);
    try {
      const invitation = await api.createTeamInvitation(teamId, inviteForm);
      setInvitations((prev) => [invitation, ...prev]);
      setShowInviteDialog(false);
      setInviteForm({ email: "" });
    } catch (err) {
      console.error("Failed to invite member:", err);
      setError(err instanceof Error ? err.message : "招待の送信に失敗しました");
    } finally {
      setIsInviting(false);
    }
  };

  const handleCancelInvitation = async (invitationId: string) => {
    try {
      await api.cancelTeamInvitation(teamId, invitationId);
      setInvitations((prev) => prev.filter((i) => i.id !== invitationId));
    } catch (err) {
      console.error("Failed to cancel invitation:", err);
      setError(err instanceof Error ? err.message : "招待のキャンセルに失敗しました");
    }
  };

  const handleRemoveMember = async (userId: string) => {
    try {
      await api.removeTeamMember(teamId, userId);
      setMembers((prev) => prev.filter((m) => m.user_id !== userId));
    } catch (err) {
      console.error("Failed to remove member:", err);
      setError(err instanceof Error ? err.message : "メンバーの削除に失敗しました");
    }
  };

  const handleChangeRole = async (userId: string, role: TeamRole) => {
    try {
      const updated = await api.updateTeamMember(teamId, userId, { role });
      setMembers((prev) =>
        prev.map((m) => (m.user_id === userId ? updated : m)),
      );
    } catch (err) {
      console.error("Failed to change role:", err);
      setError(err instanceof Error ? err.message : "役割の変更に失敗しました");
    }
  };

  const handleAddTileset = async () => {
    if (!selectedTilesetId) return;
    setIsAddingTileset(true);
    try {
      const tileset = await api.addTeamTileset(teamId, { tileset_id: selectedTilesetId });
      setTeamTilesets((prev) => [tileset, ...prev]);
      setShowAddTilesetDialog(false);
      setSelectedTilesetId("");
    } catch (err) {
      console.error("Failed to add tileset:", err);
      setError(err instanceof Error ? err.message : "タイルセットの追加に失敗しました");
    } finally {
      setIsAddingTileset(false);
    }
  };

  const handleDeleteTeam = async () => {
    setIsDeleting(true);
    try {
      await api.deleteTeam(teamId);
      router.push("/teams");
    } catch (err) {
      console.error("Failed to delete team:", err);
      setError(err instanceof Error ? err.message : "チームの削除に失敗しました");
      setIsDeleting(false);
      setShowDeleteDialog(false);
    }
  };

  const handleRemoveTileset = async (tilesetId: string) => {
    try {
      await api.removeTeamTileset(teamId, tilesetId);
      setTeamTilesets((prev) => prev.filter((t) => t.tileset_id !== tilesetId));
    } catch (err) {
      console.error("Failed to remove tileset:", err);
      setError(err instanceof Error ? err.message : "タイルセットの削除に失敗しました");
    }
  };

  if (!isReady || isLoading) {
    return (
      <AdminLayout>
        <div className="flex items-center justify-center h-64">
          <div className="text-muted-foreground">読み込み中...</div>
        </div>
      </AdminLayout>
    );
  }

  if (!team) {
    return (
      <AdminLayout>
        <div className="text-center py-12">
          <p className="text-muted-foreground">チームが見つかりません</p>
          <Button className="mt-4" onClick={() => router.push("/teams")}>
            チーム一覧に戻る
          </Button>
        </div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.push("/teams")}>
            <ArrowLeft className="w-4 h-4" />
          </Button>
          <div className="flex-1">
            <h1 className="text-2xl font-bold">{team.name}</h1>
            <p className="text-muted-foreground">@{team.slug}</p>
          </div>
          <Button
            variant="outline"
            onClick={() => setShowEditDialog(true)}
            data-testid="team-edit-button"
          >
            設定を編集
          </Button>
          <Button
            variant="destructive"
            onClick={() => setShowDeleteDialog(true)}
            data-testid="team-delete-button"
          >
            <Trash2 className="w-4 h-4 mr-2" />
            削除
          </Button>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-destructive/10 text-destructive px-4 py-3 rounded-md">
            {error}
          </div>
        )}

        {/* Stats */}
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                メンバー数
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{members.length}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                保留中の招待
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {invitations.filter((i) => i.status === "pending").length}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                共有タイルセット
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{teamTilesets.length}</div>
            </CardContent>
          </Card>
        </div>

        {/* Tabs */}
        <Tabs defaultValue="members">
          <TabsList>
            <TabsTrigger value="members">
              <Users className="w-4 h-4 mr-2" />
              メンバー
            </TabsTrigger>
            <TabsTrigger value="invitations">
              <Mail className="w-4 h-4 mr-2" />
              招待
            </TabsTrigger>
            <TabsTrigger value="tilesets">
              <MapPin className="w-4 h-4 mr-2" />
              タイルセット
            </TabsTrigger>
          </TabsList>

          {/* Members Tab */}
          <TabsContent value="members" className="space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-lg font-semibold">メンバー一覧</h2>
              <Button
                onClick={() => setShowInviteDialog(true)}
                data-testid="team-invite-button"
              >
                <Plus className="w-4 h-4 mr-2" />
                招待する
              </Button>
            </div>
            <div className="space-y-2">
              {members.map((member) => (
                <Card key={member.id} data-testid="team-member-row" data-user-id={member.user_id}>
                  <CardContent className="flex items-center justify-between py-4">
                    <div className="flex items-center gap-3">
                      {roleIcons[member.role]}
                      <div>
                        <div className="font-medium">
                          {member.user_email || member.user_id}
                        </div>
                        <div className="text-sm text-muted-foreground">
                          {roleLabels[member.role]}
                        </div>
                      </div>
                    </div>
                    {member.role !== "owner" && (
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreHorizontal className="w-4 h-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem
                            data-testid="team-member-role-promote"
                            disabled={member.role === "administrator"}
                            onClick={() =>
                              handleChangeRole(member.user_id, "administrator")
                            }
                          >
                            <Shield className="w-4 h-4 mr-2" />
                            管理者に変更
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            data-testid="team-member-role-demote"
                            disabled={member.role === "member"}
                            onClick={() =>
                              handleChangeRole(member.user_id, "member")
                            }
                          >
                            <User className="w-4 h-4 mr-2" />
                            メンバーに変更
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            className="text-destructive"
                            onClick={() => handleRemoveMember(member.user_id)}
                          >
                            <Trash2 className="w-4 h-4 mr-2" />
                            削除
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          {/* Invitations Tab */}
          <TabsContent value="invitations" className="space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-lg font-semibold">招待一覧</h2>
              <Button
                onClick={() => setShowInviteDialog(true)}
                data-testid="team-invitation-create-button"
              >
                <Plus className="w-4 h-4 mr-2" />
                新規招待
              </Button>
            </div>
            {invitations.length === 0 ? (
              <Card>
                <CardContent className="py-8 text-center text-muted-foreground">
                  保留中の招待はありません
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-2">
                {invitations.map((invitation) => (
                  <Card key={invitation.id} data-testid="team-invitation-row" data-email={invitation.email}>
                    <CardContent className="flex items-center justify-between py-4">
                      <div>
                        <div className="font-medium">{invitation.email}</div>
                        <div className="text-sm text-muted-foreground">
                          {roleLabels[invitation.role]} として招待 •{" "}
                          <Badge
                            variant={
                              invitation.status === "pending"
                                ? "default"
                                : invitation.status === "accepted"
                                ? "secondary"
                                : "outline"
                            }
                          >
                            {invitation.status === "pending"
                              ? "保留中"
                              : invitation.status === "accepted"
                              ? "承諾済み"
                              : invitation.status}
                          </Badge>
                        </div>
                      </div>
                      {invitation.status === "pending" && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleCancelInvitation(invitation.id)}
                        >
                          キャンセル
                        </Button>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

          {/* Tilesets Tab */}
          <TabsContent value="tilesets" className="space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-lg font-semibold">共有タイルセット</h2>
              <Button onClick={() => setShowAddTilesetDialog(true)}>
                <Plus className="w-4 h-4 mr-2" />
                タイルセットを追加
              </Button>
            </div>
            {teamTilesets.length === 0 ? (
              <Card>
                <CardContent className="py-8 text-center text-muted-foreground">
                  共有されているタイルセットはありません
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-2">
                {teamTilesets.map((tileset) => (
                  <Card key={tileset.id}>
                    <CardContent className="flex items-center justify-between py-4">
                      <div>
                        <div className="font-medium">
                          {tileset.tileset_name || tileset.tileset_id}
                        </div>
                        <div className="text-sm text-muted-foreground">
                          {tileset.tileset_type}
                          {tileset.permission_level && (
                            <> • 権限: {tileset.permission_level}</>
                          )}
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleRemoveTileset(tileset.tileset_id)}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>

      {/* Edit Team Dialog */}
      <Dialog open={showEditDialog} onOpenChange={setShowEditDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>チーム設定</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="edit-name">チーム名</Label>
              <Input
                id="edit-name"
                value={editForm.name ?? ""}
                onChange={(e) =>
                  setEditForm((prev) => ({ ...prev, name: e.target.value }))
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-description">説明</Label>
              <Textarea
                id="edit-description"
                value={editForm.description ?? ""}
                onChange={(e) =>
                  setEditForm((prev) => ({ ...prev, description: e.target.value }))
                }
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowEditDialog(false)}>
              キャンセル
            </Button>
            <Button onClick={handleUpdateTeam} disabled={isSaving}>
              {isSaving ? "保存中..." : "保存"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Invite Member Dialog */}
      <Dialog open={showInviteDialog} onOpenChange={setShowInviteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>メンバーを招待</DialogTitle>
            <DialogDescription>
              メールアドレスを入力して招待を送信します
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="invite-email">メールアドレス *</Label>
              <Input
                id="invite-email"
                type="email"
                value={inviteForm.email}
                onChange={(e) =>
                  setInviteForm((prev) => ({ ...prev, email: e.target.value }))
                }
                placeholder="user@example.com"
                data-testid="team-invite-email"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="invite-role">役割</Label>
              <Select
                value={inviteForm.role ?? "member"}
                onValueChange={(value: TeamRole) =>
                  setInviteForm((prev) => ({ ...prev, role: value }))
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="administrator">管理者</SelectItem>
                  <SelectItem value="member">メンバー</SelectItem>
                  <SelectItem value="guest">ゲスト</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="invite-message">メッセージ（オプション）</Label>
              <Textarea
                id="invite-message"
                value={inviteForm.message ?? ""}
                onChange={(e) =>
                  setInviteForm((prev) => ({ ...prev, message: e.target.value }))
                }
                placeholder="招待メッセージを入力..."
                rows={2}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowInviteDialog(false)}>
              キャンセル
            </Button>
            <Button
              onClick={handleInviteMember}
              disabled={!inviteForm.email.trim() || isInviting}
              data-testid="team-invite-submit"
            >
              {isInviting ? "送信中..." : "招待を送信"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Team AlertDialog (破壊的操作なので AlertDialog で confirm) */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>チームを削除</AlertDialogTitle>
            <AlertDialogDescription>
              本当に「{team.name}」を削除しますか？
              この操作は取り消せません。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>
              キャンセル
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteTeam}
              disabled={isDeleting}
              data-testid="team-delete-confirm"
            >
              {isDeleting ? "削除中..." : "削除"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Add Tileset Dialog */}
      <Dialog open={showAddTilesetDialog} onOpenChange={setShowAddTilesetDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>タイルセットを追加</DialogTitle>
            <DialogDescription>
              チームで共有するタイルセットを選択してください
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>タイルセット</Label>
              <Select value={selectedTilesetId} onValueChange={setSelectedTilesetId}>
                <SelectTrigger>
                  <SelectValue placeholder="タイルセットを選択..." />
                </SelectTrigger>
                <SelectContent>
                  {availableTilesets
                    .filter(
                      (t) => !teamTilesets.some((tt) => tt.tileset_id === t.id)
                    )
                    .map((tileset) => (
                      <SelectItem key={tileset.id} value={tileset.id}>
                        {tileset.name}
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowAddTilesetDialog(false)}
            >
              キャンセル
            </Button>
            <Button
              onClick={handleAddTileset}
              disabled={!selectedTilesetId || isAddingTileset}
            >
              {isAddingTileset ? "追加中..." : "追加"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AdminLayout>
  );
}
