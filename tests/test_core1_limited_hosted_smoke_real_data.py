"""Temporary, bounded post-merge copy smoke; existing read-only R2 route only."""

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

import pytest
import requests

from tests.cloud_core_historical_delivery_real_data import LIVE, _readiness
from tests.core1_k08_runtime_binding import ROOT, _github, _local_build_tree, non_build

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


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


def test_post_merge_four_participation_explanations(tmp_path):
    assert os.environ["NBATOOLS_DATA_GENERATION"] == LIVE
    before = _binding()
    response = requests.get(before["url"] + "/readiness", timeout=30, allow_redirects=False)
    _readiness(response.status_code, response.json(), LIVE)
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "core1-limited-hosted"
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
    subprocess.run(
        ["npx", "playwright", "install", "chromium"],
        cwd=ROOT / "frontend",
        env=env,
        check=True,
        timeout=180,
    )
    script = r"""
import {chromium} from 'playwright';
import fs from 'node:fs';
const [base, output] = process.argv.slice(1);
const queries = ['Lakers record without Davis', 'Lakers record with Davis and Reaves both out',
 'LeBron James 30 point games with Davis', 'Lakers record vs Celtics and Knicks without Tatum'];
const browser = await chromium.launch({headless:true,args:['--no-sandbox']});
const receipts = [];
try {
 for (const width of [1280,390]) for (const [i,query] of queries.entries()) {
  await new Promise(resolve=>setTimeout(resolve,7000));
  const page=await browser.newPage({viewport:{width,height:900}});
  const pending=page.waitForResponse(r=>new URL(r.url()).pathname==='/query' && r.request().method()==='POST',{timeout:60000});
  await page.goto(base+'/?q='+encodeURIComponent(query));
  const response=await pending, body=await response.json();
  await page.getByText('Participation Not Verified',{exact:true}).waitFor();
  const text=await page.locator('body').innerText();
  if(response.status()!==200 || body.result_status!=='no_result' || !['unsupported','filter_not_supported'].includes(body.result_reason) ||
    Object.keys(body.result.sections).length || body.result.metadata.season!=='2025-26' || body.query!==query ||
    !text.includes('Missing records establish neither a missed game nor nonmembership') || !text.includes('Requested season: 2025-26') ||
    text.includes('Points is not available for this query')) throw new Error(JSON.stringify({query,body,text}));
  const assets=await page.locator('script[src]').evaluateAll(nodes=>nodes.map(n=>n.src).filter(s=>s.includes('/assets/index-')));
  if(assets.length!==1 || !assets[0].startsWith(base+'/assets/')) throw new Error('Unexpected served asset');
  await page.screenshot({path:output+'/'+width+'-'+i+'.png',fullPage:true});
  receipts.push({width,query,status:response.status(),body,text,assets});
  await page.close();
 }
} finally { await browser.close(); fs.writeFileSync(output+'/browser.json',JSON.stringify(receipts,null,2)); }
if(receipts.length!==8) throw new Error('Incomplete capture');
console.log('8/8 actual hosted copy checks passed; no NBA requests, writes or readiness waiver');
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
    _readiness(response.status_code, response.json(), LIVE)
    (output / "binding.json").write_text(json.dumps(before, indent=2))
