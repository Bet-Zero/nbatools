import { useCallback, useEffect, useRef, useState } from "react";
import { fetchHealth, postQuery } from "./api/client";
import type { QueryResponse } from "./api/types";
import CopyButton from "./components/CopyButton";
import DevTools from "./components/DevTools";
import EmptyState from "./components/EmptyState";
import ErrorBox from "./components/ErrorBox";
import Loading from "./components/Loading";
import QueryBar from "./components/QueryBar";
import QueryHistory from "./components/QueryHistory";
import RawJsonToggle from "./components/RawJsonToggle";
import ResultEnvelope from "./components/ResultEnvelope";
import ResultSections from "./components/ResultSections";
import SampleQueries from "./components/SampleQueries";
import useQueryHistory from "./hooks/useQueryHistory";
import "./App.css";

export default function App() {
  const [version, setVersion] = useState<string | null>(null);
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [queryText, setQueryText] = useState("");

  const { history, addEntry, clearHistory } = useQueryHistory();
  const inputRef = useRef<HTMLInputElement | null>(null);

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

  function handleSubmit(query: string) {
    setQueryText(query);
    runQuery(query);
  }

  function handleSampleSelect(query: string) {
    setQueryText(query);
    runQuery(query);
  }

  function handleHistorySelect(query: string) {
    setQueryText(query);
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

  const hasResult = result !== null;
  const hasError = error !== null;
  const showEmpty = !loading && !hasResult && !hasError;

  return (
    <div className="app-shell">
      {/* Header */}
      <header className="app-header">
        <div className="header-left">
          <h1 className="app-title">nbatools</h1>
          <span
            className={`status-indicator ${apiOnline ? "online" : "offline"}`}
          >
            <span className="status-dot-indicator" />
            {version
              ? `v${version}`
              : apiOnline === false
                ? "API offline"
                : "…"}
          </span>
        </div>
      </header>

      {/* Query area */}
      <section className="query-area">
        <QueryBar
          value={queryText}
          onChange={setQueryText}
          onSubmit={handleSubmit}
          disabled={loading}
          ref={inputRef}
        />
        <SampleQueries onSelect={handleSampleSelect} />
      </section>

      {/* Loading */}
      {loading && <Loading />}

      {/* Error */}
      {error && <ErrorBox message={error} />}

      {/* Empty state */}
      {showEmpty && <EmptyState />}

      {/* Result area */}
      {result && (
        <section className="result-area">
          <ResultEnvelope data={result} />

          <div className="result-actions">
            <CopyButton
              text={result.query}
              label="Copy Query"
              className="copy-query-btn"
            />
            <CopyButton
              text={JSON.stringify(result, null, 2)}
              label="Copy JSON"
              className="copy-json-btn"
            />
          </div>

          <div className="result-content">
            <ResultSections data={result} />
          </div>

          <RawJsonToggle data={result} />
        </section>
      )}

      {/* Query history */}
      <QueryHistory
        entries={history}
        onSelect={handleHistorySelect}
        onEdit={handleHistoryEdit}
        onClear={clearHistory}
      />

      {/* Developer tools */}
      <DevTools
        onResult={handleStructuredResult}
        onError={handleStructuredError}
        onLoading={setLoading}
      />
    </div>
  );
}
