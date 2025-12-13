"use client";

import { useState } from "react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Loader2, Trash2 } from "lucide-react";

export interface DeleteFeatureDialogProps {
  /** フィーチャーID */
  featureId: string;
  /** 表示名（オプション、IDの省略形など） */
  displayName?: string;
  /** 削除時のハンドラー */
  onDelete: () => Promise<void>;
  /** トリガーボタンのバリアント */
  triggerVariant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link";
  /** トリガーボタンのサイズ */
  triggerSize?: "default" | "sm" | "lg" | "icon";
}

/**
 * フィーチャー削除確認ダイアログ
 */
export function DeleteFeatureDialog({
  featureId,
  displayName,
  onDelete,
  triggerVariant = "destructive",
  triggerSize = "sm",
}: DeleteFeatureDialogProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await onDelete();
      setIsOpen(false);
    } catch (error) {
      console.error("Failed to delete feature:", error);
    } finally {
      setIsDeleting(false);
    }
  };

  const name = displayName || `${featureId.slice(0, 8)}...`;

  return (
    <AlertDialog open={isOpen} onOpenChange={setIsOpen}>
      <AlertDialogTrigger asChild>
        <Button variant={triggerVariant} size={triggerSize}>
          <Trash2 className="h-4 w-4" />
          {triggerSize !== "icon" && <span className="ml-2">削除</span>}
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>フィーチャーを削除しますか？</AlertDialogTitle>
          <AlertDialogDescription>
            フィーチャー「{name}」を削除します。
            <br />
            この操作は取り消すことができません。
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isDeleting}>キャンセル</AlertDialogCancel>
          <AlertDialogAction
            onClick={handleDelete}
            disabled={isDeleting}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          >
            {isDeleting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            削除
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
