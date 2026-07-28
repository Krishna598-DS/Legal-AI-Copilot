/** Cross-component signal to open the workspace command search (owned by TopNav). */
export const OPEN_SEARCH_EVENT = "ldi:open-search";

export function openWorkspaceSearch() {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent(OPEN_SEARCH_EVENT));
}
