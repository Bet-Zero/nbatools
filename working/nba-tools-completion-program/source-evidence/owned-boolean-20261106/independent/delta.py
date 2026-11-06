"""Recheck revealed identity/headline findings and related source/scope controls."""
import argparse,contextlib,json,os,pathlib,shutil,sys,subprocess
P=pathlib.Path(__file__).resolve().parent;ap=argparse.ArgumentParser();ap.add_argument('--repo',type=pathlib.Path,required=True);ap.add_argument('--output',type=pathlib.Path,required=True);a=ap.parse_args();R=a.repo.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True);sys.path[:0]=[str(R/'src'),str(R)]
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from nbatools.api import app
from nbatools.data_source import reset_data_source_cache
from nbatools.commands import query_boolean_parser as parser
from nbatools.query_service import execute_natural_query,execute_structured_query
O=json.loads((P/'oracle.json').read_text())['cases'];records=[];failures=[];calls=0
@contextlib.contextmanager
def capture():
 orig=parser.evaluate_condition_tree_to_mask;frames=[];depth=0
 def spy(n,d):
  nonlocal depth
  depth+=1
  try:
   m=orig(n,d)
   if depth==1:frames.append(d.loc[m].copy())
   return m
  finally:depth-=1
 parser.evaluate_condition_tree_to_mask=spy
 try:yield frames
 finally:parser.evaluate_condition_tree_to_mask=orig

def activate(root):os.environ.update(DATA_SOURCE='local',NBATOOLS_DATA_ROOT=str(root),NBATOOLS_DATA_GENERATION='legacy');reset_data_source_cache()
def check(name,fn):
 try:fn();records.append({'control':name,'passed':True})
 except Exception as e:failures.append({'control':name,'error':repr(e)});print('FAIL',name,repr(e),flush=True)
def noanswer(q):
 global calls
 r=execute_natural_query(q);calls+=1;assert r.result_status!='ok' and 'primary_count' not in r.metadata,(q,r.to_dict())

controlled=P/'prior-replay/controlled'
for damage in ['opponent_is_own_team','unknown_opponent_id','context_date_mismatch','nullable_venue','nullable_opponent_scope','unrequested_nullable_rate']:
 root=out/damage;shutil.copytree(controlled,root);pp=root/'data/raw/player_game_stats/2025-26_regular_season.csv';tp=root/'data/raw/team_game_stats/2025-26_regular_season.csv';p=pd.read_csv(pp);t=pd.read_csv(tp);g=p.game_id.eq(1)
 q='How many player games with (over 90 points or exactly 100 opponent points) in 2025-26?'
 if damage=='opponent_is_own_team':p.loc[g,'opponent_team_id']=p.loc[g,'team_id'];p.to_csv(pp,index=False)
 elif damage=='unknown_opponent_id':p.loc[g,'opponent_team_id']=float('nan');p.to_csv(pp,index=False)
 elif damage=='context_date_mismatch':t.loc[t.game_id.eq(1),'game_date']='2025-11-15';t.to_csv(tp,index=False)
 elif damage=='nullable_venue':p['is_home']=p['is_home'].astype(object);p.loc[g,'is_home']=None;p.to_csv(pp,index=False);q='How many player games with (over 20 points or exactly 100 team points) at home in 2025-26?'
 elif damage=='nullable_opponent_scope':p.loc[g,'opponent_team_id']=None;p.to_csv(pp,index=False);q='How many player games with (over 20 points or exactly 100 team points) against Golden State in 2025-26?'
 else:t.loc[t.game_id.eq(1),'ts_pct']=float('nan');t.to_csv(tp,index=False)
 activate(root)
 def run(q=q,damage=damage):
  global calls
  if damage=='unrequested_nullable_rate':
   r=execute_natural_query(q);calls+=1;assert r.result_status=='ok' and r.metadata['primary_count']==3,r.to_dict()
  else:noanswer(q)
 check(damage,run)
activate(controlled)
def headline():
 global calls
 q='How many distinct players had over 20 points and exactly 100 team points in 2025-26?';r=execute_natural_query(q);calls+=1;assert r.result_status=='ok' and r.metadata['primary_count']==2,r.to_dict();s=r.metadata['count_phrase'];assert 'matching game' in s or ('100' in s and 'team' in s),s
 checkdoc=TestClient(app).post('/query',json={'query':q}).json();calls+=1;assert checkdoc['result_status']=='ok' and checkdoc['result']['metadata']['primary_count']==2;assert 'matching game' in checkdoc['result']['metadata']['count_phrase'] or ('100' in checkdoc['result']['metadata']['count_phrase'] and 'team' in checkdoc['result']['metadata']['count_phrase'])
 records.append({'headline':s})
check('plain_owned_AND_complete_headline',headline)
for q in ['How many Nikola Jokic and Missing Player games had (over 20 points or exactly 100 team points) in 2025-26?','How many distinct players had (over 20 points or the team did not score exactly 100 points) in 2025-26?','How many distinct players had (over 20 points or exactly 100 team points) against Unlistedclub in 2025-26?']:check(q,lambda q=q:noanswer(q))
activate(P/'native-3f3f/native/native-stage')
for name,pid,expr,key in [('Stephen Curry',201939,'exactly 5 threes or at least 33 team assists','n_curry_threes'),('Kevon Looney',1626172,'(over 10 points or at least 4 assists) and at least 50 team rebounds','n_looney_reb'),('Jakob Poeltl',1627751,'at least 12 rebounds or exactly 110 team points','n_poeltl_team')]:
 def run(name=name,pid=pid,expr=expr,key=key):
  global calls
  e=O[key];q=f'How many {name} games had ({expr}) in 2022-23?'
  with capture() as seen:r=execute_natural_query(q);calls+=1
  assert r.result_status=='ok' and r.metadata['primary_count']==e['player_games'],r.to_dict();assert {(int(v.game_id),int(v.team_id),int(v.player_id)) for v in seen[-1].itertuples()}==set(map(tuple,e['keys']))
  h=TestClient(app).post('/query',json={'query':q});calls+=1;assert h.status_code==200 and h.json()['result']['metadata']['primary_count']==e['player_games'],h.json()
  for api in [False,True]:
   kw=dict(player=name,season='2022-23',condition_expression=expr,limit=None)
   d=TestClient(app).post('/structured-query',json={'route':'player_game_finder','kwargs':kw}).json()['result'] if api else execute_structured_query('player_game_finder',**kw).to_dict();calls+=1;assert d['result_status']=='ok';assert {(int(v['game_id']),int(v['player_id'])) for v in d['sections']['finder']}=={(k[0],k[2]) for k in e['keys']}
  # Revealed full-name list form also must work for the original frozen lists.
  if name!='Stephen Curry':
   d=execute_natural_query(f'List {name} games with ({expr}) in 2022-23');calls+=1;assert d.result_status=='ok' and {(int(v['game_id']),int(v['player_id'])) for v in d.to_dict()['sections']['finder']}=={(k[0],k[2]) for k in e['keys']}
  noanswer(f'How many {name} and Missing Player games had ({expr}) in 2022-23?')
 check('resolved_full_name_'+name,run)
result={'revision':subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip(),'checks':records,'failures':failures,'calls':calls};(out/'receipt.json').write_text(json.dumps(result,indent=2,default=str)+'\n');print(json.dumps({'checks':len(records),'calls':calls,'failures':failures},indent=2));sys.exit(bool(failures))
