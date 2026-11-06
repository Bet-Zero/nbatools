"""Independent frozen-candidate consumer checks; raw oracle predates author candidate."""
import argparse, hashlib, json, os, pathlib, shutil, sys, tempfile
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from nbatools.api import app
from nbatools.data_source import reset_data_source_cache
from nbatools.query_service import execute_natural_query, execute_structured_query
from tests.cloud_poeltl_full_season_real_data import build_qualified_stage
REPO=pathlib.Path.cwd()
SCRIPT=pathlib.Path(__file__).resolve()
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--oracle',type=pathlib.Path,default=SCRIPT.parent/'independent-source-oracle.json')
parser.add_argument('--output',type=pathlib.Path,default=SCRIPT.parent/'consumer-replay')
parser.add_argument('--stage',type=pathlib.Path,help='Optional pristine prebuilt qualified stage')
args=parser.parse_args()
SCRATCH=args.output.resolve()
SCRATCH.mkdir(parents=True,exist_ok=True)
O=json.loads(args.oracle.read_text())
assert hashlib.sha256(args.oracle.read_bytes()).hexdigest()=='c83efdbb4543a5c15b3861da065c7cae4ec161b35c299e1255722754eea1e43f'
rows=O['eligible_games']
receipts=[]
def ids(seq):return {(int(x['game_id']),x['team_abbr']) for x in seq}
def expected(pred):
 selected=[r for r in rows if pred(r)]
 return ({(int(r['game_id']),r['team']) for r in selected}, {(int(r['game_id']),r['team']) for r in selected if r['status']=='played'}, {(int(r['game_id']),r['team']) for r in selected if r['status']=='explicit_dnp'})
def coverage_check(c,pop,played,missed):
 assert c['complete'] and c['missed_games']==len(missed) and not c['unknown_membership_dates'],c
 assert ids([r for r in c['games'] if r['membership_state']=='member'])==pop
 assert ids([r for r in c['games'] if r['participation_state']=='played'])==played
 assert ids([r for r in c['games'] if r['participation_state']=='did_not_play'])==missed
 assert sum(x['eligible_games'] for x in c['by_team'])==len(pop)
 assert sum(x['unknown'] for x in c['by_team'])==0
with pytest.MonkeyPatch.context() as mp:
 if args.stage:
  root=args.stage.resolve()
  teams=pd.read_csv(root/'data/raw/team_game_stats/2022-23_regular_season.csv')
  players=pd.read_csv(root/'data/raw/player_game_stats/2022-23_regular_season.csv')
 else:
  root,teams,players=build_qualified_stage(SCRATCH/'stage',mp)
 mp.setenv('DATA_SOURCE','local');mp.setenv('NBATOOLS_DATA_ROOT',str(root));mp.setenv('NBATOOLS_DATA_GENERATION','legacy');reset_data_source_cache()
 client=TestClient(app)
 cases=[
 ('',{},lambda r:True),
 ('with 113+ team points',{'stat':'pts','min_value':113},lambda r:r['pts']>=113),
 ('with 113+ team points at home',{'stat':'pts','min_value':113,'home_only':True},lambda r:r['pts']>=113 and ' vs. ' in r['matchup']),
 ('with at most 99 team points',{'stat':'pts','max_value':99},lambda r:r['pts']<=99),
 ('on the road with under 110 team points',{'stat':'pts','max_value':109.9999,'away_only':True},lambda r:r['pts']<110 and ' @ ' in r['matchup']),
 ('from November 1 to November 30, 2022',{'start_date':'2022-11-01','end_date':'2022-11-30'},lambda r:r['date'].startswith('2022-11')),
 ('against the Suns',{'opponent':'PHX'},lambda r:r['matchup'].endswith('PHX')),
 ('for the Raptors',{'team':'TOR'},lambda r:r['team']=='TOR'),
 ]
 for clause,kwargs,pred in cases:
  pop,played,missed=expected(pred)
  q=f'How many games did Jakob Poeltl miss in 2022-23 {clause}?'
  ans=execute_natural_query(q); assert ans.result_status=='ok',(q,ans.to_dict())
  body=ans.result.to_dict(); assert ids(body['sections'].get('finder',[]))==missed,(q,body)
  assert body['sections']['count']==[{'count':len(missed)}]
  coverage_check(body['metadata']['membership_coverage'],pop,played,missed)
  direct=execute_structured_query('game_finder',season='2022-23',membership_player='Jakob Poeltl',limit=1000,**kwargs)
  db=direct.result.to_dict();assert ids(db['sections'].get('finder',[]))==missed
  coverage_check(db['metadata']['membership_coverage'],pop,played,missed)
  resp=client.post('/query',json={'query':q}); assert resp.status_code==200
  hb=resp.json();assert hb['result_status']=='ok' and hb['result']['sections']['count']==[{'count':len(missed)}]
  assert ids(hb['result']['sections'].get('finder',[]))==missed
  coverage_check(hb['result']['metadata']['membership_coverage'],pop,played,missed)
  receipts.append({'query':q,'eligible':len(pop),'played':len(played),'missed':len(missed),'ids':sorted(missed),'all_three_consumers':'passed'})
 # Different entity with all exact observations: no manufacture of a missing-row absence.
 looney=players.loc[players.player_id.eq(1626172)];gsw=teams.loc[teams.team_abbr.eq('GSW')]
 assert len(looney)==len(gsw)==82 and set(looney.game_id)==set(gsw.game_id)
 alt=execute_natural_query('How many games did Kevon Looney miss in 2022-23?')
 assert alt.result_status=='ok' and alt.result.to_dict()['sections']['count']==[{'count':0}]
 receipts.append({'control':'independent raw-row Looney/GSW all82appearances,0missed','passed':True})
 # Exact calendar semantics retain the uncertified transaction day.
 for day,club,state in [('2023-02-08',1610612759,'member'),('2023-02-09',None,'unknown'),('2023-02-10',1610612761,'member')]:
  a=execute_structured_query('player_membership',player_id=1627751,date=day,season='2022-23')
  s=a.result.to_dict()['sections']['summary'][0];assert s['membership_state']==state,(day,s)
  if club is not None: assert int(s['member_team_id'])==club
 receipts.append({'control':'exact finite membership Feb8SAS/Feb9unknown/Feb10TOR','passed':True})
 # Every damage probe gets a new isolated path before its first read; old readers
 # correctly keep their pinned immutable inputs and process caches.
 for damage in ['missing_participation','membership_gap','source_hash']:
  probe=SCRATCH/('probe-'+damage);shutil.copytree(root,probe)
  if damage=='missing_participation':
   path=probe/'data/raw/player_game_availability/2022-23_regular_season.csv'
   av=pd.read_csv(path);av.loc[~(av.player_id.eq(1627751)&av.game_id.eq(22200375))].to_csv(path,index=False)
  elif damage=='membership_gap':
   path=probe/'data/raw/player_team_membership/2022-23.csv';l=pd.read_csv(path)
   l.loc[l.team_id.eq(1610612761),'start_date']='2023-02-11';l.to_csv(path,index=False)
  else:
   path=probe/'data/raw/player_team_membership_sources/95ba9440784d6ffa3666e8d9f318561dd6a3d059b262dc4ce1ea6958262e3ed2.source'
   path.write_bytes(b'checker-only-corruption')
  mp.setenv('NBATOOLS_DATA_ROOT',str(probe));reset_data_source_cache()
  a=execute_natural_query('How many games did Jakob Poeltl miss in 2022-23?')
  assert a.result_status!='ok' and 'count' not in a.result.to_dict()['sections'],(damage,a.to_dict())
  if damage!='source_hash':
   c=a.result.metadata['membership_coverage']
   assert a.result_status=='no_result' and a.result_reason=='no_data' and c['missed_games'] is None and not c['complete']
   if damage=='missing_participation':
    assert sum(t['eligible_games'] for t in c['by_team'])==81 and sum(t['unknown'] for t in c['by_team'])==1
    assert any(r['game_id']==22200375 and r['participation_state']=='unknown' for r in c['games'])
   else: assert '2023-02-10' in c['unknown_membership_dates']
  receipts.append({'control':damage,'passed':True})
 reset_data_source_cache()
(SCRATCH/'consumer-receipt.json').write_text(json.dumps({'reviewed_revision':'4f0b010e62400818a663acca6a628948065093cf','checker':'/root/poeltl_source_checker, independent Codex session; backend model unspecified','oracle_sha256':'c83efdbb4543a5c15b3861da065c7cae4ec161b35c299e1255722754eea1e43f','checks':receipts,'failures':0,'skips':0,'production_writes':0},indent=2)+'\n')
print(json.dumps(receipts,indent=2))
