"""Independent equality guard/margin/label delta checks after original findings."""
import argparse,csv,json,os,pathlib,subprocess,sys
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);args=p.parse_args();repo=args.repo.resolve();args.output.mkdir(parents=True,exist_ok=True)
sys.path[:0]=[str(repo/'src'),str(repo)];os.environ.update(DATA_SOURCE='local',NBATOOLS_DATA_ROOT=str(repo/'qa/fixtures/query_engine_sample'),NBATOOLS_DATA_GENERATION='legacy')
from fastapi.testclient import TestClient
from nbatools.api import app
from nbatools.query_service import execute_natural_query
unsafe=[
 'List Jayson Tatum games with points equal to 31 or more in 2025-26',
 'List Jayson Tatum games with points = 31 or fewer in 2025-26',
 'Celtics record when opponents never once scored exactly 102 points in 2025-26',
 'List Stephen Curry games when his team did not once score exactly 102 points in 2025-26',
 'List Stephen Curry games with exactly 102 team points or more in 2025-26',
 'Celtics record with exactly 102 opponent points or more in 2025-26',
]
records=[];failures=[]
for q in unsafe:
 try:
  a=execute_natural_query(q);assert a.result_status!='ok',(a.metadata,a.result.to_dict()['sections'])
  h=TestClient(app).post('/query',json={'query':q});assert h.status_code==200 and h.json()['result_status']!='ok'
  records.append({'query':q,'passed':True,'status':a.result_status})
 except Exception as e:failures.append({'query':q,'error':repr(e)})
raw=list(csv.DictReader((repo/'qa/fixtures/query_engine_sample/data/raw/player_game_stats/2025-26_regular_season.csv').open()))
for q,pred in [
 ('How many Stephen Curry games with exactly 7 assists and 0 turnovers in 2025-26?',lambda r:r['player_name']=='Stephen Curry' and float(r['ast'])==7 and float(r['tov'])==0),
 ('How many Stephen Curry games with no turnovers and exactly 7 assists in 2025-26?',lambda r:r['player_name']=='Stephen Curry' and float(r['ast'])==7 and float(r['tov'])==0),
 ('How many Stephen Curry games with assists = 7 in 2025-26?',lambda r:r['player_name']=='Stephen Curry' and float(r['ast'])==7),
]:
 try:
  expected={(int(r['game_id']),int(r['player_id'])) for r in raw if pred(r)}
  a=execute_natural_query(q);s=a.result.to_dict()['sections'];assert a.result_status=='ok' and s['count']==[{'count':len(expected)}]
  if 'finder' in s: assert {(int(r['game_id']),int(r['player_id'])) for r in s['finder']}==expected
  assert 'games' in a.metadata.get('count_phrase',''),a.metadata
  h=TestClient(app).post('/query',json={'query':q});assert h.status_code==200 and h.json()['result']['sections']['count']==[{'count':len(expected)}]
  records.append({'query':q,'passed':True,'expected_count':len(expected),'game_ids':sorted(g for g,_ in expected)})
 except Exception as e:failures.append({'query':q,'error':repr(e)})
teams=list(csv.DictReader((repo/'qa/fixtures/query_engine_sample/data/raw/team_game_stats/2025-26_regular_season.csv').open()));tm={(r['game_id'],r['team_id']):r for r in teams}
for q,expected,phrase in [
 ('How many times did the Lakers win by 1 in 2025-26?',{int(r['game_id']) for r in teams if r['team_abbr']=='LAL' and r['wl']=='W' and float(r['pts'])-float(tm[(r['game_id'],r['opponent_team_id'])]['pts'])==1},'by exactly 1 point'),
 ('How many Celtics games allowed exactly 102 points in 2025-26?',{int(r['game_id']) for r in teams if r['team_abbr']=='BOS' and float(tm[(r['game_id'],r['opponent_team_id'])]['pts'])==102},'allowed exactly 102 points'),
]:
 try:
  a=execute_natural_query(q);s=a.result.to_dict()['sections'];assert a.result_status=='ok' and s['count']==[{'count':len(expected)}]
  assert {int(r['game_id']) for r in s['finder']}==expected
  assert phrase in a.metadata['count_phrase'],a.metadata['count_phrase']
  h=TestClient(app).post('/query',json={'query':q});assert h.status_code==200 and h.json()['result']['sections']['count']==[{'count':len(expected)}]
  records.append({'query':q,'passed':True,'expected_count':len(expected),'game_ids':sorted(expected),'count_phrase':a.metadata['count_phrase']})
 except Exception as e:failures.append({'query':q,'error':repr(e)})
# Legitimate defensive equality must use opponent scores under each existing governor.
for clause in ['holding opponents to exactly 102 points','held opponents to exactly 102','limiting opponents to exactly 102 points']:
 q=f'Celtics record when {clause} in 2025-26'
 try:
  selected=[r for r in teams if r['team_abbr']=='BOS' and float(tm[(r['game_id'],r['opponent_team_id'])]['pts'])==102]
  a=execute_natural_query(q);row=a.result.to_dict()['sections']['summary'][0]
  assert a.result_status=='ok' and row['games']==len(selected)
  assert row['wins']==sum(r['wl']=='W' for r in selected)
  assert row['pts_avg']==sum(float(r['pts']) for r in selected)/len(selected)
  h=TestClient(app).post('/query',json={'query':q});assert h.status_code==200 and h.json()['result']['sections']['summary'][0]['games']==len(selected)
  records.append({'query':q,'passed':True,'game_ids':sorted(int(r['game_id']) for r in selected),'summary':row})
 except Exception as e:failures.append({'query':q,'error':repr(e)})
result={'reviewed_revision':subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip(),'checker':'/root/poeltl_source_checker; separate Codex session, exact backend model not exposed','records':records,'failures':failures,'skipped':0,'production_writes':0}
(args.output/'receipt.json').write_text(json.dumps(result,indent=2,default=str)+'\n');print(json.dumps(result,indent=2,default=str));sys.exit(bool(failures))
