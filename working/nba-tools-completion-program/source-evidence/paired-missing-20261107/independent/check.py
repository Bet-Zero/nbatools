"""Independent paired-missing consumers against frozen original-row expectations."""
import argparse,contextlib,hashlib,json,os,pathlib,shutil,subprocess,sys
P=pathlib.Path(__file__).resolve().parent;ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--repo',type=pathlib.Path,required=True);ap.add_argument('--evidence',type=pathlib.Path,default=P);ap.add_argument('--output',type=pathlib.Path,required=True);a=ap.parse_args();R=a.repo.resolve();P=a.evidence.resolve();O=a.output.resolve();O.mkdir(parents=True,exist_ok=True);sys.path[:0]=[str(R/'src'),str(R)]
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from nbatools.api import app
from nbatools.commands import _participation_observations as observations,team_record,player_game_summary
from nbatools.data_source import reset_data_source_cache
from nbatools.query_service import execute_natural_query,execute_structured_query
assert hashlib.sha256((P/'oracle.json').read_bytes()).hexdigest()=='c90bee16e62aa026f66a70e7351fd13e869284aeba3a32bc3defe116f75fc471';assert hashlib.sha256((P/'heldouts.json').read_bytes()).hexdigest()=='96f70b93939d2157e8c3a31d6a550c5e3cfc50a1dd35e85eb94cb99e0cbb44f8'
F=json.loads((P/'oracle.json').read_text())['cases'];H=json.loads((P/'heldouts.json').read_text());records=[];failures=[];calls=0
@contextlib.contextmanager
def capture(mp):
 frames=[]
 for module,attr in [(team_record,'_compute_record'),(player_game_summary,'_build_game_log_section')]:
  original=getattr(module,attr)
  def wrap(frame,*args,_old=original,**kwargs):frames.append(frame.copy());return _old(frame,*args,**kwargs)
  mp.setattr(module,attr,wrap)
 yield frames

def activate(mp,kind,root=None):
 mp.setenv('DATA_SOURCE','local');mp.setenv('NBATOOLS_DATA_ROOT',str(root or P/('controlled'if kind=='controlled'else'qualified-core')));mp.setenv('NBATOOLS_DATA_GENERATION','legacy');reset_data_source_cache()
 if kind=='controlled':
  frame=pd.read_csv(P/'controlled-observations.csv')
  mp.setattr(observations,'load_observations',lambda seasons,season_type:frame.loc[frame.season.isin(seasons)&frame.season_type.eq(season_type)].copy())

def verify(c,body,meta,seen):
 e=F[c['oracle']]
 if 'missing' in c.get('query','').lower():
  names=['Jayson Tatum','Jaylen Brown'] if c['oracle'].startswith('bos_') else ['Anthony Davis','Austin Reaves'] if c['oracle'].startswith('lal_') else ['Bam Adebayo','Tyler Herro']
  assert not meta.get('with_player') and all(n in str(meta.get('without_player','')) for n in names),(c,'negative_actor_metadata',meta)
 if c['shape']=='covered_no_match':assert body['result_status']=='no_result'and body['result_reason']=='no_match',(c,body);return
 assert body['result_status']=='ok',(c,body,meta)
 if c['shape']=='count':assert body['sections']['count']==[{'count':e['games']}],(c,body);return
 s=body['sections']['summary'][0]
 assert(s['games'],s['wins'],s['losses'])==(e['games'],e['wins'],e['losses']),(c,s)
 for stat,mean in e['means'].items():assert abs(s[stat+'_avg']-mean)<0.0011,(c,stat,s[stat+'_avg'],mean)
 assert seen,(c,'noexecutedframe')
 frame=seen[-1];cols=['game_id','team_id']+(['player_id']if len(e['keys'][0])==3 else[]);assert set(map(tuple,frame[cols].astype(int).to_numpy()))==set(map(tuple,e['keys'])),(c,'completekeys')
 for stat,total in e['sums'].items():assert abs(frame[stat].sum()-total)<1e-8,(c,'sum',stat)

with pytest.MonkeyPatch.context()as mp:
 for kind in ['qualified','controlled']:
  with mp.context()as env:
   activate(env,kind)
   for c in H['cases']:
    if c['data']!=kind:continue
    try:
     with env.context()as cap,capture(cap)as seen:r=execute_natural_query(c['query']);calls+=1;verify(c,r.result.to_dict(),r.metadata,seen)
     with env.context()as cap,capture(cap)as seen:h=TestClient(app).post('/query',json={'query':c['query']});calls+=1;assert h.status_code==200;d=h.json();verify(c,d['result'],d['result'].get('metadata',{}),seen)
     records.append({**c,'passed':True,'status':r.result_status,'reason':r.result_reason,'filters':r.metadata.get('applied_filters'),'answer':r.metadata.get('answer_phrase')or r.metadata.get('count_phrase')})
    except Exception as e:failures.append({**c,'error':repr(e)});print('FAIL',c['query'],repr(e),flush=True)
   for c in H['containment']:
    if c['data']!=kind:continue
    try:
     r=execute_natural_query(c['query']);calls+=1;assert r.result_status!='ok'and'primary_count'not in r.metadata,(c,r.to_dict());records.append({**c,'contained':True,'implemented_positive':False,'status':r.result_status,'reason':r.result_reason})
    except Exception as e:failures.append({**c,'error':repr(e)});print('FAILcontrol',c['query'],repr(e),flush=True)
 # Structured and HTTP parity on the same original-qualified pair intersection.
 for name,kw in [('bos_pair',dict(team='BOS',season='2025-26',without_player='Jayson Tatum and Jaylen Brown')),('lal_pair_zero',dict(team='LAL',season='2023-24',without_player='Anthony Davis and Austin Reaves')),('bos_pair_home',dict(team='BOS',season='2025-26',without_player='Jayson Tatum and Jaylen Brown',home_only=True))]:
  with mp.context()as env:
   activate(env,'qualified')
   try:
    c={'oracle':name,'shape':'covered_no_match'if not F[name]['games']else'record'}
    with env.context()as cap,capture(cap)as seen:r=execute_structured_query('team_record',**kw);calls+=1;verify(c,r.to_dict(),r.metadata,seen)
    with env.context()as cap,capture(cap)as seen:h=TestClient(app).post('/structured-query',json={'route':'team_record','kwargs':kw});calls+=1;assert h.status_code==200;d=h.json();verify(c,d['result'],d['result'].get('metadata',{}),seen)
    records.append({'structured':kw,'oracle':name,'passed':True})
   except Exception as e:failures.append({'structured':kw,'error':repr(e)});print('FAILstructured',repr(e),flush=True)
 # Each mutation precedes the first read of a fresh copy; no tested dataset is changed in place.
 for damage in ['missing_DNP','unknown_DNP','wrong_DNP_team','wrong_DNP_date','false_first_cannot_hide_unknown_second']:
  root=O/damage;shutil.copytree(P/'qualified-core',root);path=root/'data/raw/player_game_availability/2025-26_regular_season.csv';d=pd.read_csv(path);bos=d.team_id.eq(1610612738)
  if damage=='false_first_cannot_hide_unknown_second':
   # At a canonical Tatum positive game, Brown's independent DNP/unknown still requires coverage.
   players=pd.read_csv(root/'data/raw/player_game_stats/2025-26_regular_season.csv');tg=set(players.loc[players.player_id.eq(1628369),'game_id']);bg=set(d.loc[bos&d.player_id.eq(1627759)&d.participation_state.eq('did_not_play'),'game_id']);gid=sorted(tg&bg)[0];mask=bos&d.game_id.eq(gid)&d.player_id.eq(1627759)
  else:gid=F['bos_pair']['keys'][0][0];mask=bos&d.game_id.eq(gid)&d.player_id.eq(1627759)
  assert mask.sum()==1
  if damage in ['missing_DNP','false_first_cannot_hide_unknown_second']:d.loc[~mask].to_csv(path,index=False)
  elif damage=='unknown_DNP':d.loc[mask,'participation_state']='unknown';d.to_csv(path,index=False)
  elif damage=='wrong_DNP_team':d.loc[mask,'team_id']=1610612747;d.to_csv(path,index=False)
  else:d.loc[mask,'game_date']='2026-09-01';d.to_csv(path,index=False)
  with mp.context()as env:
   activate(env,'qualified',root)
   try:
    r=execute_natural_query('Celtics record with Tatum and Brown missing in 2025-26');calls+=1;assert r.result_status!='ok'and r.result_reason!='no_match'and'primary_count'not in r.metadata,(damage,r.to_dict());records.append({'damage':damage,'passed':True,'status':r.result_status,'reason':r.result_reason})
   except Exception as e:failures.append({'damage':damage,'error':repr(e)});print('FAILdamage',damage,repr(e),flush=True)
result={'reviewed_revision':subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip(),'checker':'Separate Codex session /root/poeltl_source_checker; exact backend model ID unavailable','frozen_oracle_sha256':hashlib.sha256((P/'oracle.json').read_bytes()).hexdigest(),'checks':records,'failures':failures,'query_invocations':calls,'production_writes':0,'source_downloads':0};(O/'receipt.json').write_text(json.dumps(result,indent=2,default=str)+'\n');print(json.dumps({'passed':len(records),'query_invocations':calls,'failures':failures},indent=2));sys.exit(bool(failures))
