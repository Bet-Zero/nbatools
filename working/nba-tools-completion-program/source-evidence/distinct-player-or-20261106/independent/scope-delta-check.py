"""Independent common-opponent-list ownership checks against frozen seven-row oracles."""
import argparse,hashlib,json,os,pathlib,subprocess,sys
P=pathlib.Path(__file__).resolve().parent;ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--repo',type=pathlib.Path,required=True);ap.add_argument('--controlled',type=pathlib.Path,default=P/'controlled');ap.add_argument('--output',type=pathlib.Path,required=True);a=ap.parse_args();repo=a.repo.resolve();sys.path[:0]=[str(repo/'src'),str(repo)];os.environ.update(DATA_SOURCE='local',NBATOOLS_DATA_ROOT=str(a.controlled.resolve()),NBATOOLS_DATA_GENERATION='legacy')
from nbatools.query_service import execute_natural_query,execute_structured_query
from nbatools.api import app
from fastapi.testclient import TestClient
O=json.load(open(P/'oracle.json'));records=[];failures=[];calls=0
qs=[
 ('How many distinct players had (over 20 points or over 10 assists) in 2025-26 against the Warriors or against the Lakers?','controlled_union',None),
 ('How many distinct players had (over 20 points or over 10 assists) in 2025-26 against the Lakers or against the Warriors?','controlled_union',None),
 ('How many distinct players had (over 20 points or over 10 assists) in 2025-26 against the Warriors, Lakers?','controlled_union',None),
 ('How many distinct players against the Warriors or against the Lakers had (over 20 points or over 10 assists) in 2025-26?','controlled_union',None),
 ('How many Nuggets players had (over 20 points or over 10 assists) against the Warriors or against the Lakers in 2025-26?','controlled_team_DEN','DEN'),
]
for q,k,team in qs:
 try:
  r=execute_natural_query(q);calls+=1;c=O['cases'][k];b=r.result.to_dict();assert r.result_status=='ok' and r.metadata['primary_count']==c['distinct_players']
  assert r.metadata.get('team')==team and set(r.metadata.get('opponents') or [v.strip() for v in r.metadata['opponent'].split(',')])=={'LAL','GSW'},r.metadata
  assert {int(x['player_id']):int(x['matching_games']) for x in b['sections']['leaderboard']}==dict(c['player_occurrences'])
  h=TestClient(app).post('/query',json={'query':q});calls+=1;hb=h.json();assert h.status_code==200 and hb['result_status']=='ok' and hb['result']['metadata']['primary_count']==c['distinct_players']
  assert hb['result']['metadata'].get('team')==team and set(hb['result']['metadata'].get('opponents') or [v.strip() for v in hb['result']['metadata']['opponent'].split(',')])=={'LAL','GSW'}
  records.append({'query':q,'passed':True,'count':c['distinct_players'],'team':team,'opponents':['GSW','LAL'],'count_phrase':r.metadata['count_phrase'],'applied_filters':r.metadata['applied_filters']})
 except Exception as e:failures.append({'query':q,'error':repr(e)})
for scope in ['against the Warriors or against Unlistedclub','at home or on the road','against Boston or while injured']:
 q=f'How many distinct players had (over 20 points or over 10 assists) in 2025-26 {scope}?'
 try:
  r=execute_natural_query(q);calls+=1;assert r.result_status!='ok' and 'primary_count' not in r.metadata
  h=TestClient(app).post('/query',json={'query':q});calls+=1;assert h.status_code==200 and h.json()['result_status']!='ok'
  records.append({'unsupported_scope':scope,'passed':True})
 except Exception as e:failures.append({'query':q,'error':repr(e)})
# Existing structured common-scope contract applies to the same row population.
try:
 r=execute_structured_query('player_occurrence_leaders',season='2025-26',condition_expression='over 20 points or over 10 assists',opponent=['GSW','LAL'],team='DEN',limit=None);calls+=1
 assert r.result_status=='ok' and {int(x['player_id']):int(x['matching_games']) for x in r.result.to_dict()['sections']['leaderboard']}==dict(O['cases']['controlled_team_DEN']['player_occurrences'])
 records.append({'structured_subject_and_opponents':True,'passed':True})
except Exception as e:failures.append({'structured_subject_and_opponents':True,'error':repr(e)})
a.output.mkdir(parents=True,exist_ok=True);(a.output/'receipt.json').write_text(json.dumps({'revision':subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip(),'checks':records,'failures':failures,'query_invocations':calls,'skipped':0,'production_writes':0},indent=2)+'\n');print(json.dumps({'passed':len(records),'query_invocations':calls,'failures':failures},indent=2));sys.exit(bool(failures))
