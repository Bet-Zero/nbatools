import { startTransition, useEffect, useRef, useState } from "react";
import { fetchDevFixtures, postQuery } from "./api/client";
import type { DevFixture, QueryResponse } from "./api/types";
import ResultEnvelope from "./components/ResultEnvelope";
import ResultRenderer from "./components/results/ResultRenderer";
import {
  classifyResultShape,
  resultShapeOrderIndex,
  type ResultShapeKey,
} from "./components/results/resultShapes";
import { Button } from "./design-system";
import {
  downloadReviewScreenshots,
  type ReviewScreenshotProgress,
} from "./lib/reviewScreenshots";
import styles from "./ReviewPage.module.css";

interface ReviewResultState {
  data?: QueryResponse;
  error?: string;
  cached?: boolean;
}

interface ShapeEntry {
  fixture: DevFixture;
  index: number;
  result: QueryResponse;
  shape: ReturnType<typeof classifyResultShape>;
}

interface IndexedFixture {
  fixture: DevFixture;
  index: number;
}

interface RunProgress {
  completed: number;
  total: number;
  label: string;
}

const REVIEW_CACHE_VERSION = "v1";
const REVIEW_CACHE_PREFIX = `nbatools.review:${REVIEW_CACHE_VERSION}:`;
const REVIEW_CONCURRENCY_LIMIT = 3;

function safeErrorMessage(err: unknown): string {
  const raw = err instanceof Error ? err.message : String(err ?? "");
  const firstLine = raw.split(/\r?\n/)[0]?.trim();
  if (!firstLine) return "Request failed.";
  return firstLine.length > 220 ? `${firstLine.slice(0, 217)}...` : firstLine;
}

function getReviewCacheKey(fixture: DevFixture): string {
  return `${REVIEW_CACHE_PREFIX}${fixture.case_id}:${fixture.query}`;
}

function readCachedReviewResult(
  fixture: DevFixture,
): ReviewResultState | null {
  try {
    const raw = window.localStorage.getItem(getReviewCacheKey(fixture));
    if (!raw) return null;

    const parsed = JSON.parse(raw) as ReviewResultState;
    if (!parsed || typeof parsed !== "object") return null;
    if (parsed.data) return { data: parsed.data, cached: true };
    if (typeof parsed.error === "string") {
      return { error: parsed.error, cached: true };
    }
  } catch {
    return null;
  }

  return null;
}

function writeCachedReviewResult(
  fixture: DevFixture,
  result: ReviewResultState,
): void {
  if (!result.data && !result.error) return;

  try {
    window.localStorage.setItem(
      getReviewCacheKey(fixture),
      JSON.stringify({ data: result.data, error: result.error }),
    );
  } catch {
    // Storage can be disabled or full; review mode should still keep working.
  }
}

function clearReviewCache(): void {
  try {
    const keys = [];
    for (let index = 0; index < window.localStorage.length; index += 1) {
      const key = window.localStorage.key(index);
      if (key?.startsWith(REVIEW_CACHE_PREFIX)) keys.push(key);
    }
    keys.forEach((key) => window.localStorage.removeItem(key));
  } catch {
    // Ignore storage failures; the visible results are still cleared by state.
  }
}

export default function ReviewPage() {
  const captureTargetsRef = useRef(new Map<ResultShapeKey, HTMLElement>());
  const runTokenRef = useRef(0);
  const runningRef = useRef(false);
  const mountedRef = useRef(true);
  const abortControllersRef = useRef(new Set<AbortController>());
  const [fixtures, setFixtures] = useState<DevFixture[]>([]);
  const [sourcePath, setSourcePath] = useState<string | null>(null);
  const [results, setResults] = useState<Record<number, ReviewResultState>>({});
  const [hasRun, setHasRun] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [runProgress, setRunProgress] = useState<RunProgress | null>(null);
  const [useCachedResults, setUseCachedResults] = useState(true);
  const [showOneExamplePerShape, setShowOneExamplePerShape] = useState(true);
  const [collapsedShapes, setCollapsedShapes] = useState<
    Partial<Record<ResultShapeKey, boolean>>
  >({});
  const [fixturesLoading, setFixturesLoading] = useState(true);
  const [fixturesError, setFixturesError] = useState<string | null>(null);
  const [captureProgress, setCaptureProgress] =
    useState<ReviewScreenshotProgress | null>(null);
  const [captureError, setCaptureError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    mountedRef.current = true;

    async function loadFixtures() {
      try {
        const data = await fetchDevFixtures();
        if (cancelled) return;

        setFixtures(data.fixtures);
        setSourcePath(data.source_path);
        setResults({});
        setHasRun(false);
        setRunProgress(null);
        setFixturesError(null);
        setFixturesLoading(false);
      } catch (error) {
        if (cancelled) return;
        setFixturesError(safeErrorMessage(error));
        setFixturesLoading(false);
      }
    }

    loadFixtures();
    return () => {
      cancelled = true;
      mountedRef.current = false;
      runTokenRef.current += 1;
      runningRef.current = false;
      abortControllersRef.current.forEach((controller) => controller.abort());
      abortControllersRef.current.clear();
    };
  }, []);

  const loadedCount = Object.keys(results).length;

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

    if (hasRun) {
      pendingFixtures.push(fixture);
    }
  });

  const sortedShapeGroups = Array.from(groupedShapes.entries()).sort(
    ([left], [right]) =>
      resultShapeOrderIndex(left) - resultShapeOrderIndex(right),
  );
  const isCapturing = captureProgress !== null;
  const screenshotsReady = sortedShapeGroups.length > 0;
  const screenshotButtonLabel = captureProgress
    ? `Capturing ${captureProgress.current}/${captureProgress.total}...`
    : "Download all screenshots";
  const canRun = !fixturesLoading && !fixturesError && fixtures.length > 0;

  function commitFixtureResult(
    index: number,
    result: ReviewResultState,
    token: number,
  ) {
    if (!mountedRef.current || runTokenRef.current !== token) return;

    startTransition(() => {
      setResults((current) => ({
        ...current,
        [index]: result,
      }));
      setRunProgress((current) =>
        current
          ? {
              ...current,
              completed: Math.min(current.completed + 1, current.total),
            }
          : current,
      );
    });
  }

  function stopRun() {
    runTokenRef.current += 1;
    abortControllersRef.current.forEach((controller) => controller.abort());
    abortControllersRef.current.clear();
    runningRef.current = false;
    setIsRunning(false);
    setRunProgress(null);
  }

  async function runFixtures(
    indexedFixtures: IndexedFixture[],
    label: string,
  ): Promise<void> {
    if (indexedFixtures.length === 0 || runningRef.current) return;

    const token = runTokenRef.current + 1;
    runTokenRef.current = token;
    runningRef.current = true;
    setHasRun(true);
    setIsRunning(true);
    setRunProgress({ completed: 0, total: indexedFixtures.length, label });
    setCaptureError(null);

    let nextIndex = 0;

    async function runOne({ fixture, index }: IndexedFixture) {
      if (runTokenRef.current !== token || !mountedRef.current) return;

      if (useCachedResults) {
        const cached = readCachedReviewResult(fixture);
        if (cached) {
          commitFixtureResult(index, cached, token);
          return;
        }
      }

      const controller = new AbortController();
      abortControllersRef.current.add(controller);
      try {
        const response = await postQuery(fixture.query, {
          signal: controller.signal,
        });
        const result = { data: response };
        writeCachedReviewResult(fixture, result);
        commitFixtureResult(index, result, token);
      } catch (error) {
        if (controller.signal.aborted || runTokenRef.current !== token) return;
        const result = { error: safeErrorMessage(error) };
        writeCachedReviewResult(fixture, result);
        commitFixtureResult(index, result, token);
      } finally {
        abortControllersRef.current.delete(controller);
      }
    }

    async function worker() {
      while (runTokenRef.current === token && mountedRef.current) {
        const entry = indexedFixtures[nextIndex];
        nextIndex += 1;
        if (!entry) return;
        await runOne(entry);
      }
    }

    const workerCount = Math.min(
      REVIEW_CONCURRENCY_LIMIT,
      indexedFixtures.length,
    );
    await Promise.all(Array.from({ length: workerCount }, () => worker()));

    if (mountedRef.current && runTokenRef.current === token) {
      runningRef.current = false;
      setIsRunning(false);
    }
  }

  function handleRun(limit?: number) {
    const selected = fixtures
      .slice(0, limit)
      .map((fixture, index) => ({ fixture, index }));
    void runFixtures(
      selected,
      limit ? `First ${selected.length}` : "Full sweep",
    );
  }

  function handleClearCache() {
    stopRun();
    clearReviewCache();
    setResults({});
    setHasRun(false);
  }

  async function handleDownloadScreenshots() {
    if (isCapturing) return;

    const targets = sortedShapeGroups.flatMap(([shapeKey, entries]) => {
      const element = captureTargetsRef.current.get(shapeKey);
      const firstEntry = entries[0];
      if (!element || !firstEntry) return [];
      return [{ element, shapeName: firstEntry.shape.name }];
    });
    if (targets.length === 0) return;

    setCaptureProgress({ current: 0, total: targets.length });
    setCaptureError(null);
    try {
      await downloadReviewScreenshots(targets, setCaptureProgress);
    } catch (error) {
      setCaptureError(safeErrorMessage(error));
    } finally {
      setCaptureProgress(null);
    }
  }

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
            <div className={styles.reviewActions}>
              <Button
                type="button"
                variant="primary"
                size="sm"
                disabled={!canRun || isRunning}
                onClick={() => handleRun()}
              >
                Run review sweep
              </Button>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                disabled={!canRun || isRunning}
                onClick={() => handleRun(10)}
              >
                Run first 10
              </Button>
              <Button
                type="button"
                variant="danger"
                size="sm"
                disabled={!isRunning}
                onClick={stopRun}
              >
                Stop
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={handleClearCache}
              >
                Clear cached results
              </Button>
            </div>

            <div className={styles.controlGroup}>
              <label className={styles.toggle}>
                <input
                  type="checkbox"
                  checked={useCachedResults}
                  disabled={isRunning}
                  onChange={(event) =>
                    setUseCachedResults(event.target.checked)
                  }
                />
                <span>Use cached results</span>
              </label>
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
              <Button
                type="button"
                variant="secondary"
                size="sm"
                loading={isCapturing}
                disabled={!screenshotsReady}
                onClick={handleDownloadScreenshots}
              >
                {screenshotButtonLabel}
              </Button>
            </div>
            <div className={styles.reviewMeta}>
              <p className={styles.meta}>
                {fixtures.length} fixtures available.{" "}
                {sortedShapeGroups.length} shapes loaded.
              </p>
              {runProgress && (
                <p className={styles.meta} aria-live="polite">
                  {runProgress.label}: {runProgress.completed} /{" "}
                  {runProgress.total} complete
                </p>
              )}
            </div>
            {captureError && (
              <p className={styles.controlError}>
                Screenshot download failed: {captureError}
              </p>
            )}
          </div>
        )}

        {!fixturesLoading && !fixturesError && (
          <aside className={styles.costNote}>
            Review sweeps run many expensive /query requests. Use cached
            results when possible, especially on Vercel.
          </aside>
        )}

        {fixturesLoading && (
          <p className={styles.placeholder}>Loading fixtures...</p>
        )}
        {fixturesError && <p className={styles.error}>{fixturesError}</p>}

        {!fixturesLoading && !hasRun && fixtures.length > 0 && (
          <section className={styles.statusPanel}>
            <h2>Ready</h2>
            <p>
              {fixtures.length} fixture{fixtures.length === 1 ? "" : "s"}{" "}
              loaded. Choose a run control to execute review queries.
            </p>
          </section>
        )}

        {!fixturesLoading && hasRun && pendingFixtures.length > 0 && (
          <section className={styles.statusPanel}>
            <h2>{isRunning ? "Loading" : "Not Loaded"}</h2>
            <p>
              {pendingFixtures.length} fixture
              {pendingFixtures.length === 1 ? " is" : "s are"}{" "}
              {isRunning ? "still loading." : "not loaded."}
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
            <section
              key={shapeKey}
              className={styles.group}
              data-review-visible-shape={shapeKey}
            >
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

        <div className={styles.captureStage} aria-hidden="true">
          {sortedShapeGroups.map(([shapeKey, entries]) => {
            const entry = entries[0];
            if (!entry) return null;

            return (
              <section
                key={shapeKey}
                ref={(node) => {
                  if (node) {
                    captureTargetsRef.current.set(shapeKey, node);
                  } else {
                    captureTargetsRef.current.delete(shapeKey);
                  }
                }}
                className={styles.group}
                data-review-capture-shape={shapeKey}
              >
                <h2 className={styles.groupHeading}>
                  <span className={styles.captureHeading}>
                    <span className={styles.groupTitle}>
                      {entry.shape.name}
                    </span>
                    <span className={styles.groupCount}>
                      {entries.length} fixture{entries.length === 1 ? "" : "s"}
                    </span>
                  </span>
                </h2>

                <p className={styles.groupDescription}>
                  {entry.shape.description}
                </p>

                <div className={styles.groupBody}>
                  <article className={styles.block}>
                    <h3 className={styles.queryTitle}>{entry.fixture.query}</h3>
                    <p className={styles.caseMeta}>Fixture {entry.index + 1}</p>
                    <ResultEnvelope data={entry.result} />
                    <div className={styles.resultSections}>
                      <ResultRenderer data={entry.result} />
                    </div>
                  </article>
                </div>
              </section>
            );
          })}
        </div>
      </div>
    </main>
  );
}
