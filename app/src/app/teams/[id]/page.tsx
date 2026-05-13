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
import { useTranslations } from "next-intl";
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

const roleIcons: Record<TeamRole, React.ReactNode> = {
  owner: <Crown className="w-4 h-4 text-yellow-500" />,
  administrator: <Shield className="w-4 h-4 text-blue-500" />,
  member: <User className="w-4 h-4 text-gray-500" />,
  guest: <Eye className="w-4 h-4 text-gray-400" />,
};

export default function TeamDetailPage() {
  const t = useTranslations("teams.detail");

  const roleLabels: Record<TeamRole, string> = {
    owner: t("role_owner"),
    administrator: t("role_administrator"),
    member: t("role_member"),
    guest: t("role_guest"),
  };
  const getRoleLabel = (role: TeamRole) => roleLabels[role];

  const permissionLabels: Record<string, string> = {
    view: t("permission_level_view"),
    edit: t("permission_level_edit"),
    admin: t("permission_level_admin"),
  };
  const getPermissionLabel = (level: string) => permissionLabels[level] ?? level;

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
      setError(err instanceof Error ? err.message : t("error_fetch"));
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
      setError(err instanceof Error ? err.message : t("error_update"));
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
      setError(err instanceof Error ? err.message : t("error_invite"));
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
      setError(err instanceof Error ? err.message : t("error_cancel_invitation"));
    }
  };

  const handleRemoveMember = async (userId: string) => {
    try {
      await api.removeTeamMember(teamId, userId);
      setMembers((prev) => prev.filter((m) => m.user_id !== userId));
    } catch (err) {
      console.error("Failed to remove member:", err);
      setError(err instanceof Error ? err.message : t("error_remove_member"));
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
      setError(err instanceof Error ? err.message : t("error_change_role"));
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
      setError(err instanceof Error ? err.message : t("error_add_tileset"));
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
      setError(err instanceof Error ? err.message : t("error_delete"));
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
      setError(err instanceof Error ? err.message : t("error_remove_tileset"));
    }
  };

  if (!isReady || isLoading) {
    return (
      <AdminLayout>
        <div className="flex items-center justify-center h-64">
          <div className="text-muted-foreground">{t("loading")}</div>
        </div>
      </AdminLayout>
    );
  }

  if (!team) {
    return (
      <AdminLayout>
        <div className="text-center py-12">
          <p className="text-muted-foreground">{t("not_found")}</p>
          <Button className="mt-4" onClick={() => router.push("/teams")}>
            {t("back_to_list")}
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
            {t("edit_button")}
          </Button>
          <Button
            variant="destructive"
            onClick={() => setShowDeleteDialog(true)}
            data-testid="team-delete-button"
          >
            <Trash2 className="w-4 h-4 mr-2" />
            {t("delete_button")}
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
                {t("stat_member_count")}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{members.length}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {t("stat_pending_invitations")}
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
                {t("stat_shared_tilesets")}
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
              {t("tab_members")}
            </TabsTrigger>
            <TabsTrigger value="invitations">
              <Mail className="w-4 h-4 mr-2" />
              {t("tab_invitations")}
            </TabsTrigger>
            <TabsTrigger value="tilesets">
              <MapPin className="w-4 h-4 mr-2" />
              {t("tab_tilesets")}
            </TabsTrigger>
          </TabsList>

          {/* Members Tab */}
          <TabsContent value="members" className="space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-lg font-semibold">{t("members_section_title")}</h2>
              <Button
                onClick={() => setShowInviteDialog(true)}
                data-testid="team-invite-button"
              >
                <Plus className="w-4 h-4 mr-2" />
                {t("invite_button")}
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
                          {getRoleLabel(member.role)}
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
                            {t("menu_promote")}
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            data-testid="team-member-role-demote"
                            disabled={member.role === "member"}
                            onClick={() =>
                              handleChangeRole(member.user_id, "member")
                            }
                          >
                            <User className="w-4 h-4 mr-2" />
                            {t("menu_demote")}
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            className="text-destructive"
                            onClick={() => handleRemoveMember(member.user_id)}
                          >
                            <Trash2 className="w-4 h-4 mr-2" />
                            {t("menu_remove_member")}
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
              <h2 className="text-lg font-semibold">{t("invitations_section_title")}</h2>
              <Button
                onClick={() => setShowInviteDialog(true)}
                data-testid="team-invitation-create-button"
              >
                <Plus className="w-4 h-4 mr-2" />
                {t("new_invitation_button")}
              </Button>
            </div>
            {invitations.length === 0 ? (
              <Card>
                <CardContent className="py-8 text-center text-muted-foreground">
                  {t("no_invitations")}
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
                          {t("invited_as", { role: getRoleLabel(invitation.role) })} •{" "}
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
                              ? t("invitation_status_pending")
                              : invitation.status === "accepted"
                              ? t("invitation_status_accepted")
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
                          {t("cancel_invitation")}
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
              <h2 className="text-lg font-semibold">{t("tilesets_section_title")}</h2>
              <Button onClick={() => setShowAddTilesetDialog(true)}>
                <Plus className="w-4 h-4 mr-2" />
                {t("add_tileset_button")}
              </Button>
            </div>
            {teamTilesets.length === 0 ? (
              <Card>
                <CardContent className="py-8 text-center text-muted-foreground">
                  {t("no_tilesets")}
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
                            <> • {t("tileset_permission", { level: getPermissionLabel(tileset.permission_level) })}</>
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
            <DialogTitle>{t("edit_dialog_title")}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="edit-name">{t("edit_name_label")}</Label>
              <Input
                id="edit-name"
                value={editForm.name ?? ""}
                onChange={(e) =>
                  setEditForm((prev) => ({ ...prev, name: e.target.value }))
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-description">{t("edit_description_label")}</Label>
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
              {t("cancel")}
            </Button>
            <Button onClick={handleUpdateTeam} disabled={isSaving}>
              {isSaving ? t("saving") : t("save_button")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Invite Member Dialog */}
      <Dialog open={showInviteDialog} onOpenChange={setShowInviteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("invite_dialog_title")}</DialogTitle>
            <DialogDescription>
              {t("invite_dialog_description")}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="invite-email">{t("invite_email_label")}</Label>
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
              <Label htmlFor="invite-role">{t("invite_role_label")}</Label>
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
                  <SelectItem value="administrator">{t("role_administrator")}</SelectItem>
                  <SelectItem value="member">{t("role_member")}</SelectItem>
                  <SelectItem value="guest">{t("role_guest")}</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="invite-message">{t("invite_message_label")}</Label>
              <Textarea
                id="invite-message"
                value={inviteForm.message ?? ""}
                onChange={(e) =>
                  setInviteForm((prev) => ({ ...prev, message: e.target.value }))
                }
                placeholder={t("invite_message_placeholder")}
                rows={2}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowInviteDialog(false)}>
              {t("cancel")}
            </Button>
            <Button
              onClick={handleInviteMember}
              disabled={!inviteForm.email.trim() || isInviting}
              data-testid="team-invite-submit"
            >
              {isInviting ? t("sending") : t("send_invite_button")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Team AlertDialog (破壊的操作なので AlertDialog で confirm) */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("delete_dialog_title")}</AlertDialogTitle>
            <AlertDialogDescription className="whitespace-pre-line">
              {t("delete_dialog_description", { name: team.name })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>
              {t("cancel")}
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteTeam}
              disabled={isDeleting}
              data-testid="team-delete-confirm"
            >
              {isDeleting ? t("deleting") : t("delete_confirm_button")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Add Tileset Dialog */}
      <Dialog open={showAddTilesetDialog} onOpenChange={setShowAddTilesetDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("add_tileset_dialog_title")}</DialogTitle>
            <DialogDescription>
              {t("add_tileset_dialog_description")}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>{t("add_tileset_label")}</Label>
              <Select value={selectedTilesetId} onValueChange={setSelectedTilesetId}>
                <SelectTrigger>
                  <SelectValue placeholder={t("add_tileset_placeholder")} />
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
              {t("cancel")}
            </Button>
            <Button
              onClick={handleAddTileset}
              disabled={!selectedTilesetId || isAddingTileset}
            >
              {isAddingTileset ? t("adding") : t("add_button")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AdminLayout>
  );
}
