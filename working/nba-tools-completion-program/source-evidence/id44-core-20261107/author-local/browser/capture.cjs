const { chromium } = require(require('path').resolve('frontend/node_modules/playwright'));
const fs = require('fs'); const crypto=require('crypto');
const path=require('path');
(async()=>{
 const output='working/nba-tools-completion-program/source-evidence/id44-core-20261107/author-local/browser';fs.mkdirSync(output,{recursive:true});
 const oracle=JSON.parse(fs.readFileSync('working/nba-tools-completion-program/source-evidence/id44-core-20261107/independent/source-qualified-oracle.json'));
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 const receipt={source_revision:'ee2f5d89',classification:'actual local desktop/mobile on original-derived historical full82 population; canonical R2 match pending; not deployed acceptance',cases:[]};
 for(const viewport of [{width:1365,height:900},{width:390,height:844}]){
  for(const polarity of ['without','with']){
   const page=await browser.newPage({viewport});const errors=[]; page.on('pageerror',e=>errors.push(e.message));
   await page.goto('http://127.0.0.1:8765/',{waitUntil:'networkidle'});
   const q=`Thunder record ${polarity} Kevin Durant in 2007-08`;
   await page.locator('#nba-query-input').fill(q);
   const response=page.waitForResponse(r=>r.url().endsWith('/query')&&r.request().method()==='POST');
   await page.locator('#nba-query-input').press('Enter');const res=await response;const body=await res.json();
   await page.waitForFunction(()=>document.body.innerText.includes('RECORD DETAIL'));const text=await page.locator('body').innerText();
   const exp=oracle.expected[polarity], sum=body.result.sections.summary[0];
   if(res.status()!==200||body.result_status!=='ok'||sum.games!==exp.games||sum.wins!==exp.wins||sum.losses!==exp.losses)throw Error('wrong numerical result');
   if(JSON.stringify(body.result.sections.game_log.map(x=>String(x.game_id).padStart(10,'0')).sort())!==JSON.stringify(exp.game_ids.slice().sort()))throw Error('wrong selected keys');
   if(!text.includes('Seattle SuperSonics')||!text.includes(`${exp.wins}-${exp.losses}`)||!text.includes('Kevin Durant')||text.includes('undefined')||text.includes('NaN')||errors.length)throw Error('wrong rendered scope');
   const overflow=await page.evaluate(()=>({document:document.documentElement.scrollWidth,viewport:innerWidth}));if(overflow.document>overflow.viewport)throw Error('page overflow');
   const file=`${polarity}-${viewport.width}.png`;await page.screenshot({path:path.join(output,file),fullPage:true});
   receipt.cases.push({query:q,viewport,http:res.status(),payload:body,text,errors,overflow,screenshot:file,sha256:crypto.createHash('sha256').update(fs.readFileSync(path.join(output,file))).digest('hex'),assets:await page.locator('script[src]').evaluateAll(es=>es.map(e=>e.src))});await page.close();
  }
 }
 await browser.close();fs.writeFileSync(path.join(output,'receipt.json'),JSON.stringify(receipt,null,2)+'\n');console.log('4 actual rendered outputs passed');
})().catch(e=>{console.error(e);process.exit(1)});
