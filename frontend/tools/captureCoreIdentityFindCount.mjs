// Actual public-interface checks; no mocked API responses or publication access.
import { chromium } from "playwright";
import { readFile, writeFile, mkdir, access } from "node:fs/promises";
import { createHash } from "node:crypto";

const [input, output, base = "https://nbatools.vercel.app"] = process.argv.slice(2);
if (!input || !output) throw new Error("Expected case JSON and evidence directory");
if (!["https://nbatools.vercel.app", "http://127.0.0.1:8765"].includes(base)) {
  throw new Error("Only production alias or local verification server allowed");
}
const cases = JSON.parse(await readFile(input, "utf8"));
const core = cases.length === 26 && cases.every(item => /^k0[13][_-]/.test(item.id));
const summaryRanking = cases.length === 33 && cases.every(item => /^k0[24][_-]/.test(item.id));
const ownershipComparison = cases.length === 20 && cases.every(item => /^k0[56][_-]/.test(item.id));
const splits = cases.length === 12 && cases.every(item => /^k07[_-]/.test(item.id));
const unionPairIds = ["union-record", "union-seasons", "union-opponent-split", "union-team-comparison", "union-player-comparison", "pair-out", "pair-playing", "pair-player-bound", "pair-qualified-empty", "pair-third-player", "owned-window", "owned-qualifying", "owned-player-team", "owned-player-opponent"];
const unionPairs = cases.length === unionPairIds.length && unionPairIds.every(id => cases.some(item => item.id === id));
const orScopeIds = ["or-shared", "or-different-opponents", "or-different-seasons"];
const orScopes = cases.length === orScopeIds.length && orScopeIds.every(id => cases.some(item => item.id === id));
const opponentPlayedIds = ["opponent-played-positive", "opponent-played-empty", "opponent-played-extra-clause", "opponent-played-unresolved-first", "opponent-played-pair-positive"];
const opponentPlayed = cases.length === opponentPlayedIds.length && opponentPlayedIds.every(id => cases.some(item => item.id === id));
const ownedOrIds = ["owned-or-positive", "owned-or-unread-prefix"];
const ownedOr = cases.length === ownedOrIds.length && ownedOrIds.every(id => cases.some(item => item.id === id));
const selfUnionIds = ["self-union-record", "self-union-own-finder", "self-union-player-team"];
const selfUnion = cases.length === selfUnionIds.length && selfUnionIds.every(id => cases.some(item => item.id === id));
const leadingListIds = ["leading-list-third-owner", "leading-list-baseline"];
const leadingList = cases.length === leadingListIds.length && leadingListIds.every(id => cases.some(item => item.id === id));
if (!core && !summaryRanking && !ownershipComparison && !splits && !unionPairs && !orScopes && !opponentPlayed && !ownedOr && !selfUnion && !leadingList) throw new Error("Expected a complete reviewed browser bundle");
await mkdir(output, { recursive: true });
let executablePath;
for (const file of ["/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser"]) {
  try { await access(file); executablePath = file; break; } catch { /* Try next installed browser. */ }
}
if (!executablePath) throw new Error("Runner browser unavailable; required check cannot skip");
const browser = await chromium.launch({ executablePath, headless: true });
const receipts = [];
const failures = [];
let lastQueryAt = 0;
try {
  for (const [viewport, width, height] of [["desktop", 1280, 900], ["mobile", 390, 844]]) {
    const context = await browser.newContext({ viewport: { width, height } });
    const page = await context.newPage();
    let errors = [];
    page.on("pageerror", error => errors.push(error.message));
    const navigation = await page.goto(base, { timeout: 30000 });
    if (!navigation?.ok()) throw new Error("Application page unavailable");
    const assets = await page.locator('script[type="module"][src]').evaluateAll(nodes => nodes.map(n => n.src));
    for (const item of cases) {
      // Public admission permits ten queries/minute; preserve it without retries
      // or bypasses. Readiness requests do not invoke statistical queries.
      if (base.startsWith("https:")) {
        await new Promise(resolve => setTimeout(resolve, Math.max(0, 7000 - (Date.now() - lastQueryAt))));
      }
      errors = [];
      const before = await context.request.get(base + "/readiness");
      const readinessBefore = await before.json();
      await page.locator("#nba-query-input").fill(item.query);
      const responsePromise = page.waitForResponse(response => response.url() === base + "/query" && response.request().method() === "POST", { timeout: 60000 });
      const start = Date.now();
      lastQueryAt = start;
      await page.getByRole("button", { name: "Query", exact: true }).click();
      const response = await responsePromise;
      const payload = await response.json();
      await page.locator('[data-app-state="loading"]').waitFor({ state: "detached", timeout: 60000 });
      const text = await page.locator('[data-state-surface="result"]').innerText();
      const after = await context.request.get(base + "/readiness");
      const readinessAfter = await after.json();
      const overflow = await page.evaluate(() => ({ viewport: innerWidth, document: document.documentElement.scrollWidth }));
      const screenshot = `${viewport}-${item.id}.png`;
      const image = await page.screenshot({ path: `${output}/${screenshot}`, fullPage: true, animations: "disabled" });
      const headers = await page.getByRole("table", { name: "Game log", exact: true }).locator("thead th").allTextContents();
      const grainErrors = [];
      if (item.id === "k03-d1") {
        if (!headers.some(h => h.trim().toLowerCase() === "player")) grainErrors.push("Missing player column");
        for (const name of ["Anthony Edwards", "Joel Embiid"]) if (!text.includes(name)) grainErrors.push(`Missing ${name}`);
        if (headers.some(h => /^(score|margin|opp pts)$/i.test(h.trim()))) grainErrors.push("Team statistic in player-game table");
      }
      const tables = await page.locator('[data-state-surface="result"] table').evaluateAll(nodes => nodes.map(table => ({
        label: table.getAttribute("aria-label"),
        headers: [...table.querySelectorAll("thead th")].map(cell => cell.textContent.trim()),
        rows: [...table.querySelectorAll("tbody tr")].map(row => [...row.querySelectorAll("td")].map(cell => cell.textContent.trim())),
        footers: [...table.querySelectorAll("tfoot tr")].map(row => [...row.querySelectorAll("th,td")].map(cell => cell.textContent.trim())),
      })));
      const forbidden = (item.forbidden ?? []).filter(value => text.includes(value));
      const missing = item.text.filter(value => !text.includes(value));
      const receipt = { id: item.id, viewport, query: item.query, http: response.status(), elapsedMs: Date.now() - start,
        payload, text, readinessBefore, readinessAfter, overflow, errors: [...errors], missing,
        headers, grainErrors, tables, forbidden, assets, screenshot, screenshotSha256: createHash("sha256").update(image).digest("hex") };
      receipts.push(receipt);
      if (forbidden.length || grainErrors.length || missing.length || errors.length || overflow.document > width || response.status() !== 200) failures.push(`${viewport}/${item.id}`);
    }
    await context.close();
  }
} finally {
  await writeFile(`${output}/browser-receipt.json`, JSON.stringify({ base, browser: browser.version(), receipts, failures,
    latencyScope: "Observed browser requests; not a declared cold/warm performance acceptance sample" }, null, 2));
  await browser.close();
}
if (failures.length) throw new Error(`Required browser checks failed: ${failures.join(", ")}`);
