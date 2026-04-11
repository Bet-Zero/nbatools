import { useCallback, useEffect, useRef, useState } from "react";
import { fetchHealth, postQuery } from "./api/client";
import type { QueryResponse } from "./api/types";
import DevTools from "./components/DevTools";
import ErrorBox from "./components/ErrorBox";
import Loading from "./components/Loading";
import QueryBar from "./components/QueryBar";
import RawJsonToggle from "./components/RawJsonToggle";
import ResultEnvelope from "./components/ResultEnvelope";
import ResultSections from "./components/ResultSections";
import SampleQueries from "./components/SampleQueries";
import "./App.css";

export default function App() {
  const [version, setVersion] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<QueryResponse | null>(null);

  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    fetchHealth()
      .then((h) => setVersion(h.version))
      .catch(() => setVersion(null));
  }, []);

  const runQuery = useCallback(async (query: string) => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await postQuery(query);
      setResult(data);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  function handleSampleSelect(query: string) {
    if (inputRef.current) {
      const setter = Object.getOwnPropertyDescriptor(
        window.HTMLInputElement.prototype,
        "value",
      );
      setter?.set?.call(inputRef.current, query);
      inputRef.current.dispatchEvent(new Event("input", { bubbles: true }));
    }
    runQuery(query);
  }

  function handleStructuredResult(data: QueryResponse) {
    setError(null);
    setResult(data);
  }

  function handleStructuredError(msg: string) {
    setResult(null);
    setError(msg);
  }

  return (
    <div className="container">
      <header>
        <h1>nbatools</h1>
        <span className="version">
          {version ? `v${version}` : "(API offline)"}
        </span>
      </header>

      <QueryBar onSubmit={runQuery} disabled={loading} ref={inputRef} />
      <SampleQueries onSelect={handleSampleSelect} />

      {loading && <Loading />}
      {error && <ErrorBox message={error} />}

      {result && (
        <div id="result-area">
          <ResultEnvelope data={result} />
          <ResultSections data={result} />
          <RawJsonToggle data={result} />
        </div>
      )}

      <DevTools
        onResult={handleStructuredResult}
        onError={handleStructuredError}
        onLoading={setLoading}
      />
    </div>
  );
}
