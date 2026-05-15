"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { Plus, Users, Settings, Trash2, MoreHorizontal } from "lucide-react";
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
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { useApi } from "@/hooks/use-api";
import { Team, TeamCreate } from "@/lib/api";

export default function TeamsPage() {
  const t = useTranslations("teams.list");
  const router = useRouter();
  const { api, isReady } = useApi();

  const [teams, setTeams] = useState<Team[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create dialog
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [createForm, setCreateForm] = useState<TeamCreate>({ name: "" });
  const [isCreating, setIsCreating] = useState(false);

  // Delete dialog
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [teamToDelete, setTeamToDelete] = useState<Team | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const loadTeams = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.listTeams();
      setTeams(response.teams);
    } catch (err) {
      console.error("Failed to load teams:", err);
      setError(err instanceof Error ? err.message : t("error_load"));
    } finally {
      setIsLoading(false);
    }
  }, [api, t]);

  useEffect(() => {
    if (isReady) {
      loadTeams();
    }
  }, [isReady, loadTeams]);

  const handleCreateTeam = async () => {
    if (!createForm.name.trim()) return;

    setIsCreating(true);
    try {
      const team = await api.createTeam(createForm);
      setTeams((prev) => [team, ...prev]);
      setShowCreateDialog(false);
      setCreateForm({ name: "" });
    } catch (err) {
      console.error("Failed to create team:", err);
      setError(err instanceof Error ? err.message : t("error_create"));
    } finally {
      setIsCreating(false);
    }
  };

  const handleDeleteTeam = async () => {
    if (!teamToDelete) return;

    setIsDeleting(true);
    try {
      await api.deleteTeam(teamToDelete.id);
      setTeams((prev) => prev.filter((t) => t.id !== teamToDelete.id));
      setShowDeleteDialog(false);
      setTeamToDelete(null);
    } catch (err) {
      console.error("Failed to delete team:", err);
      setError(err instanceof Error ? err.message : t("error_delete"));
    } finally {
      setIsDeleting(false);
    }
  };

  if (!isReady) {
    return (
      <AdminLayout>
        <div className="flex items-center justify-center h-64">
          <div className="text-muted-foreground">{t("loading")}</div>
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
            <h1 className="text-2xl font-bold">{t("title")}</h1>
            <p className="text-muted-foreground">
              {t("subtitle")}
            </p>
          </div>
          <Button
            onClick={() => setShowCreateDialog(true)}
            data-testid="team-create-button"
          >
            <Plus className="w-4 h-4 mr-2" />
            {t("new_team_button")}
          </Button>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-destructive/10 text-destructive px-4 py-3 rounded-md">
            {error}
          </div>
        )}

        {/* Teams List */}
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-muted-foreground">{t("loading")}</div>
          </div>
        ) : teams.length === 0 ? (
          <Card data-testid="team-empty-state">
            <CardContent className="flex flex-col items-center justify-center py-12">
              <Users className="w-12 h-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium mb-2">{t("empty_title")}</h3>
              <p className="text-muted-foreground text-center mb-4">
                {t("empty_description")}
              </p>
              <Button onClick={() => setShowCreateDialog(true)}>
                <Plus className="w-4 h-4 mr-2" />
                {t("empty_create_button")}
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {teams.map((team) => (
              <Card
                key={team.id}
                className="cursor-pointer hover:shadow-md transition-shadow"
                onClick={() => router.push(`/teams/${team.id}`)}
                data-testid="team-card"
              >
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <CardTitle className="text-lg">{team.name}</CardTitle>
                      <CardDescription className="text-sm">
                        @{team.slug}
                      </CardDescription>
                    </div>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          aria-label={t("menu_aria_label")}
                        >
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem
                          onClick={(e) => {
                            e.stopPropagation();
                            router.push(`/teams/${team.id}`);
                          }}
                        >
                          <Settings className="w-4 h-4 mr-2" />
                          {t("menu_settings")}
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          className="text-destructive"
                          onClick={(e) => {
                            e.stopPropagation();
                            setTeamToDelete(team);
                            setShowDeleteDialog(true);
                          }}
                        >
                          <Trash2 className="w-4 h-4 mr-2" />
                          {t("menu_delete")}
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </CardHeader>
                <CardContent>
                  {team.description && (
                    <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
                      {team.description}
                    </p>
                  )}
                  <div className="flex items-center gap-4 text-sm text-muted-foreground">
                    <div className="flex items-center gap-1">
                      <Users className="w-4 h-4" />
                      <span>{t("member_count", { count: team.member_count ?? 0 })}</span>
                    </div>
                    <Badge variant="outline">
                      {t("tileset_count", { count: team.tileset_count ?? 0 })}
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Create Team Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("create_dialog_title")}</DialogTitle>
            <DialogDescription>
              {t("create_dialog_description")}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">{t("form_name_label")}</Label>
              <Input
                id="name"
                value={createForm.name}
                onChange={(e) =>
                  setCreateForm((prev) => ({ ...prev, name: e.target.value }))
                }
                placeholder={t("form_name_placeholder")}
                data-testid="team-create-name"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="slug">{t("form_slug_label")}</Label>
              <Input
                id="slug"
                value={createForm.slug ?? ""}
                onChange={(e) =>
                  setCreateForm((prev) => ({ ...prev, slug: e.target.value }))
                }
                placeholder={t("form_slug_placeholder")}
                data-testid="team-create-slug"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">{t("form_description_label")}</Label>
              <Textarea
                id="description"
                value={createForm.description ?? ""}
                onChange={(e) =>
                  setCreateForm((prev) => ({ ...prev, description: e.target.value }))
                }
                placeholder={t("form_description_placeholder")}
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowCreateDialog(false)}
              disabled={isCreating}
            >
              {t("cancel")}
            </Button>
            <Button
              onClick={handleCreateTeam}
              disabled={!createForm.name.trim() || isCreating}
              data-testid="team-create-submit"
            >
              {isCreating ? t("creating") : t("create_button")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Team Dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("delete_dialog_title")}</DialogTitle>
            <DialogDescription className="whitespace-pre-line">
              {teamToDelete && t("delete_dialog_description", { name: teamToDelete.name })}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowDeleteDialog(false)}
              disabled={isDeleting}
            >
              {t("cancel")}
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteTeam}
              disabled={isDeleting}
            >
              {isDeleting ? t("deleting") : t("delete_button")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AdminLayout>
  );
}
