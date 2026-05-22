#!/usr/bin/env node

import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const CANONICAL_CASE_COUNT = 20;
const NAVIGATION_TIMEOUT_MS = 30_000;
const CASE_COMPLETION_TIMEOUT_MS = 180_000;
const ASSET_WAIT_TIMEOUT_MS = 5_000;
const CASE_SELECTOR = "[data-visual-case-id]";
const FRONTEND_DIRECTORY = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "..",
);
const VIEWPORTS = [
  { label: "desktop_1280", width: 1280, height: 900 },
  { label: "mobile_390", width: 390, height: 844 },
];

function printUsage() {
  console.log(`Usage:
  npm --prefix frontend run qa:visual-screenshots -- [options]

Options:
  --base-url <url>      Base URL for a built /visual-qa shell.
                        Default: http://127.0.0.1:8000
  --run-id <id>         Output folder name under the output root.
                        Default: UTC timestamp
  --output-root <path>  Screenshot artifact root.
                        Default: ../outputs/visual_qa_screenshots
  --case <case_id>      Capture one case card. Repeat for local reruns.
  --case-id <case_id>   Alias for --case.
  --help                Show this usage text.
`);
}

function timestampRunId(now = new Date()) {
  return now
    .toISOString()
    .replace(/[-:]/g, "")
    .replace(/\.\d{3}Z$/, "Z");
}

function requireOptionValue(argv, index, optionName) {
  const value = argv[index + 1];
  if (!value || value.startsWith("--")) {
    throw new Error(`${optionName} requires a value.`);
  }
  return value;
}

function requireSafeSegment(value, label) {
  if (!/^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(value)) {
    throw new Error(
      `${label} must use only letters, numbers, dots, underscores, and dashes.`,
    );
  }
  return value;
}

function parseArgs(argv) {
  const options = {
    baseUrl: process.env.VISUAL_QA_BASE_URL ?? "http://127.0.0.1:8000",
    runId: process.env.VISUAL_QA_RUN_ID ?? timestampRunId(),
    outputRoot: path.resolve(
      FRONTEND_DIRECTORY,
      process.env.VISUAL_QA_OUTPUT_ROOT ??
        "../outputs/visual_qa_screenshots",
    ),
    caseIds: [],
  };

  for (let index = 0; index < argv.length; index += 1) {
    const option = argv[index];

    if (option === "--help") {
      printUsage();
      process.exit(0);
    }

    if (option === "--base-url") {
      options.baseUrl = requireOptionValue(argv, index, option);
      index += 1;
      continue;
    }

    if (option === "--run-id") {
      options.runId = requireOptionValue(argv, index, option);
      index += 1;
      continue;
    }

    if (option === "--output-root") {
      options.outputRoot = path.resolve(
        process.cwd(),
        requireOptionValue(argv, index, option),
      );
      index += 1;
      continue;
    }

    if (option === "--case" || option === "--case-id") {
      options.caseIds.push(requireOptionValue(argv, index, option));
      index += 1;
      continue;
    }

    throw new Error(`Unknown option: ${option}`);
  }

  options.runId = requireSafeSegment(options.runId, "run ID");
  options.caseIds = options.caseIds.map((caseId) =>
    requireSafeSegment(caseId, "case ID"),
  );

  const duplicateCaseFilters = duplicates(options.caseIds);
  if (duplicateCaseFilters.length > 0) {
    throw new Error(
      `Duplicate --case filters: ${duplicateCaseFilters.join(", ")}`,
    );
  }

  let parsedBaseUrl;
  try {
    parsedBaseUrl = new URL(options.baseUrl);
  } catch {
    throw new Error(`Invalid --base-url: ${options.baseUrl}`);
  }

  if (!["http:", "https:"].includes(parsedBaseUrl.protocol)) {
    throw new Error("--base-url must use http or https.");
  }

  options.baseUrl = parsedBaseUrl.toString().replace(/\/$/, "");
  return options;
}

function duplicates(values) {
  const seen = new Set();
  const repeated = new Set();

  for (const value of values) {
    if (seen.has(value)) repeated.add(value);
    seen.add(value);
  }

  return [...repeated];
}

function toVisualQaUrl(baseUrl) {
  return new URL("/visual-qa", `${baseUrl}/`).toString();
}

function parseInteger(value, label) {
  const parsed = Number.parseInt(value ?? "", 10);
  if (!Number.isInteger(parsed)) {
    throw new Error(`Could not read ${label} from /visual-qa.`);
  }
  return parsed;
}

function parseRunProgress(value) {
  const match = value?.match(/(\d+)\s*\/\s*(\d+)\s*cases completed/i);
  if (!match) {
    throw new Error("Could not read run progress from /visual-qa.");
  }

  return {
    text: value,
    completed: parseInteger(match[1], "completed case count"),
    total: parseInteger(match[2], "total case count"),
  };
}

function parseBackendStatusCounts(value) {
  const match = value?.match(
    /ok\s+(\d+)\s*\/\s*no result\s+(\d+)\s*\/\s*error\s+(\d+)/i,
  );
  if (!match) {
    throw new Error("Could not read backend status counts from /visual-qa.");
  }

  return {
    ok: parseInteger(match[1], "ok backend status count"),
    noResult: parseInteger(match[2], "no-result backend status count"),
    error: parseInteger(match[3], "error backend status count"),
  };
}

function relativeArtifactPath(runDirectory, artifactPath) {
  return path.relative(runDirectory, artifactPath).split(path.sep).join("/");
}

async function writeJson(filePath, value) {
  await mkdir(path.dirname(filePath), { recursive: true });
  await writeFile(filePath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

async function waitForCompletedRun(page) {
  await page.locator(CASE_SELECTOR).first().waitFor({
    state: "attached",
    timeout: NAVIGATION_TIMEOUT_MS,
  });
  await page.waitForFunction(
    () => {
      const match = document.body?.innerText.match(
        /(\d+)\s*\/\s*(\d+)\s*cases completed/i,
      );
      return Boolean(match && match[1] === match[2]);
    },
    undefined,
    { timeout: CASE_COMPLETION_TIMEOUT_MS },
  );
}

async function waitForCaptureAssets(page) {
  await page.evaluate(async (timeoutMs) => {
    await document.fonts?.ready;

    const pendingImages = Array.from(document.images).filter(
      (image) => !image.complete,
    );
    await Promise.all(
      pendingImages.map(
        (image) =>
          new Promise((resolve) => {
            const finish = () => {
              window.clearTimeout(timeout);
              resolve();
            };
            const timeout = window.setTimeout(finish, timeoutMs);
            image.addEventListener("load", finish, { once: true });
            image.addEventListener("error", finish, { once: true });
          }),
      ),
    );
  }, ASSET_WAIT_TIMEOUT_MS);
}

async function readPageSnapshot(page) {
  return page.evaluate((caseSelector) => {
    function summaryValue(label) {
      const labelElement = Array.from(document.querySelectorAll("span")).find(
        (element) => element.textContent?.trim() === label,
      );
      const valueElement =
        labelElement?.parentElement?.querySelectorAll("span")[1];
      return valueElement?.textContent?.replace(/\s+/g, " ").trim() ?? null;
    }

    const root = document.documentElement;
    const body = document.body;
    const cardIds = Array.from(document.querySelectorAll(caseSelector)).map(
      (element) => element.getAttribute("data-visual-case-id") ?? "",
    );

    return {
      runProgress: summaryValue("Run progress"),
      loadedResponses: summaryValue("Loaded responses"),
      backendStatuses: summaryValue("Backend statuses"),
      requestErrors: summaryValue("Request errors"),
      viewport: {
        innerWidth: window.innerWidth,
        innerHeight: window.innerHeight,
      },
      document: {
        clientWidth: root.clientWidth,
        scrollWidth: root.scrollWidth,
      },
      body: {
        clientWidth: body.clientWidth,
        scrollWidth: body.scrollWidth,
      },
      cardIds,
    };
  }, CASE_SELECTOR);
}

function selectCaptureIds(cardIds, requestedCaseIds) {
  if (requestedCaseIds.length === 0) return cardIds;

  const requestedIds = new Set(requestedCaseIds);
  const missingCaseIds = requestedCaseIds.filter(
    (caseId) => !cardIds.includes(caseId),
  );
  if (missingCaseIds.length > 0) {
    throw new Error(
      `Requested case IDs were not found: ${missingCaseIds.join(", ")}`,
    );
  }

  return cardIds.filter((caseId) => requestedIds.has(caseId));
}

function validateSnapshot(snapshot, options, viewport) {
  if (snapshot.cardIds.some((caseId) => caseId.length === 0)) {
    throw new Error(
      `${viewport.label} found a visual QA card without a case ID.`,
    );
  }

  const duplicateCardIds = duplicates(snapshot.cardIds);
  if (duplicateCardIds.length > 0) {
    throw new Error(
      `${viewport.label} found duplicate case IDs: ${duplicateCardIds.join(", ")}`,
    );
  }

  const runProgress = parseRunProgress(snapshot.runProgress);
  const loadedCaseCount = parseInteger(
    snapshot.loadedResponses,
    "loaded response count",
  );
  const requestErrorCount = parseInteger(
    snapshot.requestErrors,
    "request error count",
  );
  const backendStatusCounts = parseBackendStatusCounts(
    snapshot.backendStatuses,
  );
  const canonicalRun = options.caseIds.length === 0;

  if (runProgress.completed !== runProgress.total) {
    throw new Error(
      `${viewport.label} stopped before all cases completed: ${runProgress.text}`,
    );
  }

  if (requestErrorCount > 0) {
    throw new Error(
      `${viewport.label} reported ${requestErrorCount} request errors.`,
    );
  }

  if (loadedCaseCount !== runProgress.total) {
    throw new Error(
      `${viewport.label} loaded ${loadedCaseCount} of ${runProgress.total} responses.`,
    );
  }

  if (canonicalRun && snapshot.cardIds.length !== CANONICAL_CASE_COUNT) {
    throw new Error(
      `${viewport.label} expected ${CANONICAL_CASE_COUNT} case cards for the canonical run and found ${snapshot.cardIds.length}.`,
    );
  }

  const documentOverflow =
    snapshot.document.scrollWidth > snapshot.document.clientWidth;
  const bodyOverflow = snapshot.body.scrollWidth > snapshot.body.clientWidth;
  const overflowPassed = !documentOverflow && !bodyOverflow;
  if (!overflowPassed) {
    throw new Error(
      `${viewport.label} measured document-level horizontal overflow.`,
    );
  }

  const captureIds = selectCaptureIds(snapshot.cardIds, options.caseIds);

  return {
    viewport: {
      label: viewport.label,
      width: viewport.width,
      height: viewport.height,
      measuredInnerWidth: snapshot.viewport.innerWidth,
      measuredInnerHeight: snapshot.viewport.innerHeight,
    },
    runProgress,
    loadedCaseCount,
    requestErrorCount,
    backendStatusCounts,
    document: snapshot.document,
    body: snapshot.body,
    cardCount: captureIds.length,
    cardIdsCaptured: [],
    observedCardCount: snapshot.cardIds.length,
    observedCardIds: snapshot.cardIds,
    overflow: {
      passed: overflowPassed,
      documentOverflow,
      bodyOverflow,
    },
  };
}

async function captureViewport(browser, options, runDirectory, viewport) {
  const viewportDirectory = path.join(runDirectory, viewport.label);
  const cardsDirectory = path.join(viewportDirectory, "cards");
  const pagePath = path.join(viewportDirectory, "page.png");
  const metricsPath = path.join(viewportDirectory, "metrics.json");
  await mkdir(cardsDirectory, { recursive: true });

  const context = await browser.newContext({
    viewport: { width: viewport.width, height: viewport.height },
  });
  const page = await context.newPage();

  try {
    const response = await page.goto(toVisualQaUrl(options.baseUrl), {
      waitUntil: "domcontentloaded",
      timeout: NAVIGATION_TIMEOUT_MS,
    });

    if (!response?.ok()) {
      const status = response ? response.status() : "no response";
      throw new Error(`${viewport.label} could not load /visual-qa: ${status}.`);
    }

    await waitForCompletedRun(page);
    await waitForCaptureAssets(page);

    const snapshot = await readPageSnapshot(page);
    const metrics = validateSnapshot(snapshot, options, viewport);
    const selectedCaseIds = new Set(
      selectCaptureIds(snapshot.cardIds, options.caseIds),
    );

    await page.screenshot({ path: pagePath, fullPage: true });

    const cards = page.locator(CASE_SELECTOR);
    for (const [index, caseId] of snapshot.cardIds.entries()) {
      if (!selectedCaseIds.has(caseId)) continue;

      const cardPath = path.join(cardsDirectory, `${caseId}.png`);
      await cards.nth(index).screenshot({ path: cardPath });
      metrics.cardIdsCaptured.push(caseId);
    }

    if (metrics.cardIdsCaptured.length !== metrics.cardCount) {
      throw new Error(
        `${viewport.label} captured ${metrics.cardIdsCaptured.length} of ${metrics.cardCount} selected case cards.`,
      );
    }

    await writeJson(metricsPath, metrics);

    return {
      label: viewport.label,
      width: viewport.width,
      height: viewport.height,
      metrics,
      pageScreenshot: relativeArtifactPath(runDirectory, pagePath),
      metricsPath: relativeArtifactPath(runDirectory, metricsPath),
      cardScreenshots: metrics.cardIdsCaptured.map((caseId) => ({
        caseId,
        path: relativeArtifactPath(
          runDirectory,
          path.join(cardsDirectory, `${caseId}.png`),
        ),
      })),
    };
  } finally {
    await context.close();
  }
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  const runDirectory = path.join(options.outputRoot, options.runId);
  await mkdir(runDirectory, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const capturedAt = new Date().toISOString();

  try {
    const viewportRuns = [];
    for (const viewport of VIEWPORTS) {
      console.log(
        `Capturing ${viewport.label} from ${toVisualQaUrl(options.baseUrl)}.`,
      );
      viewportRuns.push(
        await captureViewport(browser, options, runDirectory, viewport),
      );
    }

    const manifestPath = path.join(runDirectory, "manifest.json");
    const manifest = {
      version: 1,
      runId: options.runId,
      capturedAt,
      baseUrl: options.baseUrl,
      route: "/visual-qa",
      canonicalRun: options.caseIds.length === 0,
      canonicalCaseCount: CANONICAL_CASE_COUNT,
      caseFilters: options.caseIds,
      viewports: viewportRuns.map((viewportRun) => ({
        label: viewportRun.label,
        width: viewportRun.width,
        height: viewportRun.height,
        metricsPath: viewportRun.metricsPath,
        pageScreenshot: viewportRun.pageScreenshot,
        cardScreenshots: viewportRun.cardScreenshots,
      })),
    };
    await writeJson(manifestPath, manifest);

    console.log(`Visual QA screenshot artifacts written to ${runDirectory}.`);
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(
    `Visual QA screenshot artifact capture failed: ${error instanceof Error ? error.message : String(error)}`,
  );
  process.exitCode = 1;
});
