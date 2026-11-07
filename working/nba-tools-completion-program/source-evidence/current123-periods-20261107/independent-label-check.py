"""Independent exact caveat/meaning checks on the frozen real period data."""
import asyncio,hashlib,json,os,zipfile
from pathlib import Path
import httpx
from nbatools.api_handlers import natural_query_payload
from nbatools.query_service import execute_structured_query
from nbatools.development_data import development_snapshot
from tools.development_query import create_app
ROOT=Path('/workspace/nbatools');OUT=ROOT/'work/current123-period-independent';FOLDER=OUT/'label-stage'
E=ROOT/'working/nba-tools-completion-program/source-evidence/current123-periods-20261107'
b=json.loads((E/'binding.json').read_bytes());p=E/b['archive'];assert hashlib.sha256(p.read_bytes()).hexdigest()=='a0ab6f64958018b3ca9b535ed6ef2ae316f01c55c40d27edd21677ff79ad9175'
FOLDER.mkdir(exist_ok=False)
with zipfile.ZipFile(p) as z:z.extractall(FOLDER)
os.environ['DATA_SOURCE']='local';os.environ.pop('VERCEL_ENV',None)
cases=[('Lakers second quarter record on 2026-11-04','LAL',{'quarter':'2'},'quarter 2',1,0,33),('Lakers first half record on 2026-11-04','LAL',{'half':'first'},'first half',1,0,61),('Pelicans overtime record on 2026-11-04','NOP',{'quarter':'OT'},'overtime',1,0,16),('Clippers overtime record on 2026-11-04','LAC',{'quarter':'OT'},'overtime',0,1,9)]
results=[]
async def http(query):
 async with httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(FOLDER,b['manifest_sha256'])),base_url='http://127.0.0.1') as client:
  result=await client.post('/query',json={'query':query});assert result.status_code==200;return result.json()
for query,team,window,label,w,l,pts in cases:
 expected=f'record computed from {label} scores'
 with development_snapshot(FOLDER,b['manifest_sha256']):
  n=natural_query_payload(query)
  s=execute_structured_query('team_record',team=team,season='2026-27',start_date='2026-11-04',end_date='2026-11-04',**window)
 assert s.result_status=='ok' and expected in s.result.caveats
 sr=s.result.to_dict()['sections']['summary'][0];assert (sr['games'],sr['wins'],sr['losses'],sr['pts_avg'])==(1,w,l,pts)
 h=asyncio.run(http(query))
 for body in [n,h]:
  assert body['result_status']=='ok' and expected in body['caveats']
  assert not any('computed from 2 windows' in v or 'first windows' in v or 'OT windows' in v for v in body['caveats'])
  r=body['result']['sections']['summary'][0];assert (r['games'],r['wins'],r['losses'],r['pts_avg'])==(1,w,l,pts)
  quality=body['result']['metadata']['data_quality'];assert quality['manifest_sha256']==b['manifest_sha256'] and quality['state']=='provisional' and quality['numerical_acceptance'] is False
 results.append({'query':query,'exact_caveat':expected,'natural_structured_HTTP':'passed','games':1,'wins':w,'losses':l,'points':pts})
receipt={'source_file_sha256':hashlib.sha256((ROOT/'src/nbatools/commands/team_record.py').read_bytes()).hexdigest(),'dataset_zip_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'manifest_sha256':b['manifest_sha256'],'cases':results,'nba_requests':0,'production_writes':0,'numeric_and_selection_delta':'none; exact independently qualified expected values retained'}
(OUT/'label-delta-results.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
