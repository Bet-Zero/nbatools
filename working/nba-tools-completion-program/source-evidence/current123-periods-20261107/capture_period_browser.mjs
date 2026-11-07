// Local provisional rendering only; source/HTTP proof is in the Python replay.
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { mkdir, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../..');
const { chromium } = createRequire(root + '/frontend/package.json')('playwright');
const output = process.argv[2];
if (!output) throw Error('Output directory required');
await mkdir(output, {recursive:true});
const cases = [
 ['quarter', 'Lakers second quarter record on 2026-11-04', ['1-0','Quarter'], 33],
 ['half', 'Lakers first half record on 2026-11-04', ['1-0','Half'], 61],
 ['pelicans-ot', 'Pelicans overtime record on 2026-11-04', ['1-0','Quarter'], 16],
 ['clippers-ot', 'Clippers overtime record on 2026-11-04', ['0-1','Quarter'], 9],
];
const browser = await chromium.launch({executablePath:'/usr/bin/chromium',headless:true});
const receipts=[]; const errors=[];
try {
 for (const [viewport,width,height] of [['desktop',1280,900],['mobile',390,844]]) {
  const page=await browser.newPage({viewport:{width,height}});
  page.on('pageerror',error=>errors.push(String(error)));
  await page.goto('http://127.0.0.1:8765');
  for (const [id,query,expected,points] of cases) {
   await page.locator('#nba-query-input').fill(query);
   const responsePromise=page.waitForResponse(r=>r.url()==='http://127.0.0.1:8765/query'&&r.request().method()==='POST');
   await page.getByRole('button',{name:'Query',exact:true}).click();
   const response=await responsePromise;
   await page.locator('[data-app-state="loading"]').waitFor({state:'detached'});
   const text=await page.locator('[data-state-surface="result"]').innerText();
   const payload=await response.json();
   if (payload.result.sections.summary[0].pts_avg!==points) throw Error('Wrong source-qualified period points');
   const screenshot=`${viewport}-${id}.png`;
   const raw=await page.screenshot({path:path.join(output,screenshot),fullPage:true,animations:'disabled'});
   const overflow=await page.evaluate(()=>({viewport:innerWidth,document:document.documentElement.scrollWidth}));
   const missing=expected.filter(x=>!text.includes(x));
   if (!text.includes('PROVISIONAL') || payload.result.metadata.season!=='2026-27' || missing.length || response.status()!==200 || overflow.document>width) throw Error(JSON.stringify({id,viewport,missing,text}));
   if (payload.result.metadata.data_quality.production_accepted!==false) throw Error('False production acceptance');
   receipts.push({id,viewport,query,capturedAt:new Date().toISOString(),text,payload,http:response.status(),overflow,screenshot,screenshotSha256:createHash('sha256').update(raw).digest('hex')});
  }
  await page.close();
 }
} finally {
 await writeFile(path.join(output,'browser.json'),JSON.stringify({classification:'local provisional rendering, not deployed/current-season publication acceptance',manifest_sha256:'93b2b8f87809727e6fa72a2b3cbfae3e893e5d122bc025aee3ee19bd8254097d',browser:browser.version(),receipts,errors},null,2)+'\n');
 await browser.close();
}
