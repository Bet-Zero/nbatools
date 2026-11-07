"""Compare an independently derived original-body oracle to a frozen candidate."""
import csv,hashlib,io,json,math,sys,zipfile
from pathlib import Path
ROOT=Path('/workspace/nbatools');OUT=ROOT/'work/current123-period-independent'
ORACLE=OUT/'raw-oracle.json'; d=json.loads(ORACLE.read_bytes())
CAPTURE=Path('/tmp/codex-remote-attachments/01a1b46e-3c65-77e4-8e3a-66c0cd0520fa/75B5E594-9B94-482B-B1C0-4E6B20C9E9EE/1-collection-3.zip')
assert hashlib.sha256(CAPTURE.read_bytes()).hexdigest()==d['input_zip_sha256']
source_percentages={}
with zipfile.ZipFile(CAPTURE) as rawzip:
 for name in rawzip.namelist():
  if not name.startswith('sources/boxscoretraditional'):continue
  tag=name.rsplit('_',1)[1][:-5];box=json.loads(rawzip.read(name))['boxScoreTraditional']
  for side in ('homeTeam','awayTeam'):
   team=box[side];tid=team['teamId'];gid=int(box['gameId'])
   for pid,stats in [(None,team['statistics']),*[(p['personId'],p['statistics']) for p in team['players']]]:
    source_percentages[(gid,tag,tid,pid)]={c:stats[f] for c,f in [('fg_pct','fieldGoalsPercentage'),('fg3_pct','threePointersPercentage'),('ft_pct','freeThrowsPercentage')]}
CANDIDATE=Path(sys.argv[1]);expected_sha=sys.argv[2]
assert hashlib.sha256(CANDIDATE.read_bytes()).hexdigest()==expected_sha
with zipfile.ZipFile(CANDIDATE) as z:
 pp=list(csv.DictReader(io.StringIO(z.read('data/raw/player_game_period_stats/2026-27_regular_season.csv').decode())))
 tt=list(csv.DictReader(io.StringIO(z.read('data/raw/team_game_period_stats/2026-27_regular_season.csv').decode())))
 manifest_raw=z.read('data/metadata/development_snapshot.json');manifest=json.loads(manifest_raw)
 for name,h in manifest['files'].items():assert hashlib.sha256(z.read(name)).hexdigest()==h
 with zipfile.ZipFile(ROOT/'working/nba-tools-completion-program/source-evidence/id18-current-required-20261107/current123-required-v3.zip') as old:
  old_pp=old.read('data/raw/player_game_period_stats/2026-27_regular_season.csv');old_tt=old.read('data/raw/team_game_period_stats/2026-27_regular_season.csv')
  assert z.read('data/raw/player_game_period_stats/2026-27_regular_season.csv').startswith(old_pp)
  assert z.read('data/raw/team_game_period_stats/2026-27_regular_season.csv').startswith(old_tt)
  unchanged=[n for n in old.namelist() if n not in ('data/metadata/development_snapshot.json','data/raw/player_game_period_stats/2026-27_regular_season.csv','data/raw/team_game_period_stats/2026-27_regular_season.csv')]
  for name in unchanged:assert old.read(name)==z.read(name),name
 def key(r,player):
  gid=int(r['game_id']);tid=int(r['team_id'])
  if 'window' in r:
   tag=r['window'];fam={'q':'quarter','h':'half','o':'overtime'}[tag[0]];value={'h1':'first','h2':'second','ot':'ot'}.get(tag,tag[1:])
  else:fam=r['period_family'];value=r['period_value'].lower()
  return (gid,fam,value,tid,*([int(r['player_id'])] if player else []))
 differences=[];numeric=0
 for source,actual,player in [(d['canonical_player_rows'],pp,True),(d['team_rows'],tt,False)]:
  e={key(r,player):r for r in source};actual=[r for r in actual if 173<=int(r['game_id'])%100000<=188];a={key(r,player):r for r in actual}
  assert len(a)==len(actual)==len(e) and a.keys()==e.keys()
  for k,r in e.items():
   # Independently recompute derived shooting ratios, including qualified no-attempt zeros.
   r.update(source_percentages.get((r['game_id'],r['window'],r['team_id'],r.get('player_id')),{'fg_pct':0,'fg3_pct':0,'ft_pct':0}))
   r['efg_pct']=(r['fgm']+.5*r['fg3m'])/r['fga'] if r['fga'] else 0
   den=2*(r['fga']+.44*r['fta']);r['ts_pct']=r['pts']/den if den else 0
   for col,v in r.items():
    if col in {'game_id','team_id','player_id','window','player_name','source_clock','clock_basis'}:continue
    numeric+=1
    if not math.isclose(float(a[k][col]),float(v),rel_tol=1e-11,abs_tol=1e-11):differences.append({'key':k,'column':col,'expected':v,'actual':a[k][col]})
  assert not differences,differences[:10]
 assert len(pp)==16783 and len(tt)==1490
 unknown=sum(not r[c].strip() for r in pp for c in ('usg_pct','tov_pct'))
 assert unknown==484
 result={'candidate_zip_sha256':expected_sha,'manifest_sha256':hashlib.sha256(manifest_raw).hexdigest(),'oracle_sha256':hashlib.sha256(ORACLE.read_bytes()).hexdigest(),'numeric_cells_compared':numeric,'numeric_differences':differences,'new_player_keys':2236,'new_team_keys':196,'total_player_rows':len(pp),'total_team_rows':len(tt),'old_period_prefix_bytes_preserved':True,'unchanged_prior_nonperiod_files':len(unchanged),'old_rate_unknowns_preserved':unknown,'new_source_basis_conflict_still_open':d['failures'],'production_writes':0,'nba_requests_executed':0,'scope':'Candidate data matches independently raw-derived expectations; game184numericaltruth remains unresolved, no publication acceptance.'}
 print(json.dumps(result,indent=2));(OUT/'candidate-comparison.json').write_text(json.dumps(result,indent=2)+'\n')
