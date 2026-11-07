"""Independent original-body oracle; no application or staging imports, no network."""
import csv,hashlib,io,json,math,re,zipfile,collections
from pathlib import Path
from datetime import datetime
ROOT=Path('/workspace/nbatools')
OUT=ROOT/'work/current123-period-independent'
CAPTURE=Path('/tmp/codex-remote-attachments/01a1b46e-3c65-77e4-8e3a-66c0cd0520fa/75B5E594-9B94-482B-B1C0-4E6B20C9E9EE/1-collection-3.zip')
E=ROOT/'working/nba-tools-completion-program/source-evidence'
PLAN=json.loads((E.parent/'collection-requests/current123-new16-periods-20261107.json').read_bytes())
FIELDS={'fieldGoalsMade':'fgm','fieldGoalsAttempted':'fga','threePointersMade':'fg3m','threePointersAttempted':'fg3a','freeThrowsMade':'ftm','freeThrowsAttempted':'fta','reboundsOffensive':'oreb','reboundsDefensive':'dreb','reboundsTotal':'reb','assists':'ast','steals':'stl','blocks':'blk','turnovers':'tov','foulsPersonal':'pf','points':'pts','plusMinusPoints':'plus_minus'}
RATE={'usagePercentage':'usg_pct','assistPercentage':'ast_pct','reboundPercentage':'reb_pct','turnoverRatio':'tov_pct'}
def sha(b):return hashlib.sha256(b).hexdigest()
def clock(x):
 assert isinstance(x,str) and re.fullmatch(r'\d+:\d\d',x),x
 m,s=map(int,x.split(':'));assert 0<=s<60
 return m*60+s
checks=collections.Counter();failures=[];warnings=[]
def check(condition,code,detail):
 checks[code]+=1
 if not condition:failures.append({'code':code,'detail':detail})
with zipfile.ZipFile(E/'id18-current-required-20261107/current123-required-v3.zip') as z:
 core=list(csv.DictReader(io.StringIO(z.read('data/raw/player_game_stats/2026-27_regular_season.csv').decode())))
with zipfile.ZipFile(E/'core-live-current-20261107/new16-summary-originals.zip') as z:
 summary={d['boxScoreSummary']['gameId']:d['boxScoreSummary'] for n in z.namelist() if 'boxScoreSummary' in (d:=json.loads(z.read(n)))}
with zipfile.ZipFile(E/'id18-current-required-20261107/current-required/required-source-originals.zip') as z:
 whole={d['boxScoreTraditional']['gameId']:d['boxScoreTraditional'] for n in z.namelist() if n.startswith('boxscoretraditionalv3-') and isinstance((d:=json.loads(z.read(n))),dict) and 'boxScoreTraditional' in d}
with zipfile.ZipFile(CAPTURE) as z:
 assert len(CAPTURE.read_bytes())==527213 and sha(CAPTURE.read_bytes())=='81eea4d32217e541cab13783a06031616abb192e56b7c7b37d10f1f460978faf'
 assert len(z.infolist())==199 and z.testzip() is None
 assert len({e.filename for e in z.infolist()})==199 and sum(e.file_size for e in z.infolist())<100_000_000
 manifest=json.loads(z.read('collection-manifest.json'));report=json.loads(z.read('acquisition.json'))
 assert manifest['request']==report['request']==PLAN
 assert sha(json.dumps(PLAN,sort_keys=True,separators=(',',':')).encode())==manifest['request_sha256']==report['request_sha256']=='19cc7759dd2dec7676888538b574e3dd316d6b58712b2b30d42c9b92911a9a52'
 assert report['transport_finished'] and report['production_writes']==0 and not report['canonical_period_accepted'] and report['unattempted_jobs']==[]
 assert len(report['attempts'])==len(PLAN['jobs'])==196
 assert z.read('acquisition.json')==z.read('sources/capture-attempt.json')
 assert set(z.namelist())==set(manifest['files'])|{'collection-manifest.json'}
 for name,info in manifest['files'].items():
  b=z.read(name);assert len(b)==info['bytes'] and sha(b)==info['sha256']
 for job,a in zip(PLAN['jobs'],report['attempts']):
  assert job==a['job'] and job['parameters']==a['parameters'] and a['url']=='https://stats.nba.com/stats/'+job['endpoint']
  assert a['attempts']==1 and a['timeout_seconds']==30 and a['http_status']==200 and a['response_complete'] and a['transport_complete'] and 'error_type' not in a
  assert a['response_sha256']==sha(z.read(job['source_file'])) and a['response_bytes']==len(z.read(job['source_file']))<=2_000_000
 elapsed=(datetime.fromisoformat(report['finished_at'])-datetime.fromisoformat(report['captured_at'])).total_seconds();assert elapsed<1050
 repairs=[]; repair_seconds={}
 term_specs={'q1':[('h1',1),('q2',-1)],'q2':[('h1',1),('q1',-1)],'q3':[('h2',1),('q4',-1)],'q4':[('h2',1),('q3',-1)],'h1':[('q1',1),('q2',1)],'h2':[('q3',1),('q4',1)]}
 for job in PLAN['jobs']:
  source_name=job['source_file'];tag=source_name.rsplit('_',1)[1][:-5];gid=job['parameters']['GameID'];ep=job['endpoint'];key='boxScoreTraditional' if ep=='boxscoretraditionalv3' else 'boxScoreAdvanced'
  box=json.loads(z.read(source_name))[key]
  for side in ('homeTeam','awayTeam'):
   for person in box[side]['players']:
    literal=person['statistics']['minutes']
    try: clock(literal); continue
    except AssertionError: pass
    pid=person['personId'];tid=box[side]['teamId'];seconds=0;counts={f:0 for f in FIELDS};terms=[]
    for term,coef in term_specs[tag]:
     n=f'sources/{ep}_{gid}_{term}.json';b=json.loads(z.read(n))[key];assert b['gameId']==gid and b[side]['teamId']==tid
     p=next(p for p in b[side]['players'] if p['personId']==pid);v=clock(p['statistics']['minutes']);seconds+=coef*v
     terms.append({'window':term,'coefficient':coef,'literal':p['statistics']['minutes'],'source_sha256':sha(z.read(n))})
     tr=json.loads(z.read(f'sources/boxscoretraditionalv3_{gid}_{term}.json'))['boxScoreTraditional'];x=next(p['statistics'] for p in tr[side]['players'] if p['personId']==pid)
     for f in FIELDS:counts[f]+=coef*x[f]
    target=json.loads(z.read(f'sources/boxscoretraditionalv3_{gid}_{tag}.json'))['boxScoreTraditional'];stats=next(p['statistics'] for p in target[side]['players'] if p['personId']==pid)
    assert all(counts[f]==stats[f] for f in FIELDS) and 0<seconds<=1440
    repair_seconds[(gid,tag,tid,pid,ep)]=seconds
    repairs.append({'game_id':gid,'window':tag,'team_id':tid,'player_id':pid,'endpoint':ep,'original_literal':literal,'derived_seconds':seconds,'derived_literal':f'{seconds//60}:{seconds%60:02d}','count_cells_matched':len(FIELDS),'terms':terms,'original_sha256':sha(z.read(source_name))})
 assert len(repairs)==6
 def pclock(gid,tag,tid,pid,ep,literal):
  try:return clock(literal)
  except AssertionError:return repair_seconds[(gid,tag,tid,pid,ep)]
 rows=[];teams=[];zero=[];raw_by_window={};clock_deltas=[];raw_counts=collections.Counter()
 jobs=[j for j in PLAN['jobs'] if j['endpoint']=='boxscoretraditionalv3']
 for job in jobs:
  name=job['source_file'];tag=name.rsplit('_',1)[1][:-5];gid=job['parameters']['GameID'];start=job['parameters']['StartPeriod'];end=job['parameters']['EndPeriod']
  t=json.loads(z.read(name))['boxScoreTraditional'];a=json.loads(z.read(name.replace('traditional','advanced')))['boxScoreAdvanced'];s=summary[gid]
  check(t['gameId']==a['gameId']==s['gameId']==gid,'game_identity',name)
  win={}
  for side in ('homeTeam','awayTeam'):
   tid=t[side]['teamId'];ref=s[side];opp=s['awayTeam' if side=='homeTeam' else 'homeTeam']
   check(tid==a[side]['teamId']==ref['teamId']==whole[gid][side]['teamId'],'team_side_identity',(gid,tag,side))
   periods=[p for p in ref['periods'] if start<=p['period']<=end];duration=sum(720 if p['period']<=4 else 300 for p in periods)
   ts=t[side]['statistics'];ats=a[side]['statistics'];pts=sum(p['score'] for p in periods);op=sum(p['score'] for p in opp['periods'] if start<=p['period']<=end)
   check(ts['points']==pts and ts['plusMinusPoints']==pts-op,'summary_score_and_margin',(gid,tag,tid,pts,ts['points']))
   check(clock(ts['minutes'])==clock(ats['minutes'])==duration*5,'team_clock',(gid,tag,tid,ts['minutes'],ats['minutes']))
   tp={p['personId']:p for p in t[side]['players']};ap={p['personId']:p for p in a[side]['players']}
   check(len(tp)==len(t[side]['players']) and len(ap)==len(a[side]['players']) and tp.keys()==ap.keys(),'source_player_identity_sets',(gid,tag,tid))
   whole_ids={p['personId'] for p in whole[gid][side]['players']};context={int(p['player_id']) for p in core if int(p['game_id'])==int(gid) and int(p['team_id'])==tid}
   check(tp.keys()<=whole_ids and tp.keys()<=context,'whole_participation_membership',(gid,tag,tid,list(tp.keys()-context)))
   delta=sum(pclock(gid,tag,tid,pid,'boxscoretraditionalv3',p['statistics']['minutes']) for pid,p in tp.items())-5*duration;clock_deltas.append(delta)
   check(abs(delta)<=2,'player_clock_sum',(gid,tag,tid,delta))
   check(sum(p['statistics']['points'] for p in tp.values())==ts['points'],'player_points_sum',(gid,tag,tid))
   for pid,p in [(None,{'statistics':ts}),*tp.items()]:
    x=p['statistics'];k=(gid,tag,tid,pid)
    for f in FIELDS:
     v=x[f];check(type(v) in (int,float) and math.isfinite(v) and v==int(v) and (v>=0 or f=='plusMinusPoints'),'finite_integer_counts',(k,f,v))
    check(x['reboundsOffensive']+x['reboundsDefensive']==x['reboundsTotal'],'rebound_identity',k)
    check(x['fieldGoalsMade']<=x['fieldGoalsAttempted'] and x['threePointersMade']<=x['threePointersAttempted'] and x['freeThrowsMade']<=x['freeThrowsAttempted'] and 2*x['fieldGoalsMade']+x['threePointersMade']+x['freeThrowsMade']==x['points'],'shot_and_point_arithmetic',k)
   tr={'game_id':int(gid),'team_id':tid,'window':tag,'minutes':clock(ts['minutes'])/60,**{v:ts[k] for k,v in FIELDS.items()}}
   teams.append(tr)
   pdict={}
   for pid,p in tp.items():
    x=p['statistics'];ax=ap[pid]['statistics'];sec=pclock(gid,tag,tid,pid,'boxscoretraditionalv3',x['minutes']);asec=pclock(gid,tag,tid,pid,'boxscoreadvancedv3',ax['minutes']);k=(gid,tag,tid,pid)
    check(0<=sec<=duration and abs(sec-asec)<=1,'player_clock_pair',k)
    for f in RATE:
     val=ax[f];ceiling=100 if f=='turnoverRatio' else 1
     check(type(val) in (int,float) and math.isfinite(val) and 0<=val<=ceiling,'source_rate_scale',(k,f,val))
    den=2*(x['fieldGoalsAttempted']+0.44*x['freeThrowsAttempted'])
    expected_ts=x['points']/den if den else 0
    expected_efg=(x['fieldGoalsMade']+0.5*x['threePointersMade'])/x['fieldGoalsAttempted'] if x['fieldGoalsAttempted'] else 0
    check(abs(ax['trueShootingPercentage']-expected_ts)<=0.000501,'source_ts_rounding',(k,ax['trueShootingPercentage'],expected_ts))
    check(abs(ax['effectiveFieldGoalPercentage']-expected_efg)<=0.000501,'source_efg_rounding',(k,ax['effectiveFieldGoalPercentage'],expected_efg))
    r={'game_id':int(gid),'team_id':tid,'player_id':pid,'player_name':p['firstName']+' '+p['familyName'],'window':tag,'source_clock':x['minutes'],'clock_basis':'complementary_derived' if (gid,tag,tid,pid,'boxscoretraditionalv3') in repair_seconds else 'literal_source','minutes':sec/60,**{v:x[k] for k,v in FIELDS.items()},**{v:ax[k]/(100 if k=='turnoverRatio' else 1) for k,v in RATE.items()}}
    if sec==0:
     zero.append(r);check(all(x[f]==0 for f in FIELDS),'zero_clock_counts',k)
     r.update({v:0 for v in RATE.values()})
    rows.append(r);pdict[pid]=x;raw_counts[tag]+=1
   win[tid]={'team':ts,'players':pdict}
  raw_by_window[(gid,tag)]=win
 # Additive cross-window checks directly against original source bodies.
 for gid in sorted(whole):
  for tag,parts in [('h1',['q1','q2']),('h2',['q3','q4'])]:
   for tid,w in raw_by_window[(gid,tag)].items():
    for f in FIELDS:
     check(w['team'][f]==sum(raw_by_window[(gid,p)][tid]['team'][f] for p in parts),'team_half_additivity',(gid,tag,tid,f,w['team'][f],sum(raw_by_window[(gid,p)][tid]['team'][f] for p in parts)))
    ids=set(w['players'])|set().union(*(set(raw_by_window[(gid,p)][tid]['players']) for p in parts))
    for pid in ids:
     for f in FIELDS:
      actual=w['players'].get(pid,{}).get(f,0);expected=sum(raw_by_window[(gid,p)][tid]['players'].get(pid,{}).get(f,0) for p in parts)
      check(actual==expected,'player_half_additivity',(gid,tag,tid,pid,f,actual,expected))
    # Use actual independently retained Summary for each game, never loop's stale summary.
  tags=['q1','q2','q3','q4']+(['ot'] if summary[gid]['period']>4 else [])
  for side in ('homeTeam','awayTeam'):
   w=whole[gid][side];tid=w['teamId'];wt=w['statistics'];wp={p['personId']:p['statistics'] for p in w['players']}
   for f in FIELDS:
    actual=sum(raw_by_window[(gid,p)][tid]['team'][f] for p in tags)
    check(actual==wt[f],'team_whole_additivity',(gid,tid,f,actual,wt[f]))
   for pid,stats in wp.items():
    for f in FIELDS:
     actual=sum(raw_by_window[(gid,p)][tid]['players'].get(pid,{}).get(f,0) for p in tags)
     check(actual==stats[f],'player_whole_additivity',(gid,tid,pid,f,actual,stats[f]))
 observed={(r['game_id'],r['window'],r['team_id'],r['player_id']) for r in rows}
 synthetic=[]
 for p in core:
  if 173<=int(p['game_id'])%100000<=188:
   for tag in ('q1','q2','q3','q4','h1','h2'):
    key=(int(p['game_id']),tag,int(p['team_id']),int(p['player_id']))
    if key not in observed:
     synthetic.append({'game_id':key[0],'window':tag,'team_id':key[2],'player_id':key[3],'player_name':p['player_name'],'clock_basis':'qualified_complete_standard_window_nonparticipation','minutes':0,**{c:0 for c in [*FIELDS.values(),*RATE.values()]}})
 expected_rows=rows+synthetic
 assert len(synthetic)==317 and len(expected_rows)==2236
 for r in expected_rows:
  r['efg_pct']=(r['fgm']+0.5*r['fg3m'])/r['fga'] if r['fga'] else 0
  denominator=2*(r['fga']+0.44*r['fta']);r['ts_pct']=r['pts']/denominator if denominator else 0
 oracle={'input_zip_sha256':sha(CAPTURE.read_bytes()),'request_sha256':manifest['request_sha256'],'nba_requests_executed_by_checker':0,'source_windows':len(jobs),'team_rows':teams,'source_player_rows':rows,'canonical_player_rows':expected_rows,'standard_missing_source_zero_rows':len(synthetic),'canonical_new_player_rows':len(expected_rows),'clock_derivations':repairs,'zero_clock_rows':zero,'raw_player_counts_by_window':dict(raw_counts),'checks':dict(checks),'failures':failures,'clock_delta_bounds_seconds':[min(clock_deltas),max(clock_deltas)],'elapsed_seconds':elapsed,'whole_source_origin':'retained qualified archive originals; separate source body, not proven independent upstream scorer origin'}
 (OUT/'raw-oracle.json').write_text(json.dumps(oracle,indent=2)+'\n')
 print(json.dumps({k:v for k,v in oracle.items() if k not in ('team_rows','source_player_rows','zero_clock_rows','canonical_player_rows','clock_derivations','failures')},indent=2));print('FAILURES',len(failures));print(json.dumps(failures[:30],indent=2));print('ZERO',json.dumps(zero,indent=2))
