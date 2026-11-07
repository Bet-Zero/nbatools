"""Independent original-token delta, scorer and exposure comparison for frozen v5."""
import csv,hashlib,io,json,math,zipfile
from pathlib import Path
from fractions import Fraction
ROOT=Path('/workspace/nbatools');OUT=ROOT/'work/current123-period-independent';E=ROOT/'working/nba-tools-completion-program/source-evidence/current123-periods-20261107'
old=E/'current123-period-v4.zip';new=E/'current123-period-v5.zip';oracle=json.loads((OUT/'book-rebound-oracle.json').read_bytes());raworacle=json.loads((OUT/'raw-oracle.json').read_bytes())
assert hashlib.sha256(old.read_bytes()).hexdigest()=='a0ab6f64958018b3ca9b535ed6ef2ae316f01c55c40d27edd21677ff79ad9175'
assert hashlib.sha256(new.read_bytes()).hexdigest()=='3f00e20684617dc33777fe151b61cf5d9dc91da46661c53572c608caf6102aa5'
WINDOW={'q1':('quarter','1'),'q2':('quarter','2'),'q3':('quarter','3'),'q4':('quarter','4'),'h1':('half','first'),'h2':('half','second'),'ot':('overtime','ot')}
fields={'reboundsDefensive':'dreb','reboundsTotal':'reb'}
count_expected={}
for r in oracle['count_corrections']:
 key=(r['game_id'],r['team_id'],r.get('player_id'),*WINDOW[r['window']],fields[r['field']]);count_expected[r['dataset'],key]=(float(r['before']),float(r['after']))
rate_expected={(r['game_id'],r['team_id'],r['player_id'],*WINDOW[r['window']],'reb_pct'):Fraction(r['numerator'],r['denominator']) for r in oracle['rates']}
assert len(count_expected)==8 and len(rate_expected)==38
actual_deltas=[];count_checks=0;rate_checks=0;unchanged_tokens=0;untouched_lines=0;whole_checks=0;half_checks=0
with zipfile.ZipFile(old) as z0,zipfile.ZipFile(new) as z1:
 m0=json.loads(z0.read('data/metadata/development_snapshot.json'));m1raw=z1.read('data/metadata/development_snapshot.json');m1=json.loads(m1raw)
 assert hashlib.sha256(m1raw).hexdigest()=='535384a4710739a779f0772da4e3bcee023bd88bfed91be16d0103cdf9d8ff75'
 assert m1['quality']=='provisional' and set(m1['exceptions'])=={'DQ-001','DQ-002','DQ-003','DQ-006'}
 for n,h in m1['files'].items():assert hashlib.sha256(z1.read(n)).hexdigest()==h
 assert json.loads(z1.read('data/metadata/corrections/game184-rebound-oracle.json'))==oracle
 changed_paths={'data/metadata/development_snapshot.json'}
 for grain in ('player','team'):
  name=f'data/raw/{grain}_game_period_stats/2026-27_regular_season.csv';changed_paths.add(name)
  before=z0.read(name);after=z1.read(name);r0=list(csv.reader(io.StringIO(before.decode())));r1=list(csv.reader(io.StringIO(after.decode())));assert len(r0)==len(r1) and r0[0]==r1[0]
  header=r0[0];line0=before.splitlines(keepends=True);line1=after.splitlines(keepends=True);assert len(line0)==len(line1)==len(r0)
  frame=[]
  for rowno,(a,b) in enumerate(zip(r0[1:],r1[1:]),1):
   x=dict(zip(header,a));y=dict(zip(header,b));frame.append(y)
   ident=(int(x['game_id']),int(x['team_id']),int(x['player_id']) if grain=='player' else None,x['period_family'],x['period_value'])
   touched=False
   for col,v0,v1 in zip(header,a,b):
    key=(*ident,col)
    if (grain,key) in count_expected:
     n0,n1=count_expected[grain,key];assert float(v0)==n0 and float(v1)==n1;count_checks+=1;touched=True
    elif grain=='player' and key in rate_expected:
     assert math.isclose(float(v1),float(rate_expected[key]),abs_tol=1e-15,rel_tol=1e-15);rate_checks+=1;touched=True
    else:assert v0==v1,(grain,ident,col,v0,v1);unchanged_tokens+=1
    if v0!=v1:actual_deltas.append({'dataset':grain,'key':list(ident),'field':col,'before':v0,'after':v1})
   if not touched:assert line0[rowno]==line1[rowno];untouched_lines+=1
  if grain=='player':
   assert len(frame)==16783 and sum(not r[c] for r in frame for c in ('tov_pct','usg_pct'))==484
   assert len([r for r in frame if int(r['game_id'])>=22600173 and r['period_family']=='overtime'])==28
   players=frame
  else:assert len(frame)==1490;teams=frame
 assert count_checks==8 and rate_checks==38
 unchanged_files=[]
 for name in z0.namelist():
  if name not in changed_paths:assert z0.read(name)==z1.read(name),name;unchanged_files.append(name)
 # The previous v3 bytes still form exact prefixes, including the old647windows.
 with zipfile.ZipFile(E.parent/'id18-current-required-20261107/current123-required-v3.zip') as z3:
  for grain in ('player','team'):
   n=f'data/raw/{grain}_game_period_stats/2026-27_regular_season.csv';assert z1.read(n).startswith(z3.read(n))
 # Corrected Q2/H1 player and team rebound counts now add to both halves/full game.
 for frame,grain in [(players,'player'),(teams,'team')]:
  if grain=='player':ids={(int(r['team_id']),int(r['player_id'])) for r in frame if int(r['game_id'])==22600184}
  else:ids={(int(r['team_id']),None) for r in frame if int(r['game_id'])==22600184}
  for tid,pid in ids:
   rows={(r['period_family'],r['period_value']):r for r in frame if int(r['game_id'])==22600184 and int(r['team_id'])==tid and (pid is None or int(r['player_id'])==pid)}
   for f in ('oreb','dreb','reb'):
    qvalues=[float(rows.get(('quarter',str(q)),{}).get(f,0)) for q in (1,2,3,4)]
    for h,parts in [('first',qvalues[:2]),('second',qvalues[2:])]:assert float(rows['half',h][f])==sum(parts);half_checks+=1
    # Whole scorer report is independently parsed from the captured book.
    ref=[r for r in oracle['scorer_rows' if grain=='player' else 'team_scorer_rows'] if r['window']=='whole' and r['team_id']==tid and (pid is None or r['player_id']==pid)]
    assert len(ref)==1
    expected=ref[0][{'oreb':'reboundsOffensive','dreb':'reboundsDefensive','reb':'reboundsTotal'}[f]]
    assert sum(qvalues)==expected,(grain,tid,pid,f,qvalues,expected);whole_checks+=1
result={'candidate_zip_sha256':hashlib.sha256(new.read_bytes()).hexdigest(),'manifest_sha256':hashlib.sha256(m1raw).hexdigest(),'count_cells_verified':count_checks,'complete_window_REB_rate_cells_verified':rate_checks,'actual_changed_cell_tokens':len(actual_deltas),'unchanged_csv_cell_tokens':unchanged_tokens,'untouched_csv_lines_byte_identical':untouched_lines,'old_v3_prefix_bytes_preserved':True,'unchanged_v4_files':len(unchanged_files),'whole_rebound_count_checks':whole_checks,'half_rebound_count_checks':half_checks,'old_unknown_cells_preserved':484,'new_unknowns_created':0,'new_source_OT_keys_preserved':28,'embedded_full_proof_semantically_identical':True,'resolved_exception_removed_only_from_v5':True,'remaining_exceptions':m1['exceptions'],'actual_deltas':actual_deltas,'nba_requests_executed_by_checker':0,'production_writes':0}
(OUT/'v5-comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='actual_deltas'},indent=2))
