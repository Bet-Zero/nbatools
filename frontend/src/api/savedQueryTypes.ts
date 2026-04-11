/** Saved query model — persisted in browser localStorage. */

export interface SavedQuery {
  id: string;
  label: string;
  /** Natural query text (primary). */
  query: string;
  /** Structured route, if saved from dev tools. */
  route: string | null;
  /** Structured kwargs JSON string, if saved from dev tools. */
  kwargs: string | null;
  tags: string[];
  pinned: boolean;
  createdAt: number;
  updatedAt: number;
}

/** Fields the user fills in when creating or editing a saved query. */
export interface SavedQueryInput {
  label: string;
  query: string;
  route?: string | null;
  kwargs?: string | null;
  tags?: string[];
  pinned?: boolean;
}
