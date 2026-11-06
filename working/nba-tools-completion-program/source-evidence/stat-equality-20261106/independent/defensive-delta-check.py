"""Independent final defensive-negation delta; immutable fixture inputs only."""
import argparse,csv,json,os,pathlib,subprocess,sys
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);args=p.parse_args();repo=args.repo.resolve();sys.path[:0]=[str(repo/'src'),str(repo)]
os.environ.update(DATA_SOURCE='local',NBATOOLS_DATA_ROOT=str(repo/'qa/fixtures/query_engine_sample'),NBATOOLS_DATA_GENERATION='legacy')
from nbatools.query_service import execute_natural_query
rows=list(csv.DictReader((repo/'qa/fixtures/query_engine_sample/data/raw/team_game_stats/2025-26_regular_season.csv').open()));bykey={(r['game_id'],r['team_id']):r for r in rows};expected=[r for r in rows if r['team_abbr']=='BOS' and float(bykey[(r['game_id'],r['opponent_team_id'])]['pts'])==102]
records=[]
for verb in ['held','limited']:
 q=f'Celtics record when they never {verb} opponents to exactly 102 points in 2025-26';a=execute_natural_query(q);assert a.result_status!='ok';records.append({'query':q,'passed':True,'result_status':a.result_status})
q='Celtics record when holding opponents to exactly 102 points in 2025-26';a=execute_natural_query(q);r=a.result.to_dict()['sections']['summary'][0]
assert a.result_status=='ok' and r['games']==len(expected) and r['wins']==sum(x['wl']=='W' for x in expected) and r['pts_avg']==sum(float(x['pts']) for x in expected)/len(expected)
records.append({'query':q,'passed':True,'summary':r})
args.output.write_text(json.dumps({'revision':subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip(),'checks':records,'failed':0,'skipped':0},indent=2)+'\n')
print('Final defensive delta:3passed,0failed,0skipped')
