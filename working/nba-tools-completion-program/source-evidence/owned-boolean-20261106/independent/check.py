"""Independent frozen raw-key and ownership acceptance, no source downloads."""
import argparse,contextlib,hashlib,json,os,pathlib,shutil,subprocess,sys
P=pathlib.Path(__file__).resolve().parent
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--repo',type=pathlib.Path,required=True);ap.add_argument('--output',type=pathlib.Path,required=True);ap.add_argument('--phase',choices=['controlled','native','all'],default='all');a=ap.parse_args();repo=a.repo.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True);sys.path[:0]=[str(repo/'src'),str(repo)]
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from nbatools.api import app
from nbatools.commands import query_boolean_parser as parser
from nbatools.data_source import reset_data_source_cache
from nbatools.query_service import execute_natural_query,execute_structured_query
assert hashlib.sha256((P/'oracle.json').read_bytes()).hexdigest()=='4d16e0cfa11d3bc4e6e1cc9af93700610ae4d81c6416964f342ef3f19b85a44b'
assert hashlib.sha256((P/'heldouts.json').read_bytes()).hexdigest()=='d8588c162450649e1885d0dfd9ef7bc0deeeeb48b6eb48f8ab449c2971fb09a7'
O=json.loads((P/'oracle.json').read_text())['cases'];H=json.loads((P/'heldouts.json').read_text())['cases'];records=[];failures=[];calls=0
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

def activate(mp,path):mp.setenv('DATA_SOURCE','local');mp.setenv('NBATOOLS_DATA_ROOT',str(path));mp.setenv('NBATOOLS_DATA_GENERATION','legacy');reset_data_source_cache()
def rawkeys(frame,e):
 lookup={(g,p):t for g,t,p in e['keys']}
 return {(int(r.game_id),int(r.team_id) if hasattr(r,'team_id') else lookup[(int(r.game_id),int(r.player_id))],int(r.player_id)) for r in frame.itertuples()}
def check(c,body,meta,observed):
 e=O[c['oracle']];assert body['result_status']=='ok',(c,body.get('result_reason'),meta)
 if c['grain']=='list':
  got={(int(v['game_id']),int(v['player_id'])) for v in body['sections']['finder']};assert got=={(k[0],k[2]) for k in e['keys']},(c,'listkeys',len(got))
 else:
  assert body['sections']['count']==[{'count':e[c['grain']]}],(c,body['sections'].get('count'))
  if c['grain']=='distinct_players':
   got={int(r['player_id']):int(r['matching_games']) for r in body['sections'].get('leaderboard',[])};assert got==dict(e['occurrences']),(c,'occurrences',got)
   assert 'player' in meta['count_phrase'] and 'player-game' not in meta['count_phrase']
  else: assert 'player-game' in meta['count_phrase'],(c,meta.get('count_phrase'))
 if observed:
  assert rawkeys(observed[-1],e)==set(map(tuple,e['keys'])),(c,'executedkeys')
  for s in ['pts','ast','reb']:assert observed[-1][s].sum()==e['sums'][s],(c,'sum',s)
 else:assert False,(c,'noexecutedmaskcaptured')

def natural(c):
 global calls
 try:
  with capture() as seen:r=execute_natural_query(c['query']);calls+=1
  check(c,r.result.to_dict(),r.metadata,seen)
  with capture() as seen:h=TestClient(app).post('/query',json={'query':c['query']});calls+=1
  assert h.status_code==200;d=h.json();check(c,d['result'],d['result'].get('metadata',{}),seen)
  records.append({**c,'passed':True,'count_phrase':r.metadata.get('count_phrase'),'applied_filters':r.metadata.get('applied_filters')})
 except Exception as e:failures.append({**c,'error':repr(e)});print('FAIL',c['oracle'],c['query'],repr(e),flush=True)

def structured(expr,oracle,**scope):
 global calls
 try:
  e=O[oracle]
  for route in ['player_occurrence_leaders','player_game_finder']:
   kw=dict(condition_expression=expr,limit=None,**scope)
   with capture() as seen:r=execute_structured_query(route,**kw);calls+=1
   assert r.result_status=='ok' if e['player_games'] else r.result_reason=='no_match',(route,r.to_dict())
   if e['player_games']:
    if route=='player_occurrence_leaders':assert {int(v['player_id']):int(v['matching_games']) for v in r.result.to_dict()['sections']['leaderboard']}==dict(e['occurrences'])
    else:assert {(int(v['game_id']),int(v['player_id'])) for v in r.result.to_dict()['sections']['finder']}=={(k[0],k[2]) for k in e['keys']}
   assert rawkeys(seen[-1],e)==set(map(tuple,e['keys']))
   with capture() as seen:h=TestClient(app).post('/structured-query',json={'route':route,'kwargs':kw});calls+=1
   assert h.status_code==200;d=h.json();assert d['result_status']=='ok' if e['player_games'] else d['result_reason']=='no_match'
   if e['player_games']:
    if route=='player_occurrence_leaders':assert {int(v['player_id']):int(v['matching_games']) for v in d['result']['sections']['leaderboard']}==dict(e['occurrences'])
    else:assert {(int(v['game_id']),int(v['player_id'])) for v in d['result']['sections']['finder']}=={(k[0],k[2]) for k in e['keys']}
   assert rawkeys(seen[-1],e)==set(map(tuple,e['keys']))
  records.append({'structured':expr,'oracle':oracle,'passed':True})
 except Exception as e:failures.append({'structured':expr,'oracle':oracle,'error':repr(e)});print('FAILstructured',oracle,repr(e),flush=True)

with pytest.MonkeyPatch.context() as mp:
 if a.phase in ['controlled','all']:
  controlled=P/'prior-replay/controlled';activate(mp,controlled)
  for c in H:
   if c['data']=='controlled':natural(c)
  for expr,key in [('over 20 points or exactly 100 team points','c_player_or_team'),('over 20 points or exactly 100 opponent points','c_player_or_opponent'),('(over 20 points and exactly 100 team points) or (over 10 assists and exactly 100 opponent points)','c_nested_owners'),('(over 20 points or over 10 assists) and exactly 100 opponent points','c_outer_opponent'),('exactly 0 team points or over 90 points','c_team_exact_zero')]:structured(expr,key,season='2025-26')
  # Every damaged source is a fresh root mutated before its first read.
  for damage in ['missing_team_source','missing_own_join','missing_opponent_join','unknown_team_pts','unknown_team_ast','unknown_opponent_pts','conflicting_team_duplicate']:
   root=out/damage;shutil.copytree(controlled,root);f=root/'data/raw/team_game_stats/2025-26_regular_season.csv';d=pd.read_csv(f);own=d.game_id.eq(1)&d.team_abbr.eq('DEN');opp=d.game_id.eq(1)&d.team_abbr.eq('GSW')
   if damage=='missing_team_source':f.unlink()
   elif damage=='missing_own_join':d.loc[~own].to_csv(f,index=False)
   elif damage=='missing_opponent_join':d.loc[~opp].to_csv(f,index=False)
   elif damage=='conflicting_team_duplicate':pd.concat([d,d.loc[own].assign(pts=123)]).to_csv(f,index=False)
   else:
    stat='ast' if damage=='unknown_team_ast' else 'pts';d.loc[opp if damage=='unknown_opponent_pts' else own,stat]=float('nan');d.to_csv(f,index=False)
   activate(mp,root);owner='opponent points' if 'opponent' in damage else 'team assists' if damage=='unknown_team_ast' else 'team points';query=f'How many distinct players had (over 20 points or exactly 100 {owner}) in 2025-26?'
   try:
    r=execute_natural_query(query);calls+=1;assert r.result_status!='ok' and 'primary_count' not in r.metadata,(damage,r.to_dict());records.append({'damage':damage,'passed':True,'reason':r.result_reason})
   except Exception as e:failures.append({'damage':damage,'error':repr(e)});print('FAILdamage',damage,repr(e),flush=True)
  activate(mp,controlled)
  for suffix in ['while injured','and (over 20 points against Boston or exactly 100 team points against Phoenix)','against Unlistedclub','when the Lakers score exactly 100 points']:
   q='How many distinct players had (over 20 points or exactly 100 team points) in 2025-26 '+suffix
   try:
    r=execute_natural_query(q);calls+=1;assert r.result_status!='ok' and 'primary_count' not in r.metadata,(q,r.to_dict());records.append({'unbound_clause':suffix,'passed':True})
   except Exception as e:failures.append({'unbound_clause':suffix,'error':repr(e)})
 if a.phase in ['native','all']:
  from tests.cloud_poeltl_full_season_real_data import build_qualified_stage
  root,_,_=build_qualified_stage(out/'native',mp);activate(mp,root)
  for c in H:
   if c['data']=='native':natural(c)
  for expr,key in [('over 37 points or under 100 opponent points','n_player_or_opponent'),('(exactly 29 points or team assists equal to 30) and exactly 12 opponent turnovers','n_equality_mixed'),('(over 37 points and at least 30 team assists) or (at least 12 rebounds and at most 100 opponent points)','n_nested_owners')]:structured(expr,key,season='2022-23')
result={'reviewed_revision':subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip(),'checker':'Separate Codex checker session /root/poeltl_source_checker; exact backend model not exposed','oracle_sha256':hashlib.sha256((P/'oracle.json').read_bytes()).hexdigest(),'phase':a.phase,'checks':records,'failures':failures,'query_invocations':calls,'production_writes':0,'skipped':0};(out/'receipt.json').write_text(json.dumps(result,indent=2,default=str)+'\n');print(json.dumps({'passed':len(records),'calls':calls,'failures':failures},indent=2));sys.exit(bool(failures))
