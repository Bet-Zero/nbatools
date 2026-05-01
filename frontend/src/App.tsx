import {
  type CSSProperties,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import { fetchHealth, postQuery, postStructuredQuery } from "./api/client";
import type { SavedQueryInput } from "./api/savedQueryTypes";
import type { QueryResponse } from "./api/types";
import AppShell from "./components/AppShell";
import CopyButton from "./components/CopyButton";
import DevTools from "./components/DevTools";
import EmptyState from "./components/EmptyState";
import ErrorBox from "./components/ErrorBox";
import FreshnessStatus from "./components/FreshnessStatus";
import Loading from "./components/Loading";
import QueryBar from "./components/QueryBar";
import QueryHistory from "./components/QueryHistory";
import RawJsonToggle from "./components/RawJsonToggle";
import ResultEnvelope from "./components/ResultEnvelope";
import ResultSections from "./components/ResultSections";
import SampleQueries from "./components/SampleQueries";
import SavedQueries from "./components/SavedQueries";
import SaveQueryDialog from "./components/SaveQueryDialog";
import { Badge, Button, Card, SectionHeader } from "./design-system";
import useQueryHistory from "./hooks/useQueryHistory";
import useSavedQueries from "./hooks/useSavedQueries";
import useUrlState, { type UrlParams } from "./hooks/useUrlState";
import { resolveScopedTeamTheme } from "./lib/identity";
import styles from "./App.module.css";

type RetryRequest =
  | { kind: "natural"; query: string }
  | { kind: "structured"; route: string; kwargs: string };

function safeErrorMessage(err: unknown): string {
  const raw = err instanceof Error ? err.message : String(err ?? "");
  const firstLine = raw.split(/\r?\n/)[0]?.trim();
  if (!firstLine) return "Request failed.";
  return firstLine.length > 220 ? `${firstLine.slice(0, 217)}...` : firstLine;
}

function closestShortcutBoundary(node: Node | null): Element | null {
  let current: Node | null = node;
  while (current) {
    if (
      current instanceof Element &&
      current.matches('[role="dialog"], [data-shortcut-scope="ignore"]')
    ) {
      return current;
    }
    current = current.parentNode;
  }
  return null;
}

function isEditableOutsideQueryInput(
  target: EventTarget | null,
  queryInput: HTMLInputElement | null,
): boolean {
  if (!(target instanceof Element)) return false;
  if (target instanceof HTMLTextAreaElement) return true;
  if (target instanceof HTMLSelectElement) return true;
  if (target instanceof HTMLInputElement) return target !== queryInput;
  if (target instanceof HTMLElement && target.isContentEditable) return true;
  return Boolean(target.closest('[contenteditable="true"]'));
}

function shouldIgnoreGlobalFocusShortcut(
  target: EventTarget | null,
  queryInput: HTMLInputElement | null,
): boolean {
  if (target instanceof Node && closestShortcutBoundary(target)) return true;
  const selection = window.getSelection();
  if (
    selection &&
    !selection.isCollapsed &&
    closestShortcutBoundary(selection.anchorNode)
  ) {
    return true;
  }
  return isEditableOutsideQueryInput(target, queryInput);
}

export default function App() {
  const [version, setVersion] = useState<string | null>(null);
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastRetryableRequest, setLastRetryableRequest] =
    useState<RetryRequest | null>(null);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [queryText, setQueryText] = useState("");

  const { history, addEntry, clearHistory } = useQueryHistory();
  const saved = useSavedQueries();
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const initialUrlHandled = useRef(false);
  const historyRecallIndexRef = useRef<number | null>(null);
  const historyDraftRef = useRef("");

  const resetHistoryRecall = useCallback(() => {
    historyRecallIndexRef.current = null;
    historyDraftRef.current = "";
  }, []);

  const handleQueryTextChange = useCallback(
    (value: string) => {
      resetHistoryRecall();
      setQueryText(value);
    },
    [resetHistoryRecall],
  );

  const recallPreviousQuery = useCallback(() => {
    if (history.length === 0) return false;

    const current = historyRecallIndexRef.current;
    if (current === null) {
      historyDraftRef.current = queryText;
    }

    const next = current === null ? 0 : Math.min(current + 1, history.length - 1);
    historyRecallIndexRef.current = next;
    setQueryText(history[next].query);
    return true;
  }, [history, queryText]);

  const recallNextQuery = useCallback(() => {
    const current = historyRecallIndexRef.current;
    if (current === null) return false;
    if (current >= history.length) {
      resetHistoryRecall();
      return false;
    }

    const next = current - 1;
    if (next >= 0) {
      historyRecallIndexRef.current = next;
      setQueryText(history[next].query);
      return true;
    }

    const draft = historyDraftRef.current;
    resetHistoryRecall();
    setQueryText(draft);
    return true;
  }, [history, resetHistoryRecall]);

  /* ---- query execution ---- */

  const runQuery = useCallback(
    async (query: string) => {
      setLastRetryableRequest({ kind: "natural", query });
      setLoading(true);
      setError(null);
      setResult(null);
      try {
        const data = await postQuery(query);
        setResult(data);
        addEntry(query, data);
      } catch (err) {
        setError(safeErrorMessage(err));
      } finally {
        setLoading(false);
      }
    },
    [addEntry],
  );

  const runStructuredQuery = useCallback(
    async (route: string, kwargsStr: string | null) => {
      let parsed: Record<string, unknown>;
      try {
        parsed = JSON.parse(kwargsStr || "{}");
      } catch {
        setLastRetryableRequest(null);
        setError("Invalid kwargs in URL");
        return;
      }
      setLastRetryableRequest({
        kind: "structured",
        route,
        kwargs: kwargsStr || "{}",
      });
      setLoading(true);
      setError(null);
      setResult(null);
      try {
        const data = await postStructuredQuery(route, parsed);
        setResult(data);
        addEntry(data.query ?? route, data);
      } catch (err) {
        setError(safeErrorMessage(err));
      } finally {
        setLoading(false);
      }
    },
    [addEntry],
  );

  /* ---- URL state ---- */

  // Keep refs to the latest run functions so the popstate handler never
  // captures a stale closure.
  const runQueryRef = useRef(runQuery);
  runQueryRef.current = runQuery;
  const runStructuredRef = useRef(runStructuredQuery);
  runStructuredRef.current = runStructuredQuery;

  const handleNavigate = useCallback((nav: UrlParams) => {
    resetHistoryRecall();
    if (nav.q) {
      setQueryText(nav.q);
      runQueryRef.current(nav.q);
    } else if (nav.route) {
      runStructuredRef.current(nav.route, nav.kwargs);
    } else {
      setQueryText("");
      setResult(null);
      setError(null);
    }
  }, [resetHistoryRecall]);

  const {
    params: urlParams,
    pushQuery,
    pushStructured,
    shareUrl,
  } = useUrlState(handleNavigate);

  /* ---- lifecycle ---- */

  useEffect(() => {
    fetchHealth()
      .then((h) => {
        setVersion(h.version);
        setApiOnline(true);
      })
      .catch(() => {
        setVersion(null);
        setApiOnline(false);
      });
  }, []);

  useEffect(() => {
    function handleGlobalKeyDown(event: KeyboardEvent) {
      const isFocusShortcut =
        event.key.toLowerCase() === "k" &&
        (event.metaKey || event.ctrlKey) &&
        !event.altKey &&
        !event.shiftKey;

      if (!isFocusShortcut) return;
      if (shouldIgnoreGlobalFocusShortcut(event.target, inputRef.current)) {
        return;
      }

      event.preventDefault();
      inputRef.current?.focus();
      inputRef.current?.select();
    }

    document.addEventListener("keydown", handleGlobalKeyDown);
    return () => document.removeEventListener("keydown", handleGlobalKeyDown);
  }, []);

  // Auto-run query from URL on first load.
  useEffect(() => {
    if (initialUrlHandled.current) return;
    initialUrlHandled.current = true;
    if (urlParams.q) {
      setQueryText(urlParams.q);
      runQuery(urlParams.q);
    } else if (urlParams.route) {
      runStructuredQuery(urlParams.route, urlParams.kwargs);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- fire once on mount
  }, []);

  /* ---- handlers ---- */

  function handleSubmit(query: string) {
    resetHistoryRecall();
    setQueryText(query);
    pushQuery(query);
    runQuery(query);
  }

  function handleSampleSelect(query: string) {
    resetHistoryRecall();
    setQueryText(query);
    pushQuery(query);
    runQuery(query);
  }

  function handleHistorySelect(query: string) {
    resetHistoryRecall();
    setQueryText(query);
    pushQuery(query);
    runQuery(query);
  }

  function handleHistoryEdit(query: string) {
    resetHistoryRecall();
    setQueryText(query);
    inputRef.current?.focus();
  }

  function handleStructuredResult(data: QueryResponse) {
    setError(null);
    setResult(data);
    addEntry(data.query ?? "(structured query)", data);
  }

  function handleStructuredError(
    msg: string,
    options?: { retryable?: boolean },
  ) {
    setResult(null);
    if (options?.retryable === false) {
      setLastRetryableRequest(null);
    }
    setError(safeErrorMessage(msg));
  }

  function handleStructuredQueryStart(route: string, kwargs: string) {
    setLastRetryableRequest({ kind: "structured", route, kwargs });
    pushStructured(route, kwargs);
  }

  function handleRetryError() {
    resetHistoryRecall();
    if (!lastRetryableRequest) return;
    if (lastRetryableRequest.kind === "natural") {
      setQueryText(lastRetryableRequest.query);
      runQuery(lastRetryableRequest.query);
      return;
    }
    runStructuredQuery(lastRetryableRequest.route, lastRetryableRequest.kwargs);
  }

  /* ---- saved queries ---- */

  function handleSaveQuery(input: SavedQueryInput) {
    saved.add(input);
    setShowSaveDialog(false);
  }

  function handleSavedQueryRun(query: string) {
    resetHistoryRecall();
    setQueryText(query);
    pushQuery(query);
    runQuery(query);
  }

  function handleSavedQueryEdit(query: string) {
    resetHistoryRecall();
    setQueryText(query);
    inputRef.current?.focus();
  }

  function handleSaveFromHistory(query: string) {
    saved.add({ label: query.slice(0, 60), query });
  }

  const hasResult = result !== null;
  const hasError = error !== null;
  const retryLabel =
    lastRetryableRequest?.kind === "structured"
      ? "Retry structured query"
      : "Retry query";
  const showEmpty = !loading && !hasResult && !hasError;
  const appState = loading
    ? "loading"
    : hasError
      ? "error"
      : showEmpty
        ? "empty"
        : hasResult
          ? "result"
          : "idle";
  const teamTheme = result
    ? resolveScopedTeamTheme(result.result?.metadata)
    : null;
  const teamThemeStyle = (teamTheme?.styleVars ?? undefined) as
    | CSSProperties
    | undefined;
  const teamThemedSurfaceClass = teamTheme ? styles.teamThemedSurface : "";

  const header = (
    <div className={styles.headerContent}>
      <div className={styles.brandBlock}>
        <div className={styles.logoMark} aria-hidden="true">
          NT
        </div>
        <div>
          <div className={styles.eyebrow}>NBA search workspace</div>
          <h1 className={styles.appTitle}>nbatools</h1>
          <p className={styles.tagline}>
            Natural-language lookup for players, teams, streaks, and leaders.
          </p>
        </div>
      </div>
      <div className={styles.statusStack} aria-label="API status">
        <span
          className={[
            styles.statusIndicator,
            apiOnline ? styles.online : styles.offline,
          ].join(" ")}
        >
          <span className={styles.statusDotIndicator} />
          <span>{apiOnline === false ? "API offline" : "API online"}</span>
        </span>
        <Badge variant={apiOnline === false ? "danger" : "neutral"} size="sm">
          {version
            ? `v${version}`
            : apiOnline === false
              ? "unreachable"
              : "checking"}
        </Badge>
      </div>
    </div>
  );

  const queryRegion = (
    <>
      <QueryBar
        value={queryText}
        onChange={handleQueryTextChange}
        onSubmit={handleSubmit}
        onHistoryPrevious={recallPreviousQuery}
        onHistoryNext={recallNextQuery}
        disabled={loading}
        ref={inputRef}
      />
      <SampleQueries onSelect={handleSampleSelect} />
    </>
  );

  const secondaryPanels = (
    <>
      <SavedQueries
        queries={saved.queries}
        onRun={handleSavedQueryRun}
        onEdit={handleSavedQueryEdit}
        onSave={handleSaveQuery}
        onUpdate={saved.update}
        onDelete={saved.remove}
        onPin={saved.pin}
        onClearAll={saved.clearAll}
        onExport={saved.exportJSON}
        onImport={saved.importJSON}
      />
      <QueryHistory
        entries={history}
        onSelect={handleHistorySelect}
        onEdit={handleHistoryEdit}
        onClear={clearHistory}
        onSave={handleSaveFromHistory}
      />
      <DevTools
        onResult={handleStructuredResult}
        onError={handleStructuredError}
        onLoading={setLoading}
        onQueryStart={handleStructuredQueryStart}
      />
    </>
  );

  const dialog = showSaveDialog ? (
    <SaveQueryDialog
      defaultQuery={queryText || result?.query || ""}
      defaultRoute={result?.route}
      onSave={handleSaveQuery}
      onCancel={() => setShowSaveDialog(false)}
    />
  ) : null;

  return (
    <AppShell
      header={header}
      status={
        apiOnline ? (
          <FreshnessStatus variant={showEmpty ? "banner" : "panel"} />
        ) : null
      }
      query={queryRegion}
      secondary={secondaryPanels}
      dialog={dialog}
    >
      <div className={styles.stateStack} data-app-state={appState}>
        {loading && (
          <div className={styles.stateSurface} data-state-surface="loading">
            <Loading />
          </div>
        )}
        {error && (
          <div className={styles.stateSurface} data-state-surface="error">
            <ErrorBox
              message={error}
              onRetry={lastRetryableRequest ? handleRetryError : undefined}
              retryLabel={retryLabel}
              apiOnline={apiOnline}
            />
          </div>
        )}
        {showEmpty && (
          <div className={styles.stateSurface} data-state-surface="empty">
            <EmptyState />
          </div>
        )}

        {result && (
          <section
            className={[
              styles.stateSurface,
              styles.resultArea,
              teamTheme ? styles.teamThemedResultArea : "",
            ]
              .filter(Boolean)
              .join(" ")}
            data-state-surface="result"
            data-team-theme={teamTheme?.team.teamAbbr ?? undefined}
            style={teamThemeStyle}
          >
            <Card
              className={[
                styles.resultActionsPanel,
                teamThemedSurfaceClass,
              ].join(" ")}
              depth="elevated"
              padding="md"
            >
              <SectionHeader
                eyebrow="Result"
                title="Query output"
                actions={
                  <div className={styles.resultActions}>
                    <CopyButton
                      text={shareUrl}
                      label="Copy Link"
                      variant="share"
                    />
                    <CopyButton text={result.query} label="Copy Query" />
                    <CopyButton
                      text={JSON.stringify(result, null, 2)}
                      label="Copy JSON"
                    />
                    <Button
                      type="button"
                      className={styles.saveQueryButton}
                      onClick={() => setShowSaveDialog(true)}
                      size="sm"
                      variant="secondary"
                    >
                      Save Query
                    </Button>
                  </div>
                }
              />
            </Card>

            <ResultEnvelope
              data={result}
              onAlternateSelect={handleSubmit}
              className={teamThemedSurfaceClass}
            />

            <div
              className={[styles.resultSections, teamThemedSurfaceClass].join(
                " ",
              )}
            >
              <ResultSections data={result} />
            </div>

            <RawJsonToggle data={result} />
          </section>
        )}
      </div>
    </AppShell>
  );
}
