"""Independent equality review against frozen raw-row oracles, never parser expectations."""
import argparse, csv, hashlib, json, math, os, pathlib, shutil, subprocess, sys
import pytest
P=pathlib.Path(__file__).resolve().parent
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--repo',type=pathlib.Path,default=pathlib.Path.cwd());ap.add_argument('--oracle',type=pathlib.Path,default=P/'oracle.json');ap.add_argument('--heldouts',type=pathlib.Path,default=P/'heldouts.json');ap.add_argument('--output',type=pathlib.Path,default=P/'results');ap.add_argument('--phase',choices=['fixture','native','safety','all'],default='all')
a=ap.parse_args();repo=a.repo.resolve();output=a.output.resolve();output.mkdir(parents=True,exist_ok=True)
sys.path[:0]=[str(repo/'src'),str(repo)]
from fastapi.testclient import TestClient
from nbatools.api import app
from nbatools.data_source import reset_data_source_cache
from nbatools.query_service import execute_natural_query,execute_structured_query
O=json.loads(a.oracle.read_text());H=json.loads(a.heldouts.read_text());assert hashlib.sha256(a.oracle.read_bytes()).hexdigest()=='52c21ee2d0b27160f8b6bdd8f2eead5850e6b6f532384c6887350085b18acbbd'
records=[];failures=[]
def keys(rs):return {(int(r['game_id']),int(r.get('player_id') or 0)) for r in rs}
def expected_keys(c):return {(int(k[0]),int(k[2] or 0)) for k in c['keys']}
def summary(row,c):
 assert row['games']==c['rows'],(row,c['rows'])
 for k in ['wins','losses']: assert row[k]==c[k],(k,row[k],c[k])
 for stat in ['pts','reb','ast','tov']:
  if stat+'_sum' in row:assert math.isclose(row[stat+'_sum'],c['sums'][stat],abs_tol=.001)
  if stat+'_avg' in row:assert math.isclose(row[stat+'_avg'],c['means'][stat],abs_tol=.001)
def check_body(x,b):
 c=O['cases'].get(x.get('oracle'));kind=x['kind'];s=b['sections']
 if kind=='unsafe':assert b['result_status']!='ok';return
 assert b['result_status']=='ok',(x['query'],b.get('result_reason'))
 if kind=='season_split':
  assert len(s['split_comparison'])==2
  for row in s['split_comparison']:summary(row,O['season_splits_curry_ast7'][row['bucket']])
 elif kind=='distinct_player_count':
  assert s['count']==[{'count':c['players']}]
 elif kind=='ranking':
  # Existing score-desc/date-desc order. Expectations directly from raw CSVs.
  raw=list(csv.DictReader((repo/'qa/fixtures/query_engine_sample/data/raw/player_game_stats/2025-26_regular_season.csv').open()))
  raw=[r for r in raw if r['player_name']=='Stephen Curry' and float(r['ast'])==7]
  raw=sorted(raw,key=lambda r:(float(r['pts']),r['game_date']),reverse=True)[:3]
  assert [int(r['game_id']) for r in s['finder']]==[int(r['game_id']) for r in raw]
 elif kind=='team_record':summary(s['summary'][0],c)
 elif kind=='summary' and 'summary' in s:
  summary(s['summary'][0],c);assert keys(s['game_log'])==expected_keys(c)
 else:
  rows=s.get('finder',[]);ek=expected_keys(c)
  if c['rows']<=25 or kind in ['count','player_game_count','missed_count']:
   assert keys(rows)==ek,(x['query'],len(rows),len(ek))
  else:assert len(rows)==25 and keys(rows)<=ek
  if kind in ['count','player_game_count','missed_count']:assert s['count']==[{'count':c['rows']}]

def run_case(x,http=True):
 try:
  r=execute_natural_query(x['query']);b=r.result.to_dict();check_body(x,b)
  # Equality count labels must state equality; floor and ceiling controls keep their own language.
  if 'exactly' in x['query'] and x['kind'] in ['count','player_game_count','distinct_player_count','missed_count']:
   phrase=r.metadata.get('count_phrase',r.metadata.get('answer_phrase',''))
   assert 'exactly' in phrase,phrase
  if http:
   h=TestClient(app).post('/query',json={'query':x['query']});assert h.status_code==200;hb=h.json();check_body(x,hb['result'])
  records.append({**x,'passed':True,'http':http,'route':r.route,'count':b['sections'].get('count'),'summary':b['sections'].get('summary')})
 except Exception as e:failures.append({**x,'error':repr(e)});print('FAIL',x['query'],repr(e),flush=True)

def activate(mp,root):
 mp.setenv('DATA_SOURCE','local');mp.setenv('NBATOOLS_DATA_ROOT',str(root));mp.setenv('NBATOOLS_DATA_GENERATION','legacy');reset_data_source_cache()
if a.phase in ['fixture','all']:
 with pytest.MonkeyPatch.context() as mp:
  activate(mp,repo/'qa/fixtures/query_engine_sample')
  for x in H['cases']:
   if x.get('data')!='native':run_case(x)
  for q in ['Stephen Curry averages with exactly 7 assists in 2025-26','Stephen Curry average rebounds with exactly 7 assists in 2025-26']:
   run_case({'query':q,'oracle':'fixture_curry_assists7','kind':'summary'})
  # Full count controls explicitly avoid default finder truncation.
  for clause,key in [('0+ turnovers','fixture_curry_tov0plus'),('at most 7 assists','fixture_curry_assists7_ceiling'),('under 7 assists','fixture_curry_assists7_strictceiling')]:
   run_case({'query':f'How many games did Stephen Curry have {clause} in 2025-26?','oracle':key,'kind':'count'})
  for route,kwargs,key in [
   ('player_game_finder',dict(player='Anthony Davis',stat='reb',min_value=12,max_value=12),'fixture_ad_rebounds12'),
   ('player_game_summary',dict(player='Stephen Curry',stat='ast',min_value=7,max_value=7),'fixture_curry_assists7'),
   ('player_game_finder',dict(stat='pts',min_value=27,max_value=27),'fixture_league_pts27'),
   ('game_finder',dict(team='BOS',stat='opponent_pts',min_value=102,max_value=102),'fixture_bos_opponentpts102')]:
   try:
    r=execute_structured_query(route,season='2025-26',limit=1000,**kwargs) if route.endswith('finder') else execute_structured_query(route,season='2025-26',**kwargs)
    b=r.result.to_dict();assert r.result_status=='ok'
    if route=='player_game_summary':summary(b['sections']['summary'][0],O['cases'][key]);rows=b['sections']['game_log']
    else:rows=b['sections']['finder']
    assert keys(rows)==expected_keys(O['cases'][key]);records.append({'structured':route,'oracle':key,'passed':True})
   except Exception as e:failures.append({'structured':route,'oracle':key,'error':repr(e)})
if a.phase in ['safety','all']:
 with pytest.MonkeyPatch.context() as mp:
  activate(mp,repo/'qa/fixtures/query_engine_sample')
  for clause in ['!= 31 points','<= 31 points','>= 31 points','not exactly 31 points','exactly 31+ points','points != 31','points <= 31','points >= 31','points not equal to 31']:
   run_case({'query':f'List Jayson Tatum games with {clause} in 2025-26','kind':'unsafe'})
  for q in ['Celtics record when opponents do not score exactly 102 points in 2025-26','List Stephen Curry games when his team does not score exactly 102 points in 2025-26','List Stephen Curry games with exactly 102+ team points in 2025-26']:
   run_case({'query':q,'kind':'unsafe'})
if a.phase in ['native','all']:
 from tests.cloud_poeltl_full_season_real_data import build_qualified_stage
 with pytest.MonkeyPatch.context() as mp:
  root,_,_=build_qualified_stage(output/'native',mp);activate(mp,root)
  for x in H['cases']:
   if x.get('data')=='native':run_case(x)
  run_case({'query':'Stephen Curry average rebounds with exactly 8 assists in 2022-23','oracle':'nba_curry_ast8','kind':'summary'})
  run_case({'query':'List Kevon Looney games with exactly 7 rebounds and exactly 113 team points in 2022-23','oracle':'nba_looney_reb7_teampts113','kind':'finder'})
  run_case({'query':'How many player games with exactly 27 points in 2022-23?','oracle':'nba_league_pts27','kind':'player_game_count'})
  try:
   probe=output/'missing-equality-participation';shutil.copytree(root,probe)
   path=probe/'data/raw/player_game_availability/2022-23_regular_season.csv'
   import pandas as pd
   d=pd.read_csv(path);d.loc[~(d.player_id.eq(1627751)&d.game_id.eq(22200420))].to_csv(path,index=False)
   activate(mp,probe);r=execute_natural_query('How many games did Jakob Poeltl miss in 2022-23 with exactly 112 team points?')
   c=r.result.metadata['membership_coverage'];assert r.result_status=='no_result' and r.result_reason=='no_data' and c['missed_games'] is None and sum(x['unknown'] for x in c['by_team'])==1
   records.append({'control':'qualified exact-bound DNP observation missing: unknown retained, total withheld','passed':True})
  except Exception as e:failures.append({'control':'qualified exact-bound missing observation','error':repr(e)})
result={'checker':'/root/poeltl_source_checker; independent Codex session, exact backend model not exposed','revision':subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip(),'oracle_sha256':hashlib.sha256(a.oracle.read_bytes()).hexdigest(),'phase':a.phase,'checks':records,'failures':failures,'skipped':0,'production_writes':0}
(output/'receipt.json').write_text(json.dumps(result,indent=2,default=str)+'\n');print(json.dumps({'phase':a.phase,'passed':len(records),'failures':failures},indent=2),flush=True)
sys.exit(bool(failures))
