import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { postQuery } from "./api/client";
import type { QueryResponse } from "./api/types";
import ResultEnvelope, {
  ResultContextSummary,
} from "./components/ResultEnvelope";
import ResultRenderer from "./components/results/ResultRenderer";
import {
  downloadReviewScreenshots,
  type ReviewScreenshotProgress,
} from "./lib/reviewScreenshots";
import {
  VISUAL_QA_CASES,
  VISUAL_QA_CHECKLIST_DOC,
  VISUAL_QA_INTERNAL_ROUTE,
  VISUAL_QA_PROVENANCE_FRONTEND_COPY_RUN,
  VISUAL_QA_PROVENANCE_RAW_RUN,
  type VisualQaCase,
} from "./visualQaCases";
import styles from "./VisualQaPage.module.css";

type CaseLoadStatus = "idle" | "loading" | "loaded" | "request_error";

interface CaseLoadState {
  status: CaseLoadStatus;
  data?: QueryResponse;
  error?: string;
}

interface RunProgress {
  completed: number;
  total: number;
  isRunning: boolean;
}

const CONCURRENCY_LIMIT = 3;

function buildInitialCaseStates(
  status: CaseLoadStatus,
): Record<string, CaseLoadState> {
  return Object.fromEntries(
    VISUAL_QA_CASES.map((caseItem) => [caseItem.id, { status }]),
  );
}

function safeErrorMessage(error: unknown): string {
  const raw = error instanceof Error ? error.message : String(error ?? "");
  const firstLine = raw.split(/\r?\n/)[0]?.trim();
  if (!firstLine) return "Request failed.";
  return firstLine.length > 220 ? `${firstLine.slice(0, 217)}...` : firstLine;
}

function backendStateLabel(caseState: CaseLoadState): string {
  if (caseState.status === "loading") return "Loading live /query response...";
  if (caseState.status === "request_error") return "Request error";
  if (caseState.status !== "loaded" || !caseState.data) return "Pending";

  const route = caseState.data.route ?? "unrouted";
  return `${route} / ${caseState.data.result_status}`;
}

export default function VisualQaPage() {
  const runTokenRef = useRef(0);
  const abortControllersRef = useRef(new Set<AbortController>());
  const captureTargetsRef = useRef(new Map<string, HTMLElement>());
  const [caseStates, setCaseStates] = useState<Record<string, CaseLoadState>>(
    () => buildInitialCaseStates("idle"),
  );
  const [runProgress, setRunProgress] = useState<RunProgress>({
    completed: 0,
    total: VISUAL_QA_CASES.length,
    isRunning: false,
  });
  const [captureProgress, setCaptureProgress] =
    useState<ReviewScreenshotProgress | null>(null);
  const [captureError, setCaptureError] = useState<string | null>(null);

  const runCases = useCallback(async () => {
    const token = runTokenRef.current + 1;
    runTokenRef.current = token;

    abortControllersRef.current.forEach((controller) => controller.abort());
    abortControllersRef.current.clear();

    setCaptureError(null);
    setCaseStates(buildInitialCaseStates("loading"));
    setRunProgress({
      completed: 0,
      total: VISUAL_QA_CASES.length,
      isRunning: true,
    });

    let nextIndex = 0;

    async function worker() {
      while (true) {
        const currentIndex = nextIndex;
        nextIndex += 1;

        if (currentIndex >= VISUAL_QA_CASES.length) return;

        const caseItem = VISUAL_QA_CASES[currentIndex];
        const controller = new AbortController();
        abortControllersRef.current.add(controller);

        try {
          const data = await postQuery(caseItem.query, {
            signal: controller.signal,
          });
          if (runTokenRef.current !== token) return;

          setCaseStates((current) => ({
            ...current,
            [caseItem.id]: { status: "loaded", data },
          }));
        } catch (error) {
          if (controller.signal.aborted || runTokenRef.current !== token) {
            return;
          }

          setCaseStates((current) => ({
            ...current,
            [caseItem.id]: {
              status: "request_error",
              error: safeErrorMessage(error),
            },
          }));
        } finally {
          abortControllersRef.current.delete(controller);

          if (runTokenRef.current === token) {
            setRunProgress((current) => ({
              ...current,
              completed: Math.min(current.completed + 1, current.total),
            }));
          }
        }
      }
    }

    await Promise.all(
      Array.from(
        { length: Math.min(CONCURRENCY_LIMIT, VISUAL_QA_CASES.length) },
        () => worker(),
      ),
    );

    if (runTokenRef.current === token) {
      setRunProgress((current) => ({ ...current, isRunning: false }));
    }
  }, []);

  useEffect(() => {
    const abortControllers = abortControllersRef.current;

    void runCases();

    return () => {
      runTokenRef.current += 1;
      abortControllers.forEach((controller) => controller.abort());
      abortControllers.clear();
    };
  }, [runCases]);

  const statusCounts = useMemo(() => {
    return VISUAL_QA_CASES.reduce(
      (counts, caseItem) => {
        const caseState = caseStates[caseItem.id];

        if (caseState?.status === "loaded" && caseState.data) {
          counts.loaded += 1;
          if (caseState.data.result_status === "ok") counts.ok += 1;
          if (caseState.data.result_status === "no_result")
            counts.noResult += 1;
          if (caseState.data.result_status === "error")
            counts.backendError += 1;
        }

        if (caseState?.status === "request_error") counts.requestError += 1;

        return counts;
      },
      { loaded: 0, ok: 0, noResult: 0, backendError: 0, requestError: 0 },
    );
  }, [caseStates]);

  const downloadableCount = useMemo(() => {
    return VISUAL_QA_CASES.filter((caseItem) => {
      const caseState = caseStates[caseItem.id];
      return (
        caseState?.status === "loaded" &&
        Boolean(caseState.data) &&
        captureTargetsRef.current.has(caseItem.id)
      );
    }).length;
  }, [caseStates]);

  const captureButtonLabel = captureProgress
    ? `Capturing ${captureProgress.current}/${captureProgress.total}...`
    : "Download current viewport screenshots ZIP";

  function registerCaptureTarget(caseId: string, element: HTMLElement | null) {
    if (element) {
      captureTargetsRef.current.set(caseId, element);
      return;
    }

    captureTargetsRef.current.delete(caseId);
  }

  async function handleCapture() {
    const targets = VISUAL_QA_CASES.flatMap((caseItem) => {
      const caseState = caseStates[caseItem.id];
      const element = captureTargetsRef.current.get(caseItem.id);

      if (!element || caseState?.status !== "loaded" || !caseState.data) {
        return [];
      }

      return [{ element, shapeName: caseItem.id }];
    });

    if (targets.length === 0) return;

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
      <div className={styles.shell}>
        <header className={styles.hero}>
          <div>
            <p className={styles.eyebrow}>Internal / Dev QA Surface</p>
            <h1 className={styles.title}>Frontend Visual QA Wave 1</h1>
            <p className={styles.lede}>
              This route renders the 20 approved visual QA cases through live
              <span> </span>
              <strong>/query</strong>
              <span> </span>
              calls and the existing product result composition.
              <span> </span>
              No renderer overrides or visual fixes are applied here.
            </p>
          </div>

          <div className={styles.toolbar}>
            <button
              className={styles.button}
              type="button"
              onClick={() => void runCases()}
              disabled={runProgress.isRunning}
            >
              {runProgress.isRunning
                ? "Refreshing live cases..."
                : "Reload live cases"}
            </button>
            <button
              className={`${styles.button} ${styles.buttonSecondary}`}
              type="button"
              onClick={() => void handleCapture()}
              disabled={downloadableCount === 0 || captureProgress !== null}
            >
              {captureButtonLabel}
            </button>
          </div>

          <div aria-live="polite" className={styles.summaryGrid}>
            <div className={styles.summaryCard}>
              <span className={styles.summaryLabel}>Run progress</span>
              <span className={styles.summaryValue}>
                {runProgress.completed} / {runProgress.total} cases completed
              </span>
            </div>
            <div className={styles.summaryCard}>
              <span className={styles.summaryLabel}>Loaded responses</span>
              <span className={styles.summaryValue}>{statusCounts.loaded}</span>
            </div>
            <div className={styles.summaryCard}>
              <span className={styles.summaryLabel}>Backend statuses</span>
              <span className={styles.summaryValue}>
                ok {statusCounts.ok} / no result {statusCounts.noResult} / error{" "}
                {statusCounts.backendError}
              </span>
            </div>
            <div className={styles.summaryCard}>
              <span className={styles.summaryLabel}>Request errors</span>
              <span className={styles.summaryValue}>
                {statusCounts.requestError}
              </span>
            </div>
          </div>

          <div className={styles.metaGrid}>
            <section className={styles.metaPanel}>
              <h2>Capture workflow</h2>
              <ul>
                <li>Use desktop around 1280px and mobile around 390px.</li>
                <li>
                  Capture each card by its stable selector and keep notes in the
                  checklist doc.
                </li>
                <li>
                  Stable selector pattern:{" "}
                  <span className={styles.path}>
                    data-visual-case-id=&quot;&lt;case_id&gt;&quot;
                  </span>
                </li>
                <li>
                  Checklist path:{" "}
                  <span className={styles.path}>{VISUAL_QA_CHECKLIST_DOC}</span>
                </li>
              </ul>
            </section>

            <section className={styles.metaPanel}>
              <h2>Manifest provenance</h2>
              <ul>
                <li>
                  Raw QA provenance:<span> </span>
                  <span className={styles.path}>
                    {VISUAL_QA_PROVENANCE_RAW_RUN}
                  </span>
                </li>
                <li>
                  Frontend-copy provenance:<span> </span>
                  <span className={styles.path}>
                    {VISUAL_QA_PROVENANCE_FRONTEND_COPY_RUN}
                  </span>
                </li>
                <li>
                  Internal route:<span> </span>
                  <span className={styles.path}>
                    {VISUAL_QA_INTERNAL_ROUTE}
                  </span>
                </li>
                <li>
                  {downloadableCount} cards are ready for viewport ZIP capture.
                </li>
              </ul>
            </section>
          </div>

          {captureError ? (
            <p className={`${styles.resultState} ${styles.errorState}`}>
              {captureError}
            </p>
          ) : null}
        </header>

        <section className={styles.caseList}>
          {VISUAL_QA_CASES.map((caseItem) => (
            <VisualQaCaseCard
              key={caseItem.id}
              caseItem={caseItem}
              caseState={caseStates[caseItem.id] ?? { status: "idle" }}
              registerCaptureTarget={registerCaptureTarget}
            />
          ))}
        </section>
      </div>
    </main>
  );
}

interface VisualQaCaseCardProps {
  caseItem: VisualQaCase;
  caseState: CaseLoadState;
  registerCaptureTarget: (caseId: string, element: HTMLElement | null) => void;
}

function VisualQaCaseCard({
  caseItem,
  caseState,
  registerCaptureTarget,
}: VisualQaCaseCardProps) {
  return (
    <article
      ref={(element) => registerCaptureTarget(caseItem.id, element)}
      className={styles.caseCard}
      data-visual-case-id={caseItem.id}
    >
      <header className={styles.caseHeader}>
        <div className={styles.caseHeading}>
          <p className={styles.eyebrow}>Visual QA case</p>
          <h2>{caseItem.id}</h2>
          <p className={styles.caseQuery}>{caseItem.query}</p>
        </div>
        <div className={styles.statusBadge}>{backendStateLabel(caseState)}</div>
      </header>

      <div className={styles.caseMeta}>
        <span className={styles.metaChip}>Category: {caseItem.category}</span>
        <span className={styles.metaChip}>
          Viewports: {caseItem.viewports.join(" + ")}
        </span>
        {caseState.status === "loaded" && caseState.data ? (
          <>
            <span className={styles.metaChip}>
              Result status: {caseState.data.result_status}
            </span>
            <span className={styles.metaChip}>
              Route: {caseState.data.route ?? "unrouted"}
            </span>
          </>
        ) : null}
      </div>

      <div className={styles.cardBody}>
        <aside className={styles.checklist}>
          <h3>Capture checklist</h3>

          <div className={styles.checklistBlock}>
            <span className={styles.checklistLabel}>Visual focus</span>
            <ul>
              {caseItem.visual_focus.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>

          <div className={styles.checklistBlock}>
            <span className={styles.checklistLabel}>Desktop focus</span>
            <ul>
              {caseItem.desktop_focus.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>

          <div className={styles.checklistBlock}>
            <span className={styles.checklistLabel}>Mobile focus</span>
            <ul>
              {caseItem.mobile_focus.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>

          <div className={styles.checklistBlock}>
            <span className={styles.checklistLabel}>Primary concerns</span>
            <ul>
              {caseItem.expected_primary_visual_concerns.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>

          <p className={styles.placeholder}>
            Pass/fail notes: capture desktop and mobile evidence, then record
            manual observations in the checklist doc.
          </p>
        </aside>

        <section className={styles.resultColumn}>
          <p className={styles.captureTargetLabel}>
            Capture target selector: data-visual-case-id=&quot;{caseItem.id}
            &quot;
          </p>

          {caseState.status === "loading" ? (
            <div className={styles.resultState}>
              Loading live /query response...
            </div>
          ) : null}

          {caseState.status === "request_error" ? (
            <div className={`${styles.resultState} ${styles.errorState}`}>
              <strong>Request error</strong>
              <p>{caseState.error ?? "Request failed."}</p>
            </div>
          ) : null}

          {caseState.status === "loaded" && caseState.data ? (
            <div className={styles.captureTarget}>
              <ResultRenderer
                data={caseState.data}
                displayMode="public"
                resultContext={
                  caseState.data.result_status === "ok" ? (
                    <ResultContextSummary data={caseState.data} />
                  ) : null
                }
              />
              {caseState.data.result_status === "ok" && (
                <ResultEnvelope data={caseState.data} displayMode="public" />
              )}
            </div>
          ) : null}
        </section>
      </div>
    </article>
  );
}
