export type DisplayMode = "public" | "debug";

export type DisplayModeInput = DisplayMode | "product" | "review";

export function normalizeDisplayMode(
  displayMode: DisplayModeInput | undefined,
): DisplayMode {
  if (displayMode === "debug" || displayMode === "review") return "debug";
  return "public";
}

export function debugEnabledFromSearch(search: string): boolean {
  const params = new URLSearchParams(search);
  const value = params.get("debug");
  return value === "1" || value?.toLowerCase() === "true";
}
