"use client";

import {
  Download,
  Eye,
  FolderInput,
  MoreHorizontal,
  Pencil,
  Tags,
  Trash2,
  ExternalLink,
  BookOpen,
} from "lucide-react";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuSub,
  ContextMenuSubContent,
  ContextMenuSubTrigger,
  ContextMenuTrigger,
} from "@/components/ui/context-menu";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import type { DocumentRow } from "@/lib/types";
import type { DocActions } from "./doc-actions";

export function DocumentContextMenu({
  doc,
  actions,
  children,
}: {
  doc: DocumentRow;
  actions: DocActions;
  children: React.ReactNode;
}) {
  return (
    <ContextMenu>
      <ContextMenuTrigger asChild>{children}</ContextMenuTrigger>
      <ContextMenuContent>
        <ContextMenuItem onSelect={() => actions.onOpen(doc)}>
          <ExternalLink /> Open in workspace
        </ContextMenuItem>
        <ContextMenuItem onSelect={() => actions.onRead(doc)}>
          <BookOpen /> Read document
        </ContextMenuItem>
        <ContextMenuItem onSelect={() => actions.onPreview(doc)}>
          <Eye /> Preview
        </ContextMenuItem>
        <ContextMenuItem onSelect={() => actions.onRename(doc)}>
          <Pencil /> Rename
        </ContextMenuItem>
        <ContextMenuSub>
          <ContextMenuSubTrigger>
            <FolderInput className="size-4" /> Move to folder
          </ContextMenuSubTrigger>
          <ContextMenuSubContent>
            <ContextMenuItem onSelect={() => actions.onMove(doc, null)}>
              Unfiled
            </ContextMenuItem>
            {actions.folders.map((f) => (
              <ContextMenuItem
                key={f.id}
                onSelect={() => actions.onMove(doc, f.id)}
              >
                {f.name}
              </ContextMenuItem>
            ))}
          </ContextMenuSubContent>
        </ContextMenuSub>
        <ContextMenuItem onSelect={() => actions.onEditTags(doc)}>
          <Tags /> Edit tags
        </ContextMenuItem>
        <ContextMenuItem onSelect={() => actions.onDownload(doc)}>
          <Download /> Download
        </ContextMenuItem>
        <ContextMenuSeparator />
        <ContextMenuItem
          variant="destructive"
          onSelect={() => actions.onDelete(doc)}
        >
          <Trash2 /> Delete
        </ContextMenuItem>
      </ContextMenuContent>
    </ContextMenu>
  );
}

export function DocumentMoreMenu({
  doc,
  actions,
}: {
  doc: DocumentRow;
  actions: DocActions;
}) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          size="icon"
          variant="ghost"
          className="size-8 shrink-0"
          aria-label="Document actions"
          onClick={(e) => e.stopPropagation()}
        >
          <MoreHorizontal className="size-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" onClick={(e) => e.stopPropagation()}>
        <DropdownMenuItem onSelect={() => actions.onOpen(doc)}>
          <ExternalLink /> Open in workspace
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => actions.onRead(doc)}>
          <BookOpen /> Read document
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => actions.onPreview(doc)}>
          <Eye /> Preview
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => actions.onRename(doc)}>
          <Pencil /> Rename
        </DropdownMenuItem>
        <DropdownMenuSub>
          <DropdownMenuSubTrigger>
            <FolderInput /> Move to folder
          </DropdownMenuSubTrigger>
          <DropdownMenuSubContent>
            <DropdownMenuItem onSelect={() => actions.onMove(doc, null)}>
              Unfiled
            </DropdownMenuItem>
            {actions.folders.map((f) => (
              <DropdownMenuItem
                key={f.id}
                onSelect={() => actions.onMove(doc, f.id)}
              >
                {f.name}
              </DropdownMenuItem>
            ))}
          </DropdownMenuSubContent>
        </DropdownMenuSub>
        <DropdownMenuItem onSelect={() => actions.onEditTags(doc)}>
          <Tags /> Edit tags
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => actions.onDownload(doc)}>
          <Download /> Download
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          variant="destructive"
          onSelect={() => actions.onDelete(doc)}
        >
          <Trash2 /> Delete
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
