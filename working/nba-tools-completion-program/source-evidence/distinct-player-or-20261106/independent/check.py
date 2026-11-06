"""Independent distinct-OR checking against pre-author raw row/group oracles."""
import argparse,contextlib,hashlib,json,os,pathlib,shutil,subprocess,sys
P=pathlib.Path(__file__).resolve().parent;ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--repo',type=pathlib.Path,default=P/'review');ap.add_argument('--oracle',type=pathlib.Path,default=P/'oracle.json');ap.add_argument('--heldouts',type=pathlib.Path,default=P/'heldouts.json');ap.add_argument('--supplement',type=pathlib.Path,default=P/'wording-supplement.json');ap.add_argument('--controlled',type=pathlib.Path,default=P/'controlled');ap.add_argument('--output',type=pathlib.Path,default=P/'results');ap.add_argument('--phase',choices=['controlled','native','all'],default='all');a=ap.parse_args();repo=a.repo.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True);sys.path[:0]=[str(repo/'src'),str(repo)]
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from nbatools.api import app
from nbatools.commands import query_boolean_parser as parser
from nbatools.data_source import reset_data_source_cache
from nbatools.query_service import execute_natural_query,execute_structured_query
assert hashlib.sha256(a.oracle.read_bytes()).hexdigest()=='9915885cc7afa1ba96cb47e8d38aa621c808a41ed3146b6c35ad96aeb596afd6'
O=json.loads(a.oracle.read_text());H=json.loads(a.heldouts.read_text())['cases']+json.loads(a.supplement.read_text())['cases'];records=[];failures=[];calls=0
UNFINISHED={'controlled_team_owned','native_team_owned','native_opponent_owned'}
def activate(mp,path):mp.setenv('DATA_SOURCE','local');mp.setenv('NBATOOLS_DATA_ROOT',str(path));mp.setenv('NBATOOLS_DATA_GENERATION','legacy');reset_data_source_cache()
def keys(df,expected):
 lookup={(int(g),int(p)):int(t) for g,t,p in expected['selected_keys']}
 return {(int(r.game_id),int(r.team_id) if hasattr(r,'team_id') else lookup[(int(r.game_id),int(r.player_id))],int(r.player_id)) for r in df.itertuples()}
@contextlib.contextmanager
def capture():
 original=parser.evaluate_condition_tree_to_mask;observed=[];depth=0
 def spy(node,frame):
  nonlocal depth
  depth+=1
  try:
   mask=original(node,frame)
   if depth==1:observed.append(frame.loc[mask].copy())
   return mask
  finally:depth-=1
 parser.evaluate_condition_tree_to_mask=spy
 try:yield observed
 finally:parser.evaluate_condition_tree_to_mask=original

def check_body(c,body,meta,observed):
 expected=O['cases'][c['oracle']]
 if c['oracle'] in UNFINISHED:
  assert body['result_status']!='ok' and 'primary_count' not in meta,(c,body)
  return
 assert body['result_status']=='ok',(c,body.get('result_reason'),meta)
 assert body['sections']['count']==[{'count':expected[c['grain']]}],(c,body['sections'].get('count'))
 if c['grain']=='distinct_players':
  leaders=body['sections'].get('leaderboard',[])
  got={int(r['player_id']):int(r['matching_games']) for r in leaders}
  assert got==dict(expected['player_occurrences']),(c,got,dict(expected['player_occurrences']))
  assert len(leaders)==len(got)==expected['distinct_players']
  assert 'player' in meta['count_phrase'] and 'player-game' not in meta['count_phrase']
  assert any(f.get('kind')=='boolean' for f in meta['applied_filters'])
 else:
  rows=body['sections']['finder'];assert {(int(r['game_id']),int(r['player_id'])) for r in rows}=={(r[0],r[2]) for r in expected['selected_keys']}
  assert 'player-game' in meta['count_phrase']
 if observed:assert keys(observed[-1],expected)==set(map(tuple,expected['selected_keys'])),(c,'executedkeymismatch')
 else:assert c['grain']=='player_games',(c,'noexecutedmaskcapture')

def natural(c):
 global calls
 try:
  with capture() as seen:r=execute_natural_query(c['query']);calls+=1
  check_body(c,r.result.to_dict(),r.metadata,seen)
  with capture() as seen:h=TestClient(app).post('/query',json={'query':c['query']});calls+=1
  assert h.status_code==200;hb=h.json();check_body(c,hb['result'],hb['result'].get('metadata',{}),seen)
  records.append({**c,'passed':True,'acceptance':'safe_unsupported_unfinished' if c['oracle'] in UNFINISHED else 'positive','count':r.result.to_dict()['sections'].get('count'),'count_phrase':r.metadata.get('count_phrase')})
 except Exception as e:failures.append({**c,'error':repr(e)});print('FAIL',c['query'],repr(e),flush=True)

def structured(expression,oracle,**scope):
 global calls
 try:
  with capture() as seen:r=execute_structured_query('player_occurrence_leaders',condition_expression=expression,limit=None,**scope);calls+=1
  expected=O['cases'][oracle]
  if not expected['distinct_players']:assert r.result_reason=='no_match'
  else:assert r.result_status=='ok' and {int(v['player_id']):int(v['matching_games']) for v in r.result.to_dict()['sections']['leaderboard']}==dict(expected['player_occurrences'])
  assert keys(seen[-1],expected)==set(map(tuple,expected['selected_keys']))
  with capture() as seen:h=TestClient(app).post('/structured-query',json={'route':'player_occurrence_leaders','kwargs':dict(condition_expression=expression,limit=None,**scope)});calls+=1
  assert h.status_code==200
  hb=h.json()
  if expected['distinct_players']:assert {int(v['player_id']):int(v['matching_games']) for v in hb['result']['sections']['leaderboard']}==dict(expected['player_occurrences'])
  else:assert hb['result_reason']=='no_match'
  assert keys(seen[-1],expected)==set(map(tuple,expected['selected_keys']))
  records.append({'structured':expression,'oracle':oracle,'passed':True})
 except Exception as e:failures.append({'structured':expression,'oracle':oracle,'error':repr(e)});print('FAILstructured',repr(e),flush=True)

with pytest.MonkeyPatch.context() as mp:
 if a.phase in ['controlled','all']:
  activate(mp,a.controlled.resolve())
  for c in H:
   if c['data']=='controlled':natural(c)
  structured('(over 20 points or over 10 assists)','controlled_union',season='2025-26')
  structured('(over 20 points or over 10 assists) and exactly 25 points','controlled_outer_exact25pts',season='2025-26')
  structured('(over 20 points or over 10 assists)','controlled_team_DEN',season='2025-26',team='DEN')
  structured('(over 90 points or over 90 assists)','controlled_zero',season='2025-26')
  activate(mp,repo/'qa/fixtures/query_engine_sample')
  for c in H:
   if c['data']=='synthetic_full':natural(c)
  # Each damage source has a fresh root and is mutated before its first read.
  for damage in ['missing_source','missing_branch','unknown_branch','unknown_scope','alias_identity','missing_season']:
   root=out/damage;shutil.copytree(a.controlled,root);path=root/'data/raw/player_game_stats/2025-26_regular_season.csv';d=pd.read_csv(path)
   if damage=='missing_source':path.unlink()
   elif damage=='missing_branch':d.drop(columns='ast').to_csv(path,index=False)
   elif damage=='unknown_branch':d.loc[0,'ast']=float('nan');d.to_csv(path,index=False)
   elif damage=='unknown_scope':d['is_home']=d['is_home'].astype(object);d.loc[0,'is_home']=None;d.to_csv(path,index=False)
   elif damage=='alias_identity':d.loc[d.game_id.eq(1)&d.player_id.eq(203999),'player_name']='Controlled alternate spelling';d.to_csv(path,index=False)
   activate(mp,root)
   q='How many distinct players had (over 20 points or over 10 assists) in 2025-26?'
   if damage=='unknown_scope':q=q[:-1]+' at home?'
   try:
    if damage=='missing_season':r=execute_structured_query('player_occurrence_leaders',condition_expression='over 20 points or over 10 assists',start_season='2021-22',end_season='2025-26',limit=None)
    else:r=execute_natural_query(q)
    calls+=1
    if damage=='alias_identity':assert r.result_status=='ok' and r.metadata['primary_count']==3 and {v['player_id']:v['matching_games'] for v in r.result.to_dict()['sections']['leaderboard']}==dict(O['cases']['controlled_union']['player_occurrences'])
    else:assert r.result_status!='ok' and 'primary_count' not in r.metadata,(damage,r.to_dict())
    records.append({'control':damage,'passed':True,'status':r.result_status,'reason':r.result_reason})
   except Exception as e:failures.append({'control':damage,'error':repr(e)})
  activate(mp,a.controlled.resolve())
  for suffix in ['when everyone was happy','against Unlistedclub','while injured','and (over 20 points against Boston or over 10 assists against Phoenix)','in the last 3 games']:
   q='How many distinct players had (over 20 points or over 10 assists) in 2025-26 '+suffix
   try:
    r=execute_natural_query(q);calls+=1;assert r.result_status!='ok' and 'primary_count' not in r.metadata,(q,r.to_dict());records.append({'unread_scope':suffix,'passed':True})
   except Exception as e:failures.append({'unread_scope':suffix,'error':repr(e)})
 if a.phase in ['native','all']:
  from tests.cloud_poeltl_full_season_real_data import build_qualified_stage
  root,_,_=build_qualified_stage(out/'native',mp);activate(mp,root)
  for c in H:
   if c['data']=='native':natural(c)
  structured('over 37 points or over 10 assists','native_union',season='2022-23')
  structured('(over 37 points and at least 7 assists) or (at least 18 rebounds and at least 3 blocks)','native_grouped_and_or',season='2022-23')
  structured('over 37 points or over 10 assists','native_opponent_BOS',season='2022-23',opponent='BOS')
result={'reviewed_revision':subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip(),'checker':'/root/poeltl_source_checker; independent Codex session, exact backend model not exposed','oracle_sha256':hashlib.sha256(a.oracle.read_bytes()).hexdigest(),'phase':a.phase,'checks':records,'failures':failures,'query_invocations':calls,'skipped':0,'production_writes':0};(out/'receipt.json').write_text(json.dumps(result,indent=2,default=str)+'\n');print(json.dumps({'passed':len(records),'query_invocations':calls,'failures':failures},indent=2));sys.exit(bool(failures))
