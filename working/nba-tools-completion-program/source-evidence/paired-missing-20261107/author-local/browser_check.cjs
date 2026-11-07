const {chromium}=require('playwright');
const fs=require('fs');
(async()=>{const browser=await chromium.launch({headless:true,executablePath:"/usr/bin/chromium",args:["--no-sandbox"]});const out='work/paired-missing/browser';fs.mkdirSync(out,{recursive:true});const results=[];
for(const viewport of [{width:1365,height:900},{width:390,height:844}]){
 const page=await browser.newPage({viewport}); await page.goto('http://127.0.0.1:8031/');
 for(const [id,query,expected]of [
 ['nonempty','Celtics record with Tatum and Brown missing in 2025-26','7'],
 ['record-zero','Lakers record with Davis and Reaves missing in 2023-24','No games'],
 ['count-zero','How many Lakers games with Davis and Reaves missing in 2023-24?','0'],
 ['player-bound','Austin Reaves games with 20 points with LeBron James and Anthony Davis missing against Boston in 2023-24','32']]){
  await page.locator('#nba-query-input').fill(query);
  const responsePromise=page.waitForResponse(r=>r.url().endsWith('/query')&&r.request().method()==='POST');await page.getByRole('button',{name:'Query',exact:true}).click();const response=await responsePromise;const body=await response.json(); await page.waitForFunction(expected=>document.body.innerText.includes(expected),expected);
  const text=await page.locator('body').innerText();if(!text.includes(expected))throw new Error(id+' missing displayed expected '+expected+' : '+text.slice(-1500));
  const file=`${out}/${id}-${viewport.width}.png`;await page.screenshot({path:file,fullPage:true}); results.push({id,query,viewport,http_status:response.status(),result_status:body.result_status,result_reason:body.result_reason,metadata:body.result.metadata,display_text:text,screenshot:file});
 }
 await page.close();
}
await browser.close();fs.writeFileSync(out+'/receipt.json',JSON.stringify({source:'b29aa469f80b829c49deec54d495e23956c84aa8',scope:'qualified_local_slices_not_production_or_all_Core1',cases:results},null,2));console.log(JSON.stringify({browser_cases:results.length,status:'pass',out}));})().catch(e=>{console.error(e);process.exit(1)});
