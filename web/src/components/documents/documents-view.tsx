"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ChevronLeft, ChevronRight, FileText } from "lucide-react";
import { useAuth } from "@/components/providers/auth-provider";
import { api, apiUrl, errorMessage } from "@/lib/api";
import { routes } from "@/lib/routes";
import type { DocumentRow } from "@/lib/types";
import { useDocumentLibrary } from "@/lib/use-document-library";
import { isProcessing } from "@/lib/workspace-activity";
import { Button } from "@/components/ui/button";
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
import { EmptyState, EmptyStateAction, FadeIn, toast } from "@/design-system";
import { PageShell } from "@/components/ui/page-shell";
import { UploadZone } from "./upload-zone";
import { LibraryToolbar } from "./library-toolbar";
import { FolderMobileTrigger, FolderSidebar } from "./folder-sidebar";
import {
  LibraryGrid,
  LibraryGridSkeleton,
  LibraryList,
  LibraryListSkeleton,
} from "./library-views";
import { DocumentPreviewSheet } from "./document-preview-sheet";
import {
  EditTagsDialog,
  NewFolderDialog,
  RenameDocumentDialog,
} from "./library-dialogs";
import type { DocActions } from "./doc-actions";

export function DocumentsView() {
  const { token, user, docs, booting, refreshDocs, refreshUsage } = useAuth();
  const router = useRouter();
  const userKey = user?.email || "anon";
  const library = useDocumentLibrary(docs, userKey);

  const [previewDoc, setPreviewDoc] = useState<DocumentRow | null>(null);
  const [renameDoc, setRenameDoc] = useState<DocumentRow | null>(null);
  const [tagsDoc, setTagsDoc] = useState<DocumentRow | null>(null);
  const [deleteDoc, setDeleteDoc] = useState<DocumentRow | null>(null);
  const [newFolderOpen, setNewFolderOpen] = useState(false);
  const [renameBusy, setRenameBusy] = useState(false);
  const [loadingList, setLoadingList] = useState(true);

  useEffect(() => {
    if (booting) return;
    let cancelled = false;
    setLoadingList(true);
    refreshDocs()
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoadingList(false);
      });
    return () => {
      cancelled = true;
    };
  }, [booting, refreshDocs]);

  // Poll while any doc is processing
  const processingIds = useMemo(
    () => docs.filter((d) => isProcessing(d.status)).map((d) => d.id),
    [docs]
  );
  useEffect(() => {
    if (!processingIds.length || !token) return;
    const id = window.setInterval(() => {
      refreshDocs().catch(() => {});
    }, 2500);
    return () => window.clearInterval(id);
  }, [processingIds.length, refreshDocs, token]);

  const folderCounts = useMemo(() => {
    const byFolder: Record<string, number> = {};
    let unfiled = 0;
    docs.forEach((d) => {
      const fid = library.meta.docFolder[d.id];
      if (!fid) unfiled += 1;
      else byFolder[fid] = (byFolder[fid] || 0) + 1;
    });
    return { all: docs.length, unfiled, byFolder };
  }, [docs, library.meta.docFolder]);

  const onDownload = useCallback(
    async (doc: DocumentRow) => {
      if (!token) return;
      try {
        const res = await fetch(apiUrl(`/documents/${doc.id}/download`), {
          headers: { Authorization: `Bearer ${token}` },
          redirect: "follow",
        });
        if (!res.ok) {
          const text = await res.text();
          let data: unknown = null;
          try {
            data = text ? JSON.parse(text) : null;
          } catch {
            data = { detail: text };
          }
          throw new Error(errorMessage(data, "Download failed"));
        }
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = doc.original_filename || "document";
        a.click();
        URL.revokeObjectURL(url);
      } catch (err) {
        toast.error(err instanceof Error ? err.message : "Download failed");
      }
    },
    [token]
  );

  const actions: DocActions = useMemo(
    () => ({
      folders: library.meta.folders,
      tagsFor: (id) => library.meta.docTags[id] || [],
      onOpen: (doc) => router.push(routes.workspace(doc.id, "ask")),
      onRead: (doc) => router.push(routes.workspace(doc.id, "read")),
      onPreview: (doc) => setPreviewDoc(doc),
      onRename: (doc) => setRenameDoc(doc),
      onDownload,
      onDelete: (doc) => setDeleteDoc(doc),
      onMove: (doc, folderId) => {
        library.moveDoc(doc.id, folderId);
        toast.success(
          folderId
            ? `Moved to ${library.meta.folders.find((f) => f.id === folderId)?.name || "folder"}`
            : "Moved to Unfiled"
        );
      },
      onEditTags: (doc) => setTagsDoc(doc),
    }),
    [library, onDownload, router]
  );

  const previewFolderName = previewDoc
    ? library.meta.folders.find(
        (f) => f.id === library.meta.docFolder[previewDoc.id]
      )?.name
    : null;

  const showSkeleton = booting || loadingList;
  const emptyLibrary = !docs.length;
  const emptyFilter = docs.length > 0 && !library.filtered.length;

  return (
    <PageShell>
      <FadeIn>
        <header className="mb-6 flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
              Library
            </p>
            <h1 className="font-display mt-1 text-3xl font-bold tracking-tight text-foreground">
              Documents
            </h1>
            <p className="mt-2 max-w-xl text-sm text-muted-foreground">
              Upload agreements. Analysis stays private to your account.
            </p>
          </div>
          <FolderMobileTrigger
            folders={library.meta.folders}
            scope={library.folderScope}
            onScope={library.setFolderScope}
            counts={folderCounts}
          />
        </header>
      </FadeIn>

      <div className="flex gap-6">
        <FolderSidebar
          folders={library.meta.folders}
          scope={library.folderScope}
          onScope={library.setFolderScope}
          counts={folderCounts}
        />

        <div className="min-w-0 flex-1 space-y-5">
          <UploadZone
            token={token}
            compact={!emptyLibrary}
            onComplete={async () => {
              await refreshDocs();
              await refreshUsage();
            }}
          />

          {!emptyLibrary ? (
            <LibraryToolbar
              query={library.query}
              onQueryChange={library.setQuery}
              statusFilter={library.statusFilter}
              onStatusFilter={library.setStatusFilter}
              tagFilter={library.tagFilter}
              onTagFilter={library.setTagFilter}
              tagsCatalog={library.tagsCatalog}
              prefs={library.prefs}
              onPrefs={library.setPrefs}
              onNewFolder={() => setNewFolderOpen(true)}
              resultCount={library.filtered.length}
            />
          ) : null}

          {showSkeleton ? (
            library.prefs.view === "grid" ? (
              <LibraryGridSkeleton />
            ) : (
              <LibraryListSkeleton />
            )
          ) : emptyLibrary ? (
            <EmptyState
              icon={<FileText className="size-8" />}
              title="Your library is empty"
              description="Drop a PDF or TXT above to start asking cited questions, explaining clauses, and scanning risks."
            />
          ) : emptyFilter ? (
            <EmptyState
              title="No documents match"
              description="Try another search, filter, folder, or tag."
              action={
                <EmptyStateAction
                  variant="outline"
                  onClick={() => {
                    library.setQuery("");
                    library.setStatusFilter("all");
                    library.setTagFilter(null);
                    library.setFolderScope("all");
                  }}
                >
                  Clear filters
                </EmptyStateAction>
              }
            />
          ) : library.prefs.view === "grid" ? (
            <LibraryGrid
              docs={library.pageItems}
              token={token}
              actions={actions}
            />
          ) : (
            <LibraryList
              docs={library.pageItems}
              token={token}
              actions={actions}
            />
          )}

          {library.totalPages > 1 && !showSkeleton && !emptyFilter ? (
            <div className="flex items-center justify-between gap-3 pt-2">
              <SelectPageSize
                value={library.prefs.pageSize}
                onChange={(pageSize) =>
                  library.setPrefs({ ...library.prefs, pageSize })
                }
              />
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={library.page <= 1}
                  onClick={() => library.setPage(library.page - 1)}
                >
                  <ChevronLeft className="size-3.5" />
                  Prev
                </Button>
                <span className="text-xs text-muted-foreground">
                  Page {library.page} of {library.totalPages}
                </span>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={library.page >= library.totalPages}
                  onClick={() => library.setPage(library.page + 1)}
                >
                  Next
                  <ChevronRight className="size-3.5" />
                </Button>
              </div>
            </div>
          ) : null}
        </div>
      </div>

      <DocumentPreviewSheet
        doc={previewDoc}
        open={Boolean(previewDoc)}
        onOpenChange={(o) => {
          if (!o) setPreviewDoc(null);
        }}
        token={token}
        tags={previewDoc ? library.meta.docTags[previewDoc.id] || [] : []}
        folderName={previewFolderName}
        onOpenWorkspace={() => {
          if (previewDoc) router.push(routes.workspace(previewDoc.id, "ask"));
        }}
        onOpenReader={() => {
          if (previewDoc) router.push(routes.workspace(previewDoc.id, "read"));
        }}
        onDownload={() => {
          if (previewDoc) void onDownload(previewDoc);
        }}
      />

      <RenameDocumentDialog
        open={Boolean(renameDoc)}
        onOpenChange={(o) => {
          if (!o) setRenameDoc(null);
        }}
        initialName={renameDoc?.original_filename || ""}
        busy={renameBusy}
        onSubmit={async (name) => {
          if (!token || !renameDoc) return;
          setRenameBusy(true);
          try {
            await api(`/documents/${renameDoc.id}`, {
              method: "PATCH",
              token,
              json: { original_filename: name },
            });
            await refreshDocs();
            toast.success("Renamed");
            setRenameDoc(null);
          } catch (err) {
            toast.error(err instanceof Error ? err.message : "Rename failed");
          } finally {
            setRenameBusy(false);
          }
        }}
      />

      <EditTagsDialog
        open={Boolean(tagsDoc)}
        onOpenChange={(o) => {
          if (!o) setTagsDoc(null);
        }}
        initialTags={tagsDoc ? library.meta.docTags[tagsDoc.id] || [] : []}
        onSubmit={(tags) => {
          if (!tagsDoc) return;
          library.setTags(tagsDoc.id, tags);
          toast.success("Tags updated");
        }}
      />

      <NewFolderDialog
        open={newFolderOpen}
        onOpenChange={setNewFolderOpen}
        onSubmit={(name) => {
          library.createFolder(name);
          toast.success(`Folder “${name}” created`);
        }}
      />

      <AlertDialog
        open={Boolean(deleteDoc)}
        onOpenChange={(o) => {
          if (!o) setDeleteDoc(null);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete document?</AlertDialogTitle>
            <AlertDialogDescription>
              {deleteDoc
                ? `“${deleteDoc.original_filename}” and its chat history will be permanently removed.`
                : null}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={async () => {
                if (!token || !deleteDoc) return;
                try {
                  await api(`/documents/${deleteDoc.id}`, {
                    method: "DELETE",
                    token,
                  });
                  await refreshDocs();
                  await refreshUsage();
                  toast.success("Document deleted");
                  setDeleteDoc(null);
                } catch (err) {
                  toast.error(
                    err instanceof Error ? err.message : "Delete failed"
                  );
                }
              }}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </PageShell>
  );
}

function SelectPageSize({
  value,
  onChange,
}: {
  value: number;
  onChange: (n: number) => void;
}) {
  return (
    <label className="flex items-center gap-2 text-xs text-muted-foreground">
      Per page
      <select
        className="rounded-md border border-border bg-background px-2 py-1 text-foreground"
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      >
        <option value={12}>12</option>
        <option value={24}>24</option>
        <option value={48}>48</option>
      </select>
    </label>
  );
}
