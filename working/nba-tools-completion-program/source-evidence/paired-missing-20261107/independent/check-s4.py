"""Finite S4 team integration on retained original rows; Brown2023 requires pinned base."""
import argparse,csv,io,json,os,pathlib,shutil,sys,zipfile,hashlib
P=pathlib.Path(__file__).resolve().parent;ap=argparse.ArgumentParser();ap.add_argument('--repo',type=pathlib.Path,required=True);ap.add_argument('--output',type=pathlib.Path,required=True);a=ap.parse_args();R=a.repo.resolve();O=a.output.resolve();O.mkdir(parents=True,exist_ok=True);sys.path[:0]=[str(R/'src'),str(R)]
import pandas as pd
from fastapi.testclient import TestClient
from nbatools.api import app
from nbatools.query_service import execute_natural_query,execute_structured_query
from nbatools.data_source import reset_data_source_cache
oracle=json.loads((P/'oracle.json').read_text())['s4'];archive=R/'working/nba-tools-completion-program/source-evidence/k08-direct-dependencies/input-audit-source.zip';assert hashlib.sha256(archive.read_bytes()).hexdigest()=='33f4a6d9a013da81f3f4c3c25f837c44cd7248de42f425b92e01af68b71cb67a'
root=O/'stage';shutil.copytree(P/'qualified-core',root)
with zipfile.ZipFile(archive)as z:
 d=pd.read_csv(io.BytesIO(z.read('acquired_data/direct-k08-participation-coverage/2023-24-1610612747-reciprocal-team164.csv')));add=d.loc[d.team_id.eq(1610612738)];assert set(add.game_id)=={22300403,22300684}
f=root/'data/raw/team_game_stats/2023-24_regular_season.csv';pd.concat([pd.read_csv(f),add]).to_csv(f,index=False)
records=[];failures=[];calls=0
def activate(where):os.environ.update(DATA_SOURCE='local',NBATOOLS_DATA_ROOT=str(where),NBATOOLS_DATA_GENERATION='legacy');reset_data_source_cache()
activate(root)
for relation,selected,empty in [('with','2023-24','2025-26'),('without','2025-26','2023-24')]:
 q=f'Celtics record vs Lakers {relation} Jayson Tatum in 2023-24 and 2025-26';kw=dict(team='BOS',split='season',start_season='2023-24',end_season='2025-26',split_seasons=['2023-24','2025-26'],opponent='LAL',**{relation+'_player':'Jayson Tatum'})
 try:
  natural=execute_natural_query(q);structured=execute_structured_query('team_split_summary',**kw);http=TestClient(app).post('/query',json={'query':q});api=TestClient(app).post('/structured-query',json={'route':'team_split_summary','kwargs':kw});calls+=4;assert http.status_code==api.status_code==200
  e=oracle[selected]['team']
  for d in [natural.to_dict(),structured.to_dict(),http.json()['result'],api.json()['result']]:
   assert d['result_status']=='ok',d;sec=d['sections'];assert sec['summary'][0]['games_total']==2;rows=sec['split_comparison'];assert len(rows)==1 and rows[0]['bucket']==selected;row=rows[0];assert(row['games'],row['wins'],row['losses'])==(2,e['wins'],e['losses']);assert all(abs(row[s+'_avg']-e['means'][s])<0.0011 for s in ['pts','reb','ast']);assert 'no games in '+empty in d['caveats']
  labels={r['label']:r['value']for r in natural.metadata['applied_filters']};assert labels[relation.capitalize()+' player']=='Jayson Tatum'and labels['Opponent']=='LAL'and labels['Seasons']=='2023-24, 2025-26';records.append({'relation':relation,'selected':selected,'empty':empty,'passed':True,'expected_raw':e,'natural':natural.to_dict(),'http':http.json()})
 except Exception as ex:failures.append({'query':q,'error':repr(ex)});print('FAIL',q,repr(ex),flush=True)
# A requested unknown in2025 cannot disappear as an empty bucket or leave only2023 results.
for state in ['missing','unknown']:
 target=O/state;shutil.copytree(root,target);f=target/'data/raw/player_game_availability/2025-26_regular_season.csv';d=pd.read_csv(f);mask=d.game_id.eq(22500338)&d.player_id.eq(1628369);assert mask.sum()==1
 if state=='missing':d=d.loc[~mask]
 else:d.loc[mask,'participation_state']='unknown'
 d.to_csv(f,index=False);activate(target)
 try:
  r=execute_natural_query('Celtics record vs Lakers without Tatum in 2023-24 and 2025-26');calls+=1;assert r.result_status!='ok'and r.result_reason!='no_match'and 'primary_count'not in r.metadata,r.to_dict();records.append({'S4_requested_coverage':state,'passed':True,'status':r.result_status,'reason':r.result_reason})
 except Exception as ex:failures.append({'state':state,'error':repr(ex)});print('FAILunknown',repr(ex),flush=True)
result={'classification':'Independent finiteS4team newintegration only; Brown2023 exactraw pendingactualR2; no reacquisition','revision':__import__('subprocess').check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip(),'checks':records,'failures':failures,'calls':calls,'excluded_middle_season_file_present':(root/'data/raw/team_game_stats/2024-25_regular_season.csv').exists()};(O/'receipt.json').write_text(json.dumps(result,indent=2,default=str)+'\n');print(json.dumps({'passed':len(records),'calls':calls,'failures':failures},indent=2));sys.exit(bool(failures))
