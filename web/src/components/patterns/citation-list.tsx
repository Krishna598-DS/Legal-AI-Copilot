import Link from "next/link";
import type { Citation } from "@/lib/types";
import { Badge } from "@/design-system";
import { workspaceRead } from "@/lib/routes";

export function CitationList({
  citations,
  documentId,
}: {
  citations?: Citation[];
  documentId?: string | null;
}) {
  if (!citations?.length) return null;
  return (
    <div className="mt-2 flex flex-wrap gap-1">
      {citations.map((c, i) => {
        const label = `${c.filename || "doc"}${c.page != null ? ` · p.${c.page}` : ""}`;
        if (documentId && c.page != null) {
          return (
            <Link
              key={i}
              href={workspaceRead(documentId, {
                page: c.page,
                q: c.snippet ? c.snippet.slice(0, 80) : null,
              })}
              title={c.snippet || undefined}
            >
              <Badge variant="secondary" className="font-normal hover:border-primary/40">
                {label}
              </Badge>
            </Link>
          );
        }
        return (
          <Badge
            key={i}
            variant="secondary"
            title={c.snippet || undefined}
            className="font-normal"
          >
            {label}
          </Badge>
        );
      })}
    </div>
  );
}
