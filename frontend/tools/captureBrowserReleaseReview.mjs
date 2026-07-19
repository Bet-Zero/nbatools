#!/usr/bin/env node

import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import AxeBuilder from "@axe-core/playwright";
import { chromium } from "playwright";

const FRONTEND_DIRECTORY = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "..",
);
const REPOSITORY_ROOT = path.resolve(FRONTEND_DIRECTORY, "..");
const VISUAL_CORPUS_PATH = path.join(
  REPOSITORY_ROOT,
  "qa",
  "frontend_visual_qa_corpus.json",
);
const VIEWPORTS = [
  { label: "desktop_1280", width: 1280, height: 900 },
  { label: "mobile_390", width: 390, height: 844 },
];
const NAVIGATION_TIMEOUT_MS = 30_000;
const QUERY_TIMEOUT_MS = 90_000;
const NBA_ASSET_PATTERN = "https://cdn.nba.com/**";

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

function safeSegment(value, label) {
  if (!/^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(value)) {
    throw new Error(`${label} contains unsupported path characters.`);
  }
  return value;
}

function parseArgs(argv) {
  const options = {
    baseUrl: process.env.BROWSER_REVIEW_BASE_URL ?? "http://127.0.0.1:8000",
    runId: process.env.BROWSER_REVIEW_RUN_ID ?? timestampRunId(),
    outputRoot: path.resolve(
      FRONTEND_DIRECTORY,
      process.env.BROWSER_REVIEW_OUTPUT_ROOT ??
        "../outputs/browser_release_review",
    ),
  };

  for (let index = 0; index < argv.length; index += 1) {
    const option = argv[index];
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
    throw new Error(`Unknown option: ${option}`);
  }

  options.runId = safeSegment(options.runId, "run ID");
  const parsedBaseUrl = new URL(options.baseUrl);
  if (!["http:", "https:"].includes(parsedBaseUrl.protocol)) {
    throw new Error("--base-url must use http or https.");
  }
  options.baseUrl = parsedBaseUrl.toString().replace(/\/$/, "");
  return options;
}

async function writeJson(filePath, value) {
  await mkdir(path.dirname(filePath), { recursive: true });
  await writeFile(filePath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

async function sha256File(filePath) {
  return createHash("sha256")
    .update(await readFile(filePath))
    .digest("hex");
}

function repositoryState() {
  const sourceCommit = execFileSync("git", ["rev-parse", "HEAD"], {
    cwd: REPOSITORY_ROOT,
    encoding: "utf8",
  }).trim();
  const trackedStatus = execFileSync(
    "git",
    ["status", "--porcelain", "--untracked-files=no"],
    { cwd: REPOSITORY_ROOT, encoding: "utf8" },
  ).trim();
  return { sourceCommit, sourceTreeClean: trackedStatus.length === 0 };
}

function relativePath(root, filePath) {
  return path.relative(root, filePath).split(path.sep).join("/");
}

function simplifiedViolations(result) {
  return result.violations.map((violation) => ({
    id: violation.id,
    impact: violation.impact,
    help: violation.help,
    helpUrl: violation.helpUrl,
    nodes: violation.nodes.map((node) => ({
      target: node.target,
      html: node.html.slice(0, 500),
      failureSummary: node.failureSummary,
    })),
  }));
}

async function axeScan(page, state) {
  const result = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  const violations = simplifiedViolations(result);
  return {
    state,
    violationCount: violations.length,
    seriousOrCriticalCount: violations.filter((violation) =>
      ["serious", "critical"].includes(violation.impact),
    ).length,
    violations,
  };
}

async function captureState(page, runDirectory, viewportLabel, state, scans) {
  const stateDirectory = path.join(runDirectory, viewportLabel);
  const screenshotPath = path.join(stateDirectory, `${state}.jpg`);
  await mkdir(stateDirectory, { recursive: true });
  await page.screenshot({
    path: screenshotPath,
    type: "jpeg",
    quality: 72,
    fullPage: true,
  });
  const scan = await axeScan(page, state);
  scans.push(scan);
  return relativePath(runDirectory, screenshotPath);
}

async function submitQuery(page, query) {
  await page.locator("#nba-query-input").fill(query);
  await page.getByRole("button", { name: "Query", exact: true }).click();
}

async function waitForAppState(page, state) {
  await page.locator(`[data-app-state="${state}"]`).waitFor({
    state: "attached",
    timeout: QUERY_TIMEOUT_MS,
  });
}

async function installNbaAssetProxy(page, probe) {
  await page.route(NBA_ASSET_PATTERN, async (route) => {
    probe.requested += 1;
    try {
      const response = await fetch(route.request().url());
      if (!response.ok) {
        throw new Error(`upstream returned ${response.status}`);
      }
      const body = Buffer.from(await response.arrayBuffer());
      await route.fulfill({
        status: response.status,
        headers: {
          "cache-control": "no-store",
          "content-type":
            response.headers.get("content-type") ??
            "application/octet-stream",
        },
        body,
      });
      probe.fulfilled += 1;
    } catch (error) {
      probe.failed.push(
        error instanceof Error ? error.message : String(error),
      );
      await route.abort("failed");
    }
  });
}

async function resultImageProbe(page) {
  const image = page.locator('[data-state-surface="result"] img').first();
  try {
    await image.waitFor({ state: "visible", timeout: NAVIGATION_TIMEOUT_MS });
    await page.waitForFunction(
      () => {
        const candidate = document.querySelector(
          '[data-state-surface="result"] img',
        );
        return Boolean(
          candidate instanceof HTMLImageElement &&
            candidate.complete &&
            candidate.naturalWidth > 0 &&
            candidate.naturalHeight > 0,
        );
      },
      undefined,
      { timeout: NAVIGATION_TIMEOUT_MS },
    );
    return await image.evaluate((element) => ({
      loaded: element.complete && element.naturalWidth > 0,
      src: element.currentSrc || element.src,
      naturalWidth: element.naturalWidth,
      naturalHeight: element.naturalHeight,
    }));
  } catch (error) {
    return {
      loaded: false,
      src: null,
      naturalWidth: 0,
      naturalHeight: 0,
      error: error instanceof Error ? error.message : String(error),
    };
  }
}

async function tableResultProbe(page) {
  const table = page.locator('[data-state-surface="result"] table').first();
  try {
    await table.waitFor({ state: "visible", timeout: QUERY_TIMEOUT_MS });
    const rowCount = await table.locator("tbody tr").count();
    const layout = await table.evaluate((element) => {
      const scrollOwner = element.parentElement;
      return {
        tableScrollWidth: element.scrollWidth,
        tableClientWidth: element.clientWidth,
        scrollOwnerWidth: scrollOwner?.clientWidth ?? null,
        documentOverflow:
          document.documentElement.scrollWidth > window.innerWidth + 1,
      };
    });
    return { visible: true, rowCount, ...layout };
  } catch (error) {
    return {
      visible: false,
      rowCount: 0,
      tableScrollWidth: 0,
      tableClientWidth: 0,
      scrollOwnerWidth: null,
      documentOverflow: null,
      error: error instanceof Error ? error.message : String(error),
    };
  }
}

async function dialogProbe(page, trigger, dialogName, cancelName) {
  await trigger.click();
  const dialog = page.getByRole("dialog", { name: dialogName });
  await dialog.waitFor({ state: "visible" });
  const initialFocus = await page.evaluate(() => {
    const active = document.activeElement;
    const owner = active?.closest('[role="dialog"]');
    return {
      insideDialog: Boolean(owner),
      tag: active?.tagName ?? null,
      id: active?.id ?? null,
      text: active?.textContent?.trim().slice(0, 80) ?? null,
    };
  });
  await page.keyboard.press("Escape");
  const escapeClosed = await dialog.isHidden().catch(() => false);
  if (!escapeClosed) {
    await page.getByRole("button", { name: cancelName, exact: true }).click();
  }

  await trigger.click();
  await dialog.waitFor({ state: "visible" });
  const focusables = dialog.locator(
    'button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
  );
  const focusableCount = await focusables.count();
  if (focusableCount > 0) {
    await focusables.nth(focusableCount - 1).focus();
    await page.keyboard.press("Tab");
  }
  const tabWrapped = await dialog.evaluate((element) =>
    element.contains(document.activeElement),
  );
  await page.getByRole("button", { name: cancelName, exact: true }).click();
  const focusRestored = await trigger.evaluate(
    (element) => document.activeElement === element,
  );
  return {
    initialFocus,
    escapeClosed,
    focusableCount,
    tabWrapped,
    focusRestored,
  };
}

function noResultPayload({ query, reason, unsupported = false }) {
  return {
    ok: false,
    query,
    route: "game_finder",
    intent: "game_finder",
    result_status: "no_result",
    result_reason: reason,
    result: {
      query_class: "finder",
      metadata: {
        query_class: "finder",
        route: "game_finder",
        current_through: "2026-04-13",
        unsupported_filters: unsupported ? ["synthetic_review_boundary"] : [],
      },
      sections: {},
    },
    notes: [],
    caveats: [],
    errors: [],
  };
}

function backendErrorPayload(query) {
  return {
    ok: false,
    query,
    route: null,
    intent: null,
    result_status: "error",
    result_reason: "error",
    result: {
      query_class: "error",
      metadata: { query_class: "error" },
      sections: {},
    },
    notes: [],
    caveats: [],
    errors: ["Synthetic browser-review backend error."],
  };
}

async function fulfillNextQuery(page, payload, status = 200) {
  await page.route(
    "**/query",
    async (route) => {
      await route.fulfill({
        status,
        contentType: "application/json",
        body: JSON.stringify(payload),
      });
    },
    { times: 1 },
  );
}

async function resultAnnouncementProbe(page) {
  return page.locator('[data-state-surface="result"]').evaluate((element) => {
    const liveOwner = element.closest(
      '[aria-live], [role="status"], [role="alert"]',
    );
    return {
      hasLiveOwner: Boolean(liveOwner),
      liveMode: liveOwner?.getAttribute("aria-live") ?? null,
      role: liveOwner?.getAttribute("role") ?? null,
      activeElement: document.activeElement?.tagName ?? null,
      activeElementId: document.activeElement?.id ?? null,
    };
  });
}

async function reducedMotionProbe(browser, options, viewport) {
  const context = await browser.newContext({
    viewport: { width: viewport.width, height: viewport.height },
    reducedMotion: "reduce",
  });
  const page = await context.newPage();
  try {
    await page.route(
      "**/query",
      async (route) => {
        await new Promise((resolve) => setTimeout(resolve, 1_200));
        await route.continue();
      },
      { times: 1 },
    );
    await page.goto(options.baseUrl, {
      waitUntil: "domcontentloaded",
      timeout: NAVIGATION_TIMEOUT_MS,
    });
    await submitQuery(page, "Jokic stats this season");
    await waitForAppState(page, "loading");
    return await page.evaluate(() => {
      const offenders = [];
      for (const element of document.querySelectorAll("*")) {
        const style = getComputedStyle(element);
        const names = style.animationName
          .split(",")
          .map((value) => value.trim());
        const durations = style.animationDuration
          .split(",")
          .map((value) => value.trim());
        if (names.some((name) => name && name !== "none")) {
          offenders.push({
            tag: element.tagName,
            className: String(element.className).slice(0, 180),
            animationName: style.animationName,
            animationDuration: durations.join(", "),
            animationIterationCount: style.animationIterationCount,
          });
        }
      }
      return {
        prefersReducedMotion: true,
        animatedElementCount: offenders.length,
        offenders,
      };
    });
  } finally {
    await context.close();
  }
}

async function reviewViewport(browser, options, runDirectory, viewport) {
  const context = await browser.newContext({
    viewport: { width: viewport.width, height: viewport.height },
  });
  const page = await context.newPage();
  const scans = [];
  const screenshots = [];
  const nbaAssetProxy = { requested: 0, fulfilled: 0, failed: [] };
  let queryRequestCount = 0;
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (request.method() === "POST" && url.pathname === "/query") {
      queryRequestCount += 1;
    }
  });

  try {
    await installNbaAssetProxy(page, nbaAssetProxy);
    await page.route(
      "**/query",
      async (route) => {
        await new Promise((resolve) => setTimeout(resolve, 1_200));
        await route.continue();
      },
      { times: 1 },
    );
    await page.goto(options.baseUrl, {
      waitUntil: "domcontentloaded",
      timeout: NAVIGATION_TIMEOUT_MS,
    });
    await page.locator("#nba-query-input").waitFor({ state: "visible" });

    const freshness = page.getByRole("button", { name: /Data freshness:/ });
    await freshness.waitFor({
      state: "visible",
      timeout: NAVIGATION_TIMEOUT_MS,
    });
    await freshness.click();
    screenshots.push({
      state: "freshness_expanded",
      path: await captureState(
        page,
        runDirectory,
        viewport.label,
        "freshness_expanded",
        scans,
      ),
    });

    await submitQuery(page, "Jokic stats this season");
    await waitForAppState(page, "loading");
    screenshots.push({
      state: "loading",
      path: await captureState(
        page,
        runDirectory,
        viewport.label,
        "loading",
        scans,
      ),
    });
    await waitForAppState(page, "result");
    const summaryImage = await resultImageProbe(page);
    screenshots.push({
      state: "success",
      path: await captureState(
        page,
        runDirectory,
        viewport.label,
        "success",
        scans,
      ),
    });
    const resultAnnouncement = await resultAnnouncementProbe(page);

    const saveTrigger = page.getByRole("button", {
      name: "Save Query",
      exact: true,
    });
    await saveTrigger.click();
    screenshots.push({
      state: "save_dialog",
      path: await captureState(
        page,
        runDirectory,
        viewport.label,
        "save_dialog",
        scans,
      ),
    });
    await page.getByRole("button", { name: "Cancel", exact: true }).click();
    const saveDialog = await dialogProbe(
      page,
      saveTrigger,
      "Save Query",
      "Cancel",
    );

    await submitQuery(page, "Jokic last 10 games");
    await waitForAppState(page, "result");
    const tableResult = await tableResultProbe(page);
    screenshots.push({
      state: "table_success",
      path: await captureState(
        page,
        runDirectory,
        viewport.label,
        "table_success",
        scans,
      ),
    });

    await fulfillNextQuery(
      page,
      noResultPayload({ query: "Synthetic zero row", reason: "no_match" }),
    );
    await submitQuery(page, "Synthetic zero row");
    await waitForAppState(page, "result");
    screenshots.push({
      state: "zero_result",
      path: await captureState(
        page,
        runDirectory,
        viewport.label,
        "zero_result",
        scans,
      ),
    });

    await fulfillNextQuery(
      page,
      noResultPayload({
        query: "Synthetic unsupported boundary",
        reason: "filter_not_supported",
        unsupported: true,
      }),
    );
    await submitQuery(page, "Synthetic unsupported boundary");
    await waitForAppState(page, "result");
    screenshots.push({
      state: "no_result",
      path: await captureState(
        page,
        runDirectory,
        viewport.label,
        "no_result",
        scans,
      ),
    });

    await fulfillNextQuery(
      page,
      backendErrorPayload("Synthetic backend error"),
    );
    await submitQuery(page, "Synthetic backend error");
    await waitForAppState(page, "result");
    screenshots.push({
      state: "backend_error",
      path: await captureState(
        page,
        runDirectory,
        viewport.label,
        "backend_error",
        scans,
      ),
    });

    await fulfillNextQuery(page, { error: "Synthetic transport failure" }, 503);
    await submitQuery(page, "Synthetic transport error");
    await waitForAppState(page, "error");
    screenshots.push({
      state: "transport_error",
      path: await captureState(
        page,
        runDirectory,
        viewport.label,
        "transport_error",
        scans,
      ),
    });

    const visualContext = await browser.newContext({
      viewport: { width: viewport.width, height: viewport.height },
    });
    const visualPage = await visualContext.newPage();
    let visualMountQueryCount = 0;
    visualPage.on("request", (request) => {
      const url = new URL(request.url());
      if (request.method() === "POST" && url.pathname === "/query") {
        visualMountQueryCount += 1;
      }
    });
    try {
      await visualPage.goto(
        new URL("/visual-qa", `${options.baseUrl}/`).toString(),
        {
          waitUntil: "networkidle",
          timeout: NAVIGATION_TIMEOUT_MS,
        },
      );
      screenshots.push({
        state: "visual_qa_idle",
        path: await captureState(
          visualPage,
          runDirectory,
          viewport.label,
          "visual_qa_idle",
          scans,
        ),
      });
    } finally {
      await visualContext.close();
    }

    const reducedMotion = await reducedMotionProbe(browser, options, viewport);
    return {
      viewport,
      screenshots,
      axeScans: scans,
      queryRequestCount,
      resultAnnouncement,
      dialogs: { save: saveDialog },
      summaryImage,
      tableResult,
      nbaAssetProxy,
      reducedMotion,
      visualQaMountQueryCount: visualMountQueryCount,
    };
  } finally {
    await context.close();
  }
}

function blockingFindings(viewportRuns) {
  const findings = [];
  for (const run of viewportRuns) {
    const label = run.viewport.label;
    const seriousAxeResults = run.axeScans.flatMap((scan) =>
      scan.violations.filter((violation) =>
        ["serious", "critical"].includes(violation.impact),
      ),
    );
    if (seriousAxeResults.length > 0) {
      const ruleIds = [
        ...new Set(seriousAxeResults.map((violation) => violation.id)),
      ];
      findings.push(
        `${label}: ${seriousAxeResults.length} serious/critical axe state-rule results (${ruleIds.join(", ")})`,
      );
    }
    if (!run.resultAnnouncement.hasLiveOwner) {
      findings.push(
        `${label}: completed result has no live announcement owner`,
      );
    }
    if (!run.summaryImage.loaded) {
      findings.push(`${label}: summary player image did not load`);
    }
    if (run.nbaAssetProxy.failed.length > 0) {
      findings.push(
        `${label}: ${run.nbaAssetProxy.failed.length} NBA visual assets failed in the review proxy`,
      );
    }
    if (!run.tableResult.visible || run.tableResult.rowCount < 10) {
      findings.push(
        `${label}: representative game table did not render all ten rows`,
      );
    }
    if (run.tableResult.documentOverflow) {
      findings.push(
        `${label}: representative game table caused document-level horizontal overflow`,
      );
    }
    for (const [name, dialog] of Object.entries(run.dialogs)) {
      if (!dialog.initialFocus.insideDialog)
        findings.push(`${label}: ${name} dialog lacks initial focus`);
      if (!dialog.escapeClosed)
        findings.push(`${label}: ${name} dialog does not close on Escape`);
      if (!dialog.tabWrapped)
        findings.push(`${label}: ${name} dialog does not wrap Tab focus`);
      if (!dialog.focusRestored)
        findings.push(
          `${label}: ${name} dialog does not restore trigger focus`,
        );
    }
    if (run.reducedMotion.animatedElementCount > 0) {
      findings.push(
        `${label}: ${run.reducedMotion.animatedElementCount} animations remain with reduced motion`,
      );
    }
    if (run.visualQaMountQueryCount !== 0) {
      findings.push(
        `${label}: /visual-qa mount issued ${run.visualQaMountQueryCount} query requests`,
      );
    }
  }
  return findings;
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  const runDirectory = path.join(options.outputRoot, options.runId);
  await mkdir(runDirectory, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const provenance = repositoryState();
  try {
    const viewportRuns = [];
    for (const viewport of VIEWPORTS) {
      console.log(`Reviewing ${viewport.label} at ${options.baseUrl}.`);
      viewportRuns.push(
        await reviewViewport(browser, options, runDirectory, viewport),
      );
    }
    const findings = blockingFindings(viewportRuns);
    const screenshotPaths = viewportRuns.flatMap((run) =>
      run.screenshots.map((screenshot) => screenshot.path),
    );
    const artifacts = await Promise.all(
      screenshotPaths.map(async (artifactPath) => ({
        path: artifactPath,
        sha256: await sha256File(path.join(runDirectory, artifactPath)),
      })),
    );
    const receipt = {
      version: 1,
      runId: options.runId,
      capturedAt: new Date().toISOString(),
      baseUrl: options.baseUrl,
      browser: { name: "chromium", version: browser.version() },
      sourceCommit: provenance.sourceCommit,
      sourceTreeClean: provenance.sourceTreeClean,
      visualCorpusSha256: await sha256File(VISUAL_CORPUS_PATH),
      executionStatus: "complete",
      acceptanceStatus: findings.length === 0 ? "pass" : "blocked",
      humanReview: "pending",
      fixtureBoundary: {
        liveStates: [
          "freshness_expanded",
          "loading",
          "success",
          "table_success",
          "visual_qa_idle",
        ],
        syntheticStates: [
          "zero_result",
          "no_result",
          "backend_error",
          "transport_error",
        ],
      },
      blockingFindings: findings,
      viewports: viewportRuns,
      artifacts,
    };
    await writeJson(path.join(runDirectory, "receipt.json"), receipt);
    console.log(`Browser release review written to ${runDirectory}.`);
    console.log(`Acceptance status: ${receipt.acceptanceStatus}.`);
    console.log(`Blocking findings: ${findings.length}.`);
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(
    `Browser release review failed: ${error instanceof Error ? error.message : String(error)}`,
  );
  process.exitCode = 1;
});
