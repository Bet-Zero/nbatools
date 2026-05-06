import { startTransition, useEffect, useState } from "react";
import { fetchDevFixtures, postQuery } from "./api/client";
import type { DevFixture, QueryResponse } from "./api/types";
import ResultEnvelope from "./components/ResultEnvelope";
import ResultRenderer from "./components/results/ResultRenderer";
import styles from "./ReviewPage.module.css";

interface ReviewResultState {
  data?: QueryResponse;
  error?: string;
}

function safeErrorMessage(err: unknown): string {
  const raw = err instanceof Error ? err.message : String(err ?? "");
  const firstLine = raw.split(/\r?\n/)[0]?.trim();
  if (!firstLine) return "Request failed.";
  return firstLine.length > 220 ? `${firstLine.slice(0, 217)}...` : firstLine;
}

export default function ReviewPage() {
  const [fixtures, setFixtures] = useState<DevFixture[]>([]);
  const [sourcePath, setSourcePath] = useState<string | null>(null);
  const [results, setResults] = useState<Record<number, ReviewResultState>>({});
  const [loadedCount, setLoadedCount] = useState(0);
  const [fixturesLoading, setFixturesLoading] = useState(true);
  const [fixturesError, setFixturesError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadFixtures() {
      try {
        const data = await fetchDevFixtures();
        if (cancelled) return;

        setFixtures(data.fixtures);
        setSourcePath(data.source_path);
        setLoadedCount(0);
        setResults({});
        setFixturesError(null);
        setFixturesLoading(false);

        data.fixtures.forEach((fixture, index) => {
          postQuery(fixture.query)
            .then((response) => {
              if (cancelled) return;
              startTransition(() => {
                setResults((current) => ({
                  ...current,
                  [index]: { data: response },
                }));
                setLoadedCount((current) => current + 1);
              });
            })
            .catch((error) => {
              if (cancelled) return;
              startTransition(() => {
                setResults((current) => ({
                  ...current,
                  [index]: { error: safeErrorMessage(error) },
                }));
                setLoadedCount((current) => current + 1);
              });
            });
        });
      } catch (error) {
        if (cancelled) return;
        setFixturesError(safeErrorMessage(error));
        setFixturesLoading(false);
      }
    }

    loadFixtures();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main className={styles.page}>
      <div className={styles.progressBar} aria-live="polite">
        <strong>
          {loadedCount} / {fixtures.length} loaded
        </strong>
        {sourcePath && (
          <span className={styles.source}>Source: {sourcePath}</span>
        )}
      </div>

      <div className={styles.content}>
        <header className={styles.header}>
          <h1>Parser Review</h1>
          <p>Internal sweep review for parser example queries.</p>
        </header>

        {fixturesLoading && (
          <p className={styles.placeholder}>Loading fixtures...</p>
        )}
        {fixturesError && <p className={styles.error}>{fixturesError}</p>}

        {fixtures.map((fixture, index) => {
          const result = results[index];
          return (
            <section key={fixture.case_id} className={styles.block}>
              <h2>{fixture.query}</h2>

              {result?.data ? (
                <>
                  <ResultEnvelope data={result.data} />
                  <div className={styles.resultSections}>
                    <ResultRenderer data={result.data} />
                  </div>
                </>
              ) : result?.error ? (
                <p className={styles.error}>{result.error}</p>
              ) : (
                <p className={styles.placeholder}>Loading result...</p>
              )}

              <hr className={styles.divider} />
            </section>
          );
        })}
      </div>
    </main>
  );
}
