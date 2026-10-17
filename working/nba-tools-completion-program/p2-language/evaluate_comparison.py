"""Finite independent assessment of frozen receipts; does not run either interpreter."""
import hashlib,json,math,statistics
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).parent
truth=json.loads((ROOT/'holdouts.json').read_text())
assert hashlib.sha256((ROOT/'holdouts.json').read_bytes()).hexdigest()=='d65cf93f47b03bd9263105ecb91bb3e4936e73c9bbfb5a08d2261bbab39c1027'
names={203999:'Nikola Jokić',1628973:'Jalen Brunson',1630162:'Anthony Edwards',1628401:'Derrick White'}
def assess(c,r,control=False):
 m=r.get('metadata') or {};res=r.get('result') or {};status=r.get('status');reason=res.get('result_reason')
 if control:
  return ('wrong_accepted' if status=='ok' else 'error' if status=='error' else 'ambiguity' if reason=='ambiguous' or m.get('entity_ambiguity') else 'safe_refusal'),[]
 if status!='ok':return ('error' if status=='error' else 'ambiguity' if reason=='ambiguous' or m.get('entity_ambiguity') else 'refusal'),[str(reason or status)]
 errors=[]
 def check(ok,why):
  if not ok:errors.append(why)
 check(r.get('route') in c['intended_routes'],'route')
 check(m.get('team' if c['kind']=='team' else 'player')==(c['subject'] if c['kind']=='team' else names[c['subject']]),'subject')
 check(m.get('season_type')=='Regular Season','season_type')
 check(set(m.get('season_list') or [])==set(c['seasons']) if c.get('split') else m.get('season')==c['seasons'][0],'season selection')
 labels={a['label']:a['value'] for a in m.get('applied_filters',[])}
 if 'opponent' in c:check(m.get('opponent')==c['opponent'],'opponent metadata')
 if 'home' in c:check(labels.get('Location')==('Home' if c['home'] else 'Away'),'venue label')
 conditions=(m.get('conditions') or [])+(m.get('threshold_conditions') or [])
 if m.get('stat'):conditions.append({'stat':m['stat'],'min_value':m.get('min_value'),'max_value':m.get('max_value')})
 if 'own_min' in c:check(any(x.get('stat')=='pts' and x.get('min_value')==c['own_min'] for x in conditions),'owned pts threshold')
 if 'opponent_lt' in c:check(any(x.get('stat')=='opponent_pts' and isinstance(x.get('max_value'),(int,float)) and c['opponent_lt']-1<=x['max_value']<c['opponent_lt'] for x in conditions),'opponent threshold')
 if 'last_n' in c:
  check(m.get('last_n')==c['last_n'] and m.get('last_n_scope')==c['last_n_scope'],'last N order metadata')
  check('Sample selection' in labels,'sample selection label')
 if 'participation' in c:check(m.get(c['participation']+'_player')=='Jayson Tatum','participation identity/relation')
 sections=res.get('sections') or {};actual=sections.get('split_comparison',[]) if c.get('split') else sections.get('summary',[])
 expected_keys={b['season'] for b in c['expected_buckets'] if b['count']}
 if c.get('split'):check({a.get('bucket') for a in actual}==expected_keys,'bucket set')
 else:check(len(actual)==1,'single summary')
 for b in c['expected_buckets']:
  key=b['season'] if c.get('split') else None
  if not b['count']:
   check(any(b['season'] in str(note) for note in res.get('caveats',[])),'empty-season caveat '+b['season']);continue
  rows=[a for a in actual if not c.get('split') or a.get('bucket')==key]
  if len(rows)!=1:errors.append('missing/duplicate result bucket '+str(key));continue
  a=rows[0]
  for field,expected in [('games',b['count']),('wins',b['wins']),('losses',b['losses'])]:check(a.get(field)==expected,str(key)+' '+field)
  for stat in ['pts','reb','ast']:
   value=a.get(stat+'_avg');check(isinstance(value,(float,int)) and abs(value-b['averages'][stat])<=0.001,str(key)+' '+stat+'_avg')
   if stat+'_sum' in a:check(a[stat+'_sum']==b['sums'][stat],str(key)+' '+stat+'_sum')
  samples=[s for s in r.get('captured_samples',[]) if s.get('bucket')==key]
  ids=samples[0]['ids'] if len(samples)==1 else sections.get('game_log',[]) if not c.get('split') and c['kind']=='player' else []
  keys=['game_id','team_id']+(['player_id'] if c['kind']=='player' else [])
  try:
   observed=[tuple(int(x[k]) for k in keys) for x in ids];expected=[tuple(int(x[k]) for k in keys) for x in b['ids']]
   check(len(observed)==len(expected) and set(observed)==set(expected),str(key)+' exact sample identities')
  except (KeyError,ValueError,TypeError):errors.append(str(key)+' invalid identity schema')
 return ('wrong_accepted' if errors else 'correct'),errors
results={};hashes={};all_latencies={}
for path in ['incumbent','candidate']:
 detail=[];cold=[];warm=[]
 for control,cases in [(False,truth['valid_cases']),(True,truth['controls'])]:
  for c in cases:
   f=ROOT/'receipts'/(c['id']+'-'+path+'.json');hashes[f.name]=hashlib.sha256(f.read_bytes()).hexdigest();runs=json.loads(f.read_text());assert len(runs)==4
   outcomes=[]
   for r in runs:
    verdict,errors=assess(c,r,control);outcomes.append(dict(repetition=r['repetition'],verdict=verdict,errors=errors))
    (cold if r['repetition']==0 else warm).append(r['seconds'])
   distinct={x['verdict'] for x in outcomes};case_verdict=next(iter(distinct)) if len(distinct)==1 else 'unstable'
   detail.append(dict(id=c['id'],control=control,verdict=case_verdict,repetitions=outcomes))
 def percentile95(xs):return sorted(xs)[math.ceil(.95*len(xs))-1]
 results[path]=dict(valid_counts=dict(Counter(x['verdict'] for x in detail if not x['control'])),control_counts=dict(Counter(x['verdict'] for x in detail if x['control'])),latency=dict(cold_max=max(cold),warm_p95=percentile95(warm),warm_median=statistics.median(warm),cold_limit_pass=max(cold)<=5,warm_limit_pass=percentile95(warm)<=2),cases=detail)
base=results['incumbent']['latency']['warm_median'];cand=results['candidate']['latency']['warm_median'];overhead=cand-base;limit=max(.2*base,.1)
output=dict(holdouts_sha256=hashlib.sha256((ROOT/'holdouts.json').read_bytes()).hexdigest(),receipt_sha256=hashes,results=results,candidate_median_overhead_seconds=overhead,allowed_median_overhead_seconds=limit,overhead_limit_pass=overhead<=limit,decision='Do not adopt candidate: wrong accepted answers fail the frozen selection rule.',limitations=['Finite local staged-source experiment, not deployed or published-data acceptance.','Controls count safe containment only, never positive capability completion; refusal does not certify a helpful explanation. Control 7 refuses for unsupported win_pct after a subject rewrite, not demonstrated understanding of exhaustion.','Cold-process timings are retained runner measurements; filesystem cache may already be warm.','Team and split exact IDs rely on captured sample hooks; player summaries use returned game logs.','Metadata checks require semantic identities/qualifiers; no permissive route-only success.'])
(ROOT/'evaluation.json').write_text(json.dumps(output,indent=2)+'\n')
print(json.dumps({k:{x:v for x,v in value.items() if x!='cases'} for k,value in results.items()},indent=2))
