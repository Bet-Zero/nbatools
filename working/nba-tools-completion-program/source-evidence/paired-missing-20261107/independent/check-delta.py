import argparse,pathlib,sys,os,json
P=pathlib.Path(__file__).resolve().parent;ap=argparse.ArgumentParser();ap.add_argument('--repo',type=pathlib.Path,required=True);ap.add_argument('--output',type=pathlib.Path,required=True);a=ap.parse_args();R=a.repo.resolve();sys.path[:0]=[str(R/'src'),str(R)];os.environ.update(DATA_SOURCE='local',NBATOOLS_DATA_GENERATION='legacy',NBATOOLS_DATA_ROOT=str(P/'qualified-core'))
from nbatools.query_service import execute_natural_query,execute_structured_query
from nbatools.data_source import reset_data_source_cache
from fastapi.testclient import TestClient
from nbatools.api import app
records=[];fail=[];calls=0
for suffix in ['missing','out','not playing']:
 q=f'Celtics record with Tatum and Brown {suffix} and at least 111 points in 2025-26'
 try:r=execute_natural_query(q);calls+=1;s=r.to_dict()['sections']['summary'][0];assert r.result_status=='ok'and(s['games'],s['wins'],s['losses'])==(5,5,0),r.to_dict();records.append({'positive_suffix':suffix,'games':5,'passed':True})
 except Exception as e:fail.append({'query':q,'error':repr(e)})
for tail in ['and LeBron James','and Missing Player','and Missing Player playing','and on the bench']:
 q='Celtics record with Tatum and Brown missing and at least 111 points '+tail+' in 2025-26'
 try:r=execute_natural_query(q);calls+=1;assert r.result_status!='ok'and 'primary_count'not in r.metadata,r.to_dict();records.append({'extra_tail':tail,'passed':True,'reason':r.result_reason})
 except Exception as e:fail.append({'query':q,'error':repr(e)})
os.environ['NBATOOLS_DATA_ROOT']=str(P/'s4-results-cdbf55/stage');reset_data_source_cache()
kw=dict(team='BOS',split='season',start_season='2023-24',end_season='2025-26',split_seasons=['2023-24','2025-26'],opponent='LAL',with_player='Jayson Tatum')
try:
 r=execute_structured_query('team_split_summary',**kw);h=TestClient(app).post('/structured-query',json={'route':'team_split_summary','kwargs':kw});calls+=2;assert h.status_code==200
 for d in [r.to_dict(),h.json()['result']]:
  labels={v['label']:v['value']for v in d['metadata']['applied_filters']};assert labels['Seasons']=='2023-24, 2025-26'and'Season range'not in labels;assert d['metadata']['season_list']==['2023-24','2025-26']
 records.append({'structured_explicit_nonadjacent_labels':True,'passed':True})
except Exception as e:fail.append({'S4_structured_labels':repr(e)})
for extra in [{'invented_filter':True},{'with_player':['Jayson Tatum']},{'without_player':17}]:
 h=TestClient(app).post('/structured-query',json={'route':'team_split_summary','kwargs':{**kw,**extra}});calls+=1
 try:assert h.status_code==422,h.json();records.append({'HTTP_type_unknown_field_guard':extra,'passed':True})
 except Exception as e:fail.append({'HTTP_guard':extra,'error':repr(e)})
res={'revision':__import__('subprocess').check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip(),'checks':records,'failures':fail,'calls':calls};a.output.write_text(json.dumps(res,indent=2,default=str)+'\n');print(json.dumps({'passed':len(records),'calls':calls,'failures':fail},indent=2));sys.exit(bool(fail))
