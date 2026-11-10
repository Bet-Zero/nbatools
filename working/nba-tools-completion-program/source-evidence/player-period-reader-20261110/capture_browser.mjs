// Actual browser -> existing loopback HTTP app -> pinned qualified source rows.
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
 ['quarter', 'Austin Reaves second quarter points on 2026-11-04', 'ok', 22600185, 4, 2, 0, 'Quarter'],
 ['half', 'Austin Reaves first half assists on 2026-11-04', 'ok', 22600185, 9, 2, 1, 'Half'],
 ['ot', 'Saddiq Bey overtime points on 2026-11-04', 'ok', 22600179, 8, 1, 0, 'Quarter'],
 ['null-preserved', 'Kevin Durant fourth quarter points on 2026-10-21', 'ok', 22600091, null, null, null, 'Quarter'],
 ['unknown-rate', 'Kevin Durant fourth quarter usage percentage in 2026-27', 'no_data'],
 ['unknown-or', 'Kevin Durant fourth quarter games with over 1000 points or over 0 usage percentage in 2026-27', 'no_data'],
 ['sum', 'How many points did Austin Reaves score in second quarters on 2026-11-04?', 'sum'],
 ['zero-count', 'Ryan Kalkbrenner second quarter points on 2026-11-04', 'ok', 22600176, 0, 1, 1, 'Quarter'],
 ['zero-derived', 'Ryan Kalkbrenner second quarter games with at least 0 true shooting percentage on 2026-11-04', 'no_data'],
 ['context-basis', 'Austin Reaves second quarter games when opponents score at least 20 points on 2026-11-04', 'no_data'],
].filter(c=>process.argv[3]==='delta' ? ['zero-count','zero-derived','context-basis'].includes(c[0]) : !['zero-count','zero-derived','context-basis'].includes(c[0]));
const browser = await chromium.launch({executablePath:'/usr/bin/chromium',headless:true});
const receipts=[]; const errors=[];
try {
 for (const [viewport,width,height] of [['desktop',1280,900],['mobile',390,844]]) {
  const page=await browser.newPage({viewport:{width,height}});
  page.on('pageerror',error=>errors.push(String(error)));
  await page.goto('http://127.0.0.1:8765');
  for (const [id,query,status,game,points,rebounds,assists,period] of cases) {
   await page.locator('#nba-query-input').fill(query);
   const pending=page.waitForResponse(r=>r.url()==='http://127.0.0.1:8765/query'&&r.request().method()==='POST');
   await page.getByRole('button',{name:'Query',exact:true}).click();
   const response=await pending;
   await page.locator('[data-app-state="loading"]').waitFor({state:'detached'});
   if (id==='null-preserved' || id==='zero-count') {
    await page.getByRole('button',{name:'Show additional columns',exact:true}).click();
    await page.getByText('Details',{exact:true}).click();
   }
   if (status==='no_data' && !(await page.locator('[data-state-surface="result"]').innerText()).includes('PROVISIONAL')) {
    await page.getByText('Details',{exact:true}).click();
   }
   const text=await page.locator('[data-state-surface="result"]').innerText();
   const payload=await response.json();
   const quality=payload.result.metadata.data_quality;
   if (response.status()!==200 || !text.includes('PROVISIONAL') || quality.manifest_sha256!=='e46b6748887d263a342b44dd896e6f4cd2619fd824428f4842dda5be0ac380b7' || quality.production_accepted!==false) throw Error('False isolation/label');
   if (status==='no_data') {
    if (payload.result_status!=='no_result' || payload.result_reason!=='no_data' || Object.keys(payload.result.sections).length || !text.includes('Data Not Available')) throw Error('Unknown-dependent answer escaped');
   } else if (status==='sum') {
    if (payload.result_status!=='ok' || payload.result.sections.count[0].count!==4 || !text.includes('4')) throw Error('Wrong period sum');
   } else {
    const rows=payload.result.sections.finder;
    if (payload.result_status!=='ok' || rows.length!==1 || rows[0].game_id!==game || !text.includes(period)) throw Error('Wrong period sample/render');
    if (points!==null && (rows[0].pts!==points || rows[0].reb!==rebounds || rows[0].ast!==assists)) throw Error('Wrong independent source values');
    if (id==='null-preserved' && (rows[0].usg_pct!==null || rows[0].tov_pct!==null || !text.includes('Unrequested source rates remain unknown'))) throw Error('Unknown rates hidden or zeroed');
    if (id==='zero-count' && (rows[0].ts_pct!==null || rows[0].efg_pct!==null)) throw Error('Undefined derived ratio set to zero');
   }
   const tables=await page.locator('table').evaluateAll(nodes=>nodes.map(n=>({text:n.innerText,headers:Array.from(n.querySelectorAll('th')).map(c=>c.innerText),rows:Array.from(n.querySelectorAll('tbody tr')).map(r=>Array.from(r.querySelectorAll('td')).map(c=>c.innerText))})));
   if (id==='null-preserved') {
    const detail=tables.find(t=>t.headers.includes('USG PCT'));
    if (!detail || detail.rows[0][detail.headers.indexOf('USG PCT')]!=='—' || detail.rows[0][detail.headers.indexOf('TOV PCT')]!=='—') throw Error('Native unknown not visibly retained');
   }
   if (id==='zero-count') {
    const detail=tables.find(t=>t.headers.includes('TS PCT'));
    if (!detail || detail.rows[0][detail.headers.indexOf('TS PCT')]!=='—' || detail.rows[0][detail.headers.indexOf('EFG PCT')]!=='—') throw Error('Undefined derived ratio not visibly retained');
   }
   if (id==='null-preserved' || id==='zero-count') {
    await page.locator('table').last().evaluate(table=>{for(let el=table.parentElement;el&&el!==document.body;el=el.parentElement) if(el.scrollWidth>el.clientWidth) el.scrollLeft=el.scrollWidth;});
   }
   const screenshot=`${viewport}-${id}.png`;
   const raw=await page.screenshot({path:path.join(output,screenshot),fullPage:true,animations:'disabled'});
   const overflow=await page.evaluate(()=>({viewport:innerWidth,document:document.documentElement.scrollWidth}));
   if (overflow.document>width) throw Error('Document overflow');
   receipts.push({id,viewport,query,capturedAt:new Date().toISOString(),text,tables,payload,http:response.status(),overflow,screenshot,screenshotSha256:createHash('sha256').update(raw).digest('hex')});
  }
  await page.close();
 }
 if (errors.length) throw Error(JSON.stringify(errors));
} finally {
 await writeFile(path.join(output,'browser.json'),JSON.stringify({classification:'local qualified-input provisional rendering; not deployed acceptance',manifest_sha256:'e46b6748887d263a342b44dd896e6f4cd2619fd824428f4842dda5be0ac380b7',browser:browser.version(),receipts,errors},null,2)+'\n');
 await browser.close();
}
