import type { DashboardAction } from "@/lib/types";
import { routes, type WorkspaceMode } from "@/lib/routes";

export function actionDestination(
  action: DashboardAction,
  latestReadyId: string | null
): { href: string; mode?: WorkspaceMode } {
  switch (action.id) {
    case "upload":
      return { href: routes.documents };
    case "search":
      return { href: routes.documents };
    case "ask":
      return {
        href: latestReadyId ? routes.workspace(latestReadyId, "ask") : routes.documents,
        mode: "ask",
      };
    case "explain":
      return {
        href: latestReadyId
          ? routes.workspace(latestReadyId, "explain")
          : routes.documents,
        mode: "explain",
      };
    case "risks":
      return {
        href: latestReadyId ? routes.workspace(latestReadyId, "risks") : routes.documents,
        mode: "risks",
      };
    case "consult":
      return {
        href: latestReadyId
          ? routes.workspace(latestReadyId, "consult")
          : routes.documents,
        mode: "consult",
      };
    case "expert":
      return {
        href: latestReadyId
          ? routes.workspace(latestReadyId, "connect")
          : routes.professionals(),
        mode: "connect",
      };
    case "compare":
      return {
        href: latestReadyId
          ? routes.workspace(latestReadyId, "compare")
          : routes.documents,
        mode: "compare",
      };
    default:
      return {
        href: latestReadyId ? routes.workspace(latestReadyId, "ask") : routes.documents,
        mode: "ask",
      };
  }
}

export function runAction(
  action: DashboardAction,
  latestReadyId: string | null,
  navigate: (href: string) => void
) {
  const dest = actionDestination(action, latestReadyId);
  if (action.prompt && dest.href.includes("/workspace")) {
    sessionStorage.setItem("copilot_ask_draft", action.prompt);
  }
  navigate(dest.href);
}
