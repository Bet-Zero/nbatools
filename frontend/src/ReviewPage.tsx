import { startTransition, useEffect, useState } from "react";
import { fetchDevFixtures, postQuery } from "./api/client";
import type { DevFixture, QueryResponse } from "./api/types";
import ResultEnvelope from "./components/ResultEnvelope";
import ResultRenderer from "./components/results/ResultRenderer";
import {
  classifyResultShape,
  resultShapeOrderIndex,
  type ResultShapeKey,
} from "./components/results/resultShapes";
import styles from "./ReviewPage.module.css";

interface ReviewResultState {
  data?: QueryResponse;
  error?: string;
}

interface ShapeEntry {
  fixture: DevFixture;
  index: number;
  result: QueryResponse;
  shape: ReturnType<typeof classifyResultShape>;
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
  const [showOneExamplePerShape, setShowOneExamplePerShape] = useState(true);
  const [collapsedShapes, setCollapsedShapes] = useState<
    Partial<Record<ResultShapeKey, boolean>>
  >({});
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

  const groupedShapes = new Map<ResultShapeKey, ShapeEntry[]>();
  const pendingFixtures: DevFixture[] = [];
  const failedFixtures: Array<{ fixture: DevFixture; error: string }> = [];

  fixtures.forEach((fixture, index) => {
    const result = results[index];
    if (result?.data) {
      const shape = classifyResultShape(result.data);
      const group = groupedShapes.get(shape.key) ?? [];
      group.push({ fixture, index, result: result.data, shape });
      groupedShapes.set(shape.key, group);
      return;
    }

    if (result?.error) {
      failedFixtures.push({ fixture, error: result.error });
      return;
    }

    pendingFixtures.push(fixture);
  });

  const sortedShapeGroups = Array.from(groupedShapes.entries()).sort(
    ([left], [right]) =>
      resultShapeOrderIndex(left) - resultShapeOrderIndex(right),
  );

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
          <p>
            Internal sweep review grouped by the renderer shape each query
            produces.
          </p>
        </header>

        {!fixturesLoading && !fixturesError && (
          <div className={styles.controls}>
            <label className={styles.toggle}>
              <input
                type="checkbox"
                checked={showOneExamplePerShape}
                onChange={(event) =>
                  setShowOneExamplePerShape(event.target.checked)
                }
              />
              <span>Show one example per shape</span>
            </label>
            <p className={styles.meta}>
              {sortedShapeGroups.length} shapes loaded
            </p>
          </div>
        )}

        {fixturesLoading && (
          <p className={styles.placeholder}>Loading fixtures...</p>
        )}
        {fixturesError && <p className={styles.error}>{fixturesError}</p>}

        {!fixturesLoading && pendingFixtures.length > 0 && (
          <section className={styles.statusPanel}>
            <h2>Loading</h2>
            <p>
              {pendingFixtures.length} fixture
              {pendingFixtures.length === 1 ? " is" : "s are"} still loading.
            </p>
          </section>
        )}

        {!fixturesLoading && failedFixtures.length > 0 && (
          <section className={styles.statusPanel}>
            <h2>Request Failures</h2>
            <ul className={styles.failureList}>
              {failedFixtures.map(({ fixture, error }) => (
                <li key={fixture.case_id}>
                  <strong>{fixture.query}</strong>
                  <span>{error}</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {sortedShapeGroups.map(([shapeKey, entries]) => {
          const collapsed = collapsedShapes[shapeKey] === true;
          const visibleEntries = showOneExamplePerShape
            ? entries.slice(0, 1)
            : entries;

          return (
            <section key={shapeKey} className={styles.group}>
              <h2 className={styles.groupHeading}>
                <button
                  type="button"
                  className={styles.groupToggle}
                  aria-expanded={!collapsed}
                  onClick={() =>
                    setCollapsedShapes((current) => ({
                      ...current,
                      [shapeKey]: !current[shapeKey],
                    }))
                  }
                >
                  <span className={styles.groupTitle}>
                    {entries[0].shape.name}
                  </span>
                  <span className={styles.groupCount}>
                    {entries.length} fixture{entries.length === 1 ? "" : "s"}
                  </span>
                </button>
              </h2>

              <p className={styles.groupDescription}>
                {entries[0].shape.description}
              </p>

              {!collapsed && (
                <div className={styles.groupBody}>
                  {showOneExamplePerShape && entries.length > 1 && (
                    <p className={styles.meta}>
                      Showing 1 representative fixture. Turn the toggle off to
                      inspect all {entries.length}.
                    </p>
                  )}

                  {visibleEntries.map(({ fixture, index, result }) => (
                    <article key={fixture.case_id} className={styles.block}>
                      <h3 className={styles.queryTitle}>{fixture.query}</h3>
                      <p className={styles.caseMeta}>Fixture {index + 1}</p>
                      <ResultEnvelope data={result} />
                      <div className={styles.resultSections}>
                        <ResultRenderer data={result} />
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </section>
          );
        })}
      </div>
    </main>
  );
}
