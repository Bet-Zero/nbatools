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
import ResultEnvelope, {
  ResultContextSummary,
} from "./components/ResultEnvelope";
import ResultRenderer from "./components/results/ResultRenderer";
import SampleQueries from "./components/SampleQueries";
import SavedQueries from "./components/SavedQueries";
import SaveQueryDialog from "./components/SaveQueryDialog";
import { Badge, Button, Card, SectionHeader } from "./design-system";
import type { DisplayMode } from "./displayMode";
import useQueryHistory from "./hooks/useQueryHistory";
import useSavedQueries from "./hooks/useSavedQueries";
import useUrlState, { type UrlParams } from "./hooks/useUrlState";
import { resolveScopedTeamTheme } from "./lib/identity";
import styles from "./App.module.css";

type RetryRequest =
  | { kind: "natural"; query: string }
  | { kind: "structured"; route: string; kwargs: string };

interface ActiveRequest {
  generation: number;
  controller: AbortController;
}

interface RunRequestOptions {
  onStart?: () => void;
  invalidStructuredMessage?: string;
}

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
  const requestGenerationRef = useRef(0);
  const activeRequestRef = useRef<ActiveRequest | null>(null);
  const requestOwnerMountedRef = useRef(true);

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

  const supersedeActiveRequest = useCallback(() => {
    requestGenerationRef.current += 1;
    activeRequestRef.current?.controller.abort();
    activeRequestRef.current = null;
  }, []);

  const beginRequest = useCallback(
    (retryableRequest: RetryRequest): ActiveRequest => {
      supersedeActiveRequest();
      const activeRequest = {
        generation: requestGenerationRef.current,
        controller: new AbortController(),
      };
      activeRequestRef.current = activeRequest;
      setLastRetryableRequest(retryableRequest);
      setLoading(true);
      setError(null);
      setResult(null);
      return activeRequest;
    },
    [supersedeActiveRequest],
  );

  const ownsRequest = useCallback((generation: number): boolean => {
    return (
      requestOwnerMountedRef.current &&
      requestGenerationRef.current === generation &&
      activeRequestRef.current?.generation === generation
    );
  }, []);

  const failBeforeRequest = useCallback(
    (message: string) => {
      supersedeActiveRequest();
      setLastRetryableRequest(null);
      setLoading(false);
      setResult(null);
      setError(message);
    },
    [supersedeActiveRequest],
  );

  const runQuery = useCallback(
    async (query: string, options?: RunRequestOptions) => {
      const request = beginRequest({ kind: "natural", query });
      options?.onStart?.();
      try {
        const data = await postQuery(query, {
          signal: request.controller.signal,
        });
        if (!ownsRequest(request.generation)) return;
        setResult(data);
        addEntry(query, data);
      } catch (err) {
        if (!ownsRequest(request.generation)) return;
        const message = safeErrorMessage(err);
        setError(message);
      } finally {
        if (ownsRequest(request.generation)) {
          activeRequestRef.current = null;
          setLoading(false);
        }
      }
    },
    [addEntry, beginRequest, ownsRequest],
  );

  const runStructuredQuery = useCallback(
    async (
      route: string,
      kwargsStr: string | null,
      options?: RunRequestOptions,
    ) => {
      let parsed: Record<string, unknown>;
      try {
        parsed = JSON.parse(kwargsStr || "{}");
      } catch {
        failBeforeRequest(
          options?.invalidStructuredMessage ?? "Invalid kwargs in URL",
        );
        return;
      }
      const request = beginRequest({
        kind: "structured",
        route,
        kwargs: kwargsStr || "{}",
      });
      options?.onStart?.();
      try {
        const data = await postStructuredQuery(route, parsed, {
          signal: request.controller.signal,
        });
        if (!ownsRequest(request.generation)) return;
        setResult(data);
        addEntry(data.query ?? route, data);
      } catch (err) {
        if (!ownsRequest(request.generation)) return;
        setError(safeErrorMessage(err));
      } finally {
        if (ownsRequest(request.generation)) {
          activeRequestRef.current = null;
          setLoading(false);
        }
      }
    },
    [addEntry, beginRequest, failBeforeRequest, ownsRequest],
  );

  /* ---- URL state ---- */

  // Keep refs to the latest run functions so the popstate handler never
  // captures a stale closure.
  const runQueryRef = useRef(runQuery);
  runQueryRef.current = runQuery;
  const runStructuredRef = useRef(runStructuredQuery);
  runStructuredRef.current = runStructuredQuery;

  const handleNavigate = useCallback(
    (nav: UrlParams) => {
      resetHistoryRecall();
      if (nav.q) {
        setQueryText(nav.q);
        void runQueryRef.current(nav.q);
      } else if (nav.route) {
        setQueryText("");
        void runStructuredRef.current(nav.route, nav.kwargs);
      } else {
        supersedeActiveRequest();
        setQueryText("");
        setLastRetryableRequest(null);
        setLoading(false);
        setResult(null);
        setError(null);
      }
    },
    [resetHistoryRecall, supersedeActiveRequest],
  );

  const {
    params: urlParams,
    pushQuery,
    pushStructured,
    shareUrl,
  } = useUrlState(handleNavigate);

  /* ---- lifecycle ---- */

  useEffect(() => {
    requestOwnerMountedRef.current = true;
    return () => {
      requestOwnerMountedRef.current = false;
      initialUrlHandled.current = false;
      supersedeActiveRequest();
    };
  }, [supersedeActiveRequest]);

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
      void runQuery(urlParams.q);
    } else if (urlParams.route) {
      setQueryText("");
      void runStructuredQuery(urlParams.route, urlParams.kwargs);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- fire once on mount
  }, []);

  /* ---- handlers ---- */

  function launchNaturalQuery(query: string) {
    resetHistoryRecall();
    setQueryText(query);
    void runQuery(query, { onStart: () => pushQuery(query) });
  }

  function handleSubmit(query: string) {
    launchNaturalQuery(query);
  }

  function handleSampleSelect(query: string) {
    launchNaturalQuery(query);
  }

  function handleHistorySelect(query: string) {
    launchNaturalQuery(query);
  }

  function handleHistoryEdit(query: string) {
    resetHistoryRecall();
    setQueryText(query);
    inputRef.current?.focus();
  }

  function handleStructuredQueryRun(route: string, kwargs: string) {
    resetHistoryRecall();
    void runStructuredQuery(route, kwargs, {
      invalidStructuredMessage: "Invalid JSON in kwargs",
      onStart: () => {
        setQueryText("");
        pushStructured(route, kwargs);
      },
    });
  }

  function handleRetryError() {
    resetHistoryRecall();
    if (!lastRetryableRequest) return;
    if (lastRetryableRequest.kind === "natural") {
      setQueryText(lastRetryableRequest.query);
      void runQuery(lastRetryableRequest.query);
      return;
    }
    setQueryText("");
    void runStructuredQuery(
      lastRetryableRequest.route,
      lastRetryableRequest.kwargs,
    );
  }

  /* ---- saved queries ---- */

  function handleSaveQuery(input: SavedQueryInput) {
    saved.add(input);
    setShowSaveDialog(false);
  }

  function handleSavedQueryRun(query: string) {
    launchNaturalQuery(query);
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
  const displayMode: DisplayMode = urlParams.debug ? "debug" : "public";
  const isDebugMode = displayMode === "debug";
  const headerStatus =
    isDebugMode || apiOnline === false ? (
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
    ) : null;

  const header = (
    <div className={styles.headerContent}>
      <div className={styles.brandBlock}>
        <div className={styles.logoMark} aria-hidden="true">
          NT
        </div>
        <div>
          <h1 className={styles.appTitle}>nbatools</h1>
          <p className={styles.tagline}>
            Ask a supported NBA stat question. Get a straight answer.
          </p>
        </div>
      </div>
      {headerStatus}
    </div>
  );

  const queryRegion = (
    <QueryBar
      value={queryText}
      onChange={handleQueryTextChange}
      onSubmit={handleSubmit}
      onHistoryPrevious={recallPreviousQuery}
      onHistoryNext={recallNextQuery}
      disabled={loading}
      ref={inputRef}
    />
  );

  const secondaryPanels = (
    <>
      <SampleQueries onSelect={handleSampleSelect} displayMode={displayMode} />
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
        displayMode={displayMode}
      />
      {isDebugMode && <DevTools onRun={handleStructuredQueryRun} />}
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
  const resultActions = result ? (
    <div
      className={[
        styles.resultActions,
        !isDebugMode ? styles.publicResultActions : "",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <CopyButton text={shareUrl} label="Copy Link" variant="share" />
      {isDebugMode && <CopyButton text={result.query} label="Copy Query" />}
      {isDebugMode && (
        <CopyButton text={JSON.stringify(result, null, 2)} label="Copy JSON" />
      )}
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
            aria-live="polite"
            aria-label="Query result"
            data-team-theme={teamTheme?.team.teamAbbr ?? undefined}
            style={teamThemeStyle}
          >
            {isDebugMode ? (
              <>
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
                    actions={resultActions}
                  />
                </Card>

                <ResultEnvelope
                  data={result}
                  onAlternateSelect={handleSubmit}
                  className={teamThemedSurfaceClass}
                  displayMode={displayMode}
                />

                <div
                  className={[
                    styles.resultSections,
                    teamThemedSurfaceClass,
                  ].join(" ")}
                >
                  <ResultRenderer data={result} displayMode={displayMode} />
                </div>

                <RawJsonToggle data={result} />
              </>
            ) : (
              <>
                <div
                  className={[
                    styles.resultSections,
                    teamThemedSurfaceClass,
                  ].join(" ")}
                >
                  <ResultRenderer
                    data={result}
                    displayMode={displayMode}
                    resultContext={
                      result.result_status === "ok" ? (
                        <ResultContextSummary data={result} />
                      ) : null
                    }
                  />
                </div>

                {resultActions && (
                  <Card
                    className={[
                      styles.resultActionsPanel,
                      styles.secondaryActionsPanel,
                      teamThemedSurfaceClass,
                    ].join(" ")}
                    depth="input"
                    padding="sm"
                    aria-label="Result actions"
                  >
                    {resultActions}
                  </Card>
                )}

                {result.result_status === "ok" && (
                  <ResultEnvelope
                    data={result}
                    onAlternateSelect={handleSubmit}
                    className={teamThemedSurfaceClass}
                    displayMode={displayMode}
                  />
                )}
              </>
            )}
          </section>
        )}
      </div>
    </AppShell>
  );
}
