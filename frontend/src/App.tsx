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

export default function App() {
  const [version, setVersion] = useState<string | null>(null);
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [queryText, setQueryText] = useState("");

  const { history, addEntry, clearHistory } = useQueryHistory();
  const saved = useSavedQueries();
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const initialUrlHandled = useRef(false);

  /* ---- query execution ---- */

  const runQuery = useCallback(
    async (query: string) => {
      setLoading(true);
      setError(null);
      setResult(null);
      try {
        const data = await postQuery(query);
        setResult(data);
        addEntry(query, data);
      } catch (err) {
        setError((err as Error).message);
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
        setError("Invalid kwargs in URL");
        return;
      }
      setLoading(true);
      setError(null);
      setResult(null);
      try {
        const data = await postStructuredQuery(route, parsed);
        setResult(data);
        addEntry(data.query ?? route, data);
      } catch (err) {
        setError((err as Error).message);
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
  }, []);

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
    setQueryText(query);
    pushQuery(query);
    runQuery(query);
  }

  function handleSampleSelect(query: string) {
    setQueryText(query);
    pushQuery(query);
    runQuery(query);
  }

  function handleHistorySelect(query: string) {
    setQueryText(query);
    pushQuery(query);
    runQuery(query);
  }

  function handleHistoryEdit(query: string) {
    setQueryText(query);
    inputRef.current?.focus();
  }

  function handleStructuredResult(data: QueryResponse) {
    setError(null);
    setResult(data);
    addEntry(data.query ?? "(structured query)", data);
  }

  function handleStructuredError(msg: string) {
    setResult(null);
    setError(msg);
  }

  function handleStructuredQueryStart(route: string, kwargs: string) {
    pushStructured(route, kwargs);
  }

  /* ---- saved queries ---- */

  function handleSaveQuery(input: SavedQueryInput) {
    saved.add(input);
    setShowSaveDialog(false);
  }

  function handleSavedQueryRun(query: string) {
    setQueryText(query);
    pushQuery(query);
    runQuery(query);
  }

  function handleSavedQueryEdit(query: string) {
    setQueryText(query);
    inputRef.current?.focus();
  }

  function handleSaveFromHistory(query: string) {
    saved.add({ label: query.slice(0, 60), query });
  }

  const hasResult = result !== null;
  const hasError = error !== null;
  const showEmpty = !loading && !hasResult && !hasError;
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
        onChange={setQueryText}
        onSubmit={handleSubmit}
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
      status={apiOnline ? <FreshnessStatus /> : null}
      query={queryRegion}
      secondary={secondaryPanels}
      dialog={dialog}
    >
      {loading && <Loading />}
      {error && <ErrorBox message={error} />}
      {showEmpty && <EmptyState />}

      {result && (
        <section
          className={[
            styles.resultArea,
            teamTheme ? styles.teamThemedResultArea : "",
          ]
            .filter(Boolean)
            .join(" ")}
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
                  <CopyButton text={shareUrl} label="Copy Link" variant="share" />
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
    </AppShell>
  );
}
