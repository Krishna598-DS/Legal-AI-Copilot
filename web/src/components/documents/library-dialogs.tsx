"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Modal } from "@/design-system";

export function RenameDocumentDialog({
  open,
  onOpenChange,
  initialName,
  onSubmit,
  busy,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  initialName: string;
  onSubmit: (name: string) => Promise<void> | void;
  busy?: boolean;
}) {
  const [name, setName] = useState(initialName);
  useEffect(() => {
    if (open) setName(initialName);
  }, [initialName, open]);

  return (
    <Modal
      open={open}
      onOpenChange={onOpenChange}
      title="Rename document"
      description="Updates the display name. The stored file is unchanged."
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={busy}>
            Cancel
          </Button>
          <Button
            variant="primary"
            disabled={busy || !name.trim()}
            onClick={() => void onSubmit(name.trim())}
          >
            {busy ? "Saving…" : "Save"}
          </Button>
        </>
      }
    >
      <Label htmlFor="rename-doc">Name</Label>
      <Input
        id="rename-doc"
        className="mt-1.5"
        value={name}
        onChange={(e) => setName(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && name.trim()) void onSubmit(name.trim());
        }}
        autoFocus
      />
    </Modal>
  );
}

export function NewFolderDialog({
  open,
  onOpenChange,
  onSubmit,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  onSubmit: (name: string) => void;
}) {
  const [name, setName] = useState("");
  useEffect(() => {
    if (open) setName("");
  }, [open]);

  return (
    <Modal
      open={open}
      onOpenChange={onOpenChange}
      title="New folder"
      description="Folders are saved on this device for now."
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            variant="primary"
            disabled={!name.trim()}
            onClick={() => {
              onSubmit(name.trim());
              onOpenChange(false);
            }}
          >
            Create
          </Button>
        </>
      }
    >
      <Label htmlFor="folder-name">Folder name</Label>
      <Input
        id="folder-name"
        className="mt-1.5"
        value={name}
        onChange={(e) => setName(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && name.trim()) {
            onSubmit(name.trim());
            onOpenChange(false);
          }
        }}
        autoFocus
      />
    </Modal>
  );
}

export function EditTagsDialog({
  open,
  onOpenChange,
  initialTags,
  onSubmit,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  initialTags: string[];
  onSubmit: (tags: string[]) => void;
}) {
  const [value, setValue] = useState("");
  useEffect(() => {
    if (open) setValue(initialTags.join(", "));
  }, [initialTags, open]);

  return (
    <Modal
      open={open}
      onOpenChange={onOpenChange}
      title="Edit tags"
      description="Comma-separated labels. Stored on this device for now."
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={() => {
              const tags = value
                .split(",")
                .map((t) => t.trim())
                .filter(Boolean);
              onSubmit(tags);
              onOpenChange(false);
            }}
          >
            Save tags
          </Button>
        </>
      }
    >
      <Label htmlFor="doc-tags">Tags</Label>
      <Input
        id="doc-tags"
        className="mt-1.5"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="nda, employment, vendor"
        autoFocus
      />
    </Modal>
  );
}
