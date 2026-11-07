"""Read-only inventory oracle. No network calls or source modifications."""
from pathlib import Path
from zipfile import ZipFile
import csv,hashlib,io,json,re
ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent
SOURCE=ROOT/'working/nba-tools-completion-program/source-evidence'
REQUEST=ROOT/'working/nba-tools-completion-program/collection-requests/current123-new16-periods-20261107.json'
DENOM=SOURCE/'core-live-current-20261107/new16-window-denominator.json'
sha=lambda b:hashlib.sha256(b).hexdigest()
req=json.loads(REQUEST.read_bytes()); den=json.loads(DENOM.read_bytes())
def key(j):
 p=j['parameters'];return (j['endpoint'],p['GameID'],p['StartPeriod'],p['EndPeriod'],p['RangeType'],p['StartRange'],p['EndRange'])
expected=set()
for game in den['new16']:
 for start,end in [(1,1),(2,2),(3,3),(4,4),(1,2),(3,4)]+([(5,14)] if game['ot'] else []):
  for ep in ('boxscoretraditionalv3','boxscoreadvancedv3'):expected.add((ep,game['game_id'],start,end,1,0,28800))
assert len(req['jobs'])==len({key(j) for j in req['jobs']})==len(expected)==196
assert {key(j) for j in req['jobs']}==expected
assert len(den['new16'])==16 and sum(g['played_player_rows'] for g in den['new16'])*6==2208
assert sum(g['required_quarter_half_windows'] for g in den['new16'])==98
assert den['old107_windows']+98==745
archive_rows=[];captures=[];new_bodies=[];matches=[]
for p in sorted(SOURCE.rglob('*.zip')):
 if OUT.parent in p.parents:continue
 raw=p.read_bytes(); row={'path':str(p.relative_to(ROOT)),'sha256':sha(raw),'bytes':len(raw)}
 with ZipFile(p) as z:
  assert z.testzip() is None
  row['members']=len(z.namelist());row['new16_members']=[]
  for n in z.namelist():
   if re.search(r'0022600(?:17[3-9]|18[0-8])',n):
    item={'archive':row['path'],'member':n,'sha256':sha(z.read(n)),'bytes':len(z.read(n))}
    row['new16_members'].append(n);new_bodies.append(item)
   if n.endswith('acquisition.json'):
    a=json.loads(z.read(n)); c={'archive':row['path'],'member':n,'sha256':sha(z.read(n)),'attempts':len(a.get('attempts',[])),'unattempted':len(a.get('unattempted_jobs',[])),'stop_reason':a.get('stop_reason'),'exact_new16_attempts':[]}
    for r in a.get('attempts',[]):
     try:k=key(r)
     except (KeyError,TypeError):continue
     if k in expected:
      item={'key':list(k),'response_bytes':r.get('response_bytes'),'transport_complete':r.get('transport_complete'),'source_file':r.get('source_file'),'response_sha256':r.get('response_sha256')};c['exact_new16_attempts'].append(item)
      if r.get('transport_complete') and r.get('source_file') and r['source_file'] in z.namelist():
       assert sha(z.read(r['source_file']))==r['response_sha256'];matches.append(item)
    captures.append(c)
 archive_rows.append(row)
# Inspect unique work source cache (other worktrees carry duplicate repository evidence).
cache=ROOT/'work/current-required-source/work/source-qualification'
cache_rows=[]
retained_hashes={x['sha256'] for x in new_bodies}
for p in sorted(cache.rglob('*')):
 if p.is_file() and re.search(r'0022600(?:17[3-9]|18[0-8])',p.name):
  raw=p.read_bytes();cache_rows.append({'path':str(p.relative_to(ROOT)),'sha256':sha(raw),'bytes':len(raw),'exact_duplicate_of_retained_body':sha(raw) in retained_hashes})
assert not matches
partial_path=SOURCE/'id18-current-required-20261107/current-required/required-source-originals.zip'
with ZipFile(partial_path) as z:
 partial=z.read('archive-period-representative-0022600173.json'); obj=json.loads(partial)
 fragment=[]
 for period,v in obj.items():
  b=v['boxScoreTraditional'];assert b['gameId']=='0022600173'
  fragment.append({'period':period,'teams':[{'team_id':b[s]['teamId'],'minutes':b[s]['statistics']['minutes'],'points':b[s]['statistics']['points']} for s in ('homeTeam','awayTeam')]})
stage_path=SOURCE/'id18-current-required-20261107/current123-required-v3.zip'
stage_inventory=[]
with ZipFile(stage_path) as z:
 for name in z.namelist():
  if '/raw/' in name and 'game_period_stats' in name:
   raw=z.read(name);rows=list(csv.DictReader(io.StringIO(raw.decode())))
   windows={(r['game_id'].zfill(10),int(r['source_start_period']),int(r['source_end_period'])) for r in rows}
   assert len(windows)==647 and len({w[0] for w in windows})==107
   assert not ({w[0] for w in windows}&set(req['game_ids']))
   stage_inventory.append({'archive':str(stage_path.relative_to(ROOT)),'archive_sha256':sha(stage_path.read_bytes()),'member':name,'sha256':sha(raw),'rows':len(rows),'unique_windows':len(windows),'games':107,'overlap_with_new16_games':0})
report={'reviewer':'/root/period_source_checker','model':'not exposed by runtime','base_main':'226f62b5360b621bc52ce59df3239eda065f87ef','request_sha256':sha(REQUEST.read_bytes()),'denominator_sha256':sha(DENOM.read_bytes()),'network_requests':0,'scope':{'new_games':16,'new_windows':98,'old_qualified_windows_preserved':647,'required_total_windows':745,'new_team_period_keys':196,'new_standard_player_keys':2208,'new_OT_player_keys':'source-defined; unknown until actual source rows including zero-clock rows qualify','jobs':196,'OT_games':['0022600179','0022600186']},'qualified_retained_exact_new_period_responses':matches,'missing_exact_jobs':[{'endpoint':k[0],'GameID':k[1],'StartPeriod':k[2],'EndPeriod':k[3],'RangeType':k[4],'StartRange':k[5],'EndRange':k[6]} for k in sorted(expected)],'staged_period_inventory':stage_inventory,'retained_zip_inventory':archive_rows,'capture_metadata_inventory':captures,'retained_new16_named_bodies':new_bodies,'unique_cache_inventory':cache_rows,'partial173':{'sha256':sha(partial),'quarters':fragment,'qualification':'Partial clock/score fragments; not complete quarter or half source. Does not fulfill any exact request.'},'conclusion':'All196 requested bodies remain missing. Earlier qualified windows are excluded. No retained exact new-window success can be reused. This read-only inventory establishes no changed cloud route; no source retry was made.'}
(OUT/'retained-inventory-oracle.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'archives':len(archive_rows),'capture_receipts':len(captures),'new16namedbodies':len(new_bodies),'cachefiles':len(cache_rows),'cache_exact_duplicates':sum(x['exact_duplicate_of_retained_body'] for x in cache_rows),'exact_new_period_successes':len(matches),'partial173':report['partial173']},indent=2))
