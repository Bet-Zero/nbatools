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
if (cases.length !== 26) throw new Error("Expected all 14 K01 and 12 K03 cases");
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
      const missing = item.text.filter(value => !text.includes(value));
      const receipt = { id: item.id, viewport, query: item.query, http: response.status(), elapsedMs: Date.now() - start,
        payload, text, readinessBefore, readinessAfter, overflow, errors: [...errors], missing,
        assets, screenshot, screenshotSha256: createHash("sha256").update(image).digest("hex") };
      receipts.push(receipt);
      if (missing.length || errors.length || overflow.document > width || response.status() !== 200) failures.push(`${viewport}/${item.id}`);
    }
    await context.close();
  }
} finally {
  await writeFile(`${output}/browser-receipt.json`, JSON.stringify({ base, browser: browser.version(), receipts, failures,
    latencyScope: "Observed browser requests; not a declared cold/warm performance acceptance sample" }, null, 2));
  await browser.close();
}
if (failures.length) throw new Error(`Required browser checks failed: ${failures.join(", ")}`);
