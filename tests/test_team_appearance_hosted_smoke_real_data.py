"""Temporary, bounded post-merge participation smoke; existing read-only R2 route only."""

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

import pytest
import requests

from tests.cloud_core_historical_delivery_real_data import _readiness
from tests.core1_k08_runtime_binding import ROOT, _github, _local_build_tree, non_build

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
CURRENT = "availability-season-inactive-2024-v1-20261116"


def _binding():
    # Current Vercel bot links identify the same existing project under its
    # renamed zeros-projects slug. Accept only this exact immutable host family;
    # do not change the legacy capture helper, protection, aliases or access.
    (deployment,) = _github("deployments?environment=Production&per_page=1")
    assert deployment["creator"]["login"] == "vercel[bot]"
    (status,) = _github(f"deployments/{deployment['id']}/statuses?per_page=1")
    assert status["state"] == "success" and status["creator"]["login"] == "vercel[bot]"
    url = status["environment_url"].rstrip("/")
    assert re.fullmatch(r"https://nbatools-[a-z0-9]+-zeros-projects-686e97fc\.vercel\.app", url)
    tree = _github(f"git/trees/{deployment['sha']}?recursive=1")
    assert not tree["truncated"]
    remote = {
        e["path"]: dict(mode=e["mode"], sha=e["sha"])
        for e in tree["tree"]
        if e["type"] == "blob" and not non_build(e["path"])
    }
    assert remote == _local_build_tree(), "Production build inputs differ from the reviewed app"
    return dict(
        id=deployment["id"],
        sha=deployment["sha"],
        url=url,
        build_sha256=hashlib.sha256(json.dumps(remote, sort_keys=True).encode()).hexdigest(),
    )


def test_post_merge_team_appearance_scopes(tmp_path):
    assert os.environ["NBATOOLS_DATA_GENERATION"] == CURRENT
    before = _binding()
    response = requests.get(before["url"] + "/readiness", timeout=30, allow_redirects=False)
    _readiness(response.status_code, response.json(), CURRENT)
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]).resolve() / "team-appearance-hosted"
    output.mkdir(parents=True, exist_ok=False)
    allowed = {
        "PATH",
        "HOME",
        "TMPDIR",
        "CI",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "NO_PROXY",
        "NODE_EXTRA_CA_CERTS",
        "SSL_CERT_FILE",
    }
    env = {k: v for k, v in os.environ.items() if k in allowed}
    subprocess.run(
        ["npm", "ci", "--ignore-scripts", "--no-audit"],
        cwd=ROOT / "frontend",
        env=env,
        check=True,
        timeout=180,
    )
    script = r"""
import {chromium} from 'playwright';
import fs from 'node:fs';
const [base, output] = process.argv.slice(1);
const queries = [
 ['Cavaliers record without Stephen Curry vs Warriors in 2024-25','ok','team'],
 ['Cavaliers record without Stephen Curry anywhere in the game vs Warriors in 2024-25','no_match','game'],
 ['Cavaliers record without Caris LeVert in 2024-25','unknown','team']
];
let executablePath;
for (const file of ['/usr/bin/google-chrome','/usr/bin/chromium','/usr/bin/chromium-browser']) {
 if (fs.existsSync(file)) { executablePath=file; break; }
}
if(!executablePath) throw new Error('Runner browser unavailable; required check cannot skip');
const browser = await chromium.launch({executablePath,headless:true,args:['--no-sandbox']});
const receipts = [];
try {
 for (const width of [1280,390]) for (const [i,[query,expected,scope]] of queries.entries()) {
  await new Promise(resolve=>setTimeout(resolve,7000));
  const page=await browser.newPage({viewport:{width,height:900}});
  const pending=page.waitForResponse(r=>new URL(r.url()).pathname==='/query' && r.request().method()==='POST',{timeout:60000});
  await page.goto(base+'/?q='+encodeURIComponent(query));
  const response=await pending, body=await response.json();
  const visible=expected==='ok'?'The Cleveland Cavaliers are 2-0':expected==='no_match'?'appearances anywhere in each game':'Participation Not Verified';
  await page.waitForFunction(t=>document.body.innerText.includes(t),visible,{timeout:60000});
  const text=await page.locator('body').innerText(), meta=body.result.metadata;
  if(response.status()!==200 || meta.team!=='CLE' || meta.season!=='2024-25' || meta.season_type!=='Regular Season' ||
     meta.participation_scope!==scope || body.query!==query || text.includes('Points is not available')) throw new Error(JSON.stringify({query,body,text}));
  if(expected==='ok') {
    const s=body.result.sections.summary[0];
    const ids=body.result.sections.game_log.map(r=>Number(r.game_id)).sort((a,b)=>a-b);
    if(body.result_status!=='ok'||s.games!==2||s.wins!==2||s.losses!==0||s.pts_avg!==124.5||
       JSON.stringify(ids)!==JSON.stringify([22400188,22400446])||!text.includes('FOR selected team; before joining / after leaving included'))throw new Error(JSON.stringify({query,body,text}));
  } else {
    if(body.result_status!=='no_result'||Object.keys(body.result.sections).length||text.includes('Verified nonmembers are excluded'))throw new Error(JSON.stringify({query,body,text}));
    if(expected==='no_match'&&body.result_reason!=='no_match')throw new Error('Wrong empty interpretation');
    if(expected==='unknown'&&(!['unsupported','filter_not_supported'].includes(body.result_reason)||!body.notes.some(n=>n.startsWith('Incomplete team appearance coverage for Caris LeVert'))))throw new Error('Unknown became empty or complete');
  }
  const assets=await page.locator('script[src]').evaluateAll(nodes=>nodes.map(n=>n.src).filter(s=>s.includes('/assets/index-')));
  if(assets.length!==1 || !assets[0].startsWith(base+'/assets/')) throw new Error('Unexpected served asset');
  await page.screenshot({path:output+'/'+width+'-'+i+'.png',fullPage:true});
  receipts.push({width,query,status:response.status(),body,text,assets});
  await page.close();
 }
} finally { await browser.close(); fs.writeFileSync(output+'/browser.json',JSON.stringify(receipts,null,2)); }
if(receipts.length!==6) throw new Error('Incomplete capture');
console.log('6/6 actual hosted team/game/unknown checks passed; no NBA source acquisition, writes or readiness waiver');
"""
    subprocess.run(
        ["node", "--input-type=module", "-e", script, before["url"], str(output)],
        cwd=ROOT / "frontend",
        env=env,
        check=True,
        timeout=600,
    )
    assert _binding() == before
    response = requests.get(before["url"] + "/readiness", timeout=30, allow_redirects=False)
    _readiness(response.status_code, response.json(), CURRENT)
    (output / "binding.json").write_text(json.dumps(before, indent=2))
