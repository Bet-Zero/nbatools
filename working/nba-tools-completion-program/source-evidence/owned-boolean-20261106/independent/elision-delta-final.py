import pathlib,sys,json,os
P=pathlib.Path(__file__).resolve().parent;R=P/'final';sys.path[:0]=[str(R/'src'),str(R)]
from nbatools.commands.query_boolean_parser import parse_condition_text,condition_tree_leaves
from nbatools.query_service import execute_natural_query
from nbatools.data_source import reset_data_source_cache
out=[];fail=[]
positive={
 '(team had at least 100 points) or at least 25 assists':['team_pts','ast'],
 '(opponents had at least 100 points) or at least 25 assists':['opponent_pts','ast'],
 '(exactly 100 team points or exactly 100 opponent points) and at least 20 points':['team_pts','opponent_pts','pts'],
 'over 20 points or (team had at least 100 points and exactly 25 team assists)':['pts','team_pts','team_ast'],
 'over 20 points or (opponents had at least 100 points and exactly 25 opponent assists)':['pts','opponent_pts','opponent_ast']}
negative=['over 20 points or team had at least 100 points and at least 25 assists','over 20 points or opponents had at least 100 points and at least 25 assists','over 20 points or allowed at most 100 points and at most 20 assists','over 20 points or held opponents under 100 points and under 20 assists','over 20 points or limited opponents to under 100 points and under 20 assists','over 20 points or opponents stayed under 100 points and under 20 assists','over 20 points or kept the other team below 100 points and under 20 assists']
for expr,expected in positive.items():
 try:
  got=[n.stat for n in condition_tree_leaves(parse_condition_text(expr))];assert got==expected,(expr,got);out.append({'positive':expr,'leaves':got})
 except Exception as e:fail.append({'expression':expr,'error':repr(e)})
for expr in negative:
 try:parse_condition_text(expr);fail.append({'expression':expr,'error':'accepted_elided_owner'})
 except ValueError:out.append({'contained_unfinished':expr})
os.environ.update(DATA_SOURCE='local',NBATOOLS_DATA_ROOT=str(P/'native-3f3f/native/native-stage'),NBATOOLS_DATA_GENERATION='legacy');reset_data_source_cache()
q='How many distinct players had (over 100 points or team had at least 125 points and at least 30 assists) in 2022-23?';r=execute_natural_query(q)
try:assert r.result_status!='ok'and 'primary_count'not in r.metadata,r.to_dict();out.append({'wrong_zero_repaired_to_contained_unfinished':q,'status':r.result_status,'reason':r.result_reason})
except Exception as e:fail.append({'wrong_zero':repr(e)})
os.environ.update(NBATOOLS_DATA_ROOT=str(P/'prior-replay/controlled'));reset_data_source_cache()
for q,expected in [('Count distinct players who recorded (over 20 points or the team had exactly 100 points) during 2025-26',3),('How many player games had (over 20 points or the other team scored exactly 100 points) during 2025-26?',5)]:
 r=execute_natural_query(q)
 try:assert r.result_status=='ok'and r.metadata['primary_count']==expected,r.to_dict();out.append({'fresh_related_wording':q,'count':expected,'filters':r.metadata.get('applied_filters')})
 except Exception as e:fail.append({'query':q,'error':repr(e)})
result={'revision':'736b3d0df63d86a06983fd2d765a1a000e063d8d','checks':out,'failures':fail};(P/'elision-delta-736b.json').write_text(json.dumps(result,indent=2,default=str)+'\n');print(json.dumps({'passed':len(out),'failures':fail},indent=2));sys.exit(bool(fail))
