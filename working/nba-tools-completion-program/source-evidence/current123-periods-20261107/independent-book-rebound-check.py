"""Independent fixed-game scorer/PBP rebound oracle, original PDF only."""
from pathlib import Path
from fractions import Fraction
from collections import Counter,defaultdict
from zipfile import ZipFile
import hashlib,json,re,unicodedata
ROOT=Path('/workspace/nbatools');OUT=ROOT/'work/current123-period-independent';PAGES=OUT/'book'
CAP=ROOT/'working/nba-tools-completion-program/source-evidence/current123-periods-20261107/hosted-initial/acquired_data/current123-game184-book'
pdf=next(CAP.glob('*.pdf'));assert hashlib.sha256(pdf.read_bytes()).hexdigest()=='5d11d1974ca1426afda19575cc9a8af316d5a9471f26ced48f8470bbaf830b2b'
with ZipFile(ROOT/'working/nba-tools-completion-program/source-evidence/id18-current-required-20261107/current-required/required-source-originals.zip') as z:whole=json.loads(z.read('boxscoretraditionalv3-0022600184.json'))['boxScoreTraditional']
home=1610612759;away=1610612742
teams={whole[s]['teamId']:whole[s] for s in ('awayTeam','homeTeam')}
def norm(x):return re.sub('[^a-z0-9]','',unicodedata.normalize('NFKD',x).encode('ascii','ignore').decode().lower())
alias={}
for tid,t in teams.items():
 a=defaultdict(set)
 for p in t['players']:
  for v in [p['firstName'][0]+'.'+p['familyName'],p['nameI'],p['firstName']+' '+p['familyName']]:a[norm(v)].add(p['personId'])
 alias[tid]=a

def ident(tid,name):
 ids=alias[tid][norm(name)];assert len(ids)==1,(tid,name,ids)
 return next(iter(ids))
def seconds(token):
 if token.startswith(':'):return Fraction(token[1:])
 m,s=token.split(':');return Fraction(m)*60+Fraction(s)
starters={};events=[]
for q,pages in [(1,[8,9,10]),(2,[11,12,13])]:
 for page in pages:
  text=(PAGES/f'page-{page:02d}.txt').read_text();lines=text.splitlines();header=next(l for l in lines if l.startswith('Time '));scorecol=header.index('Score');leadcol=header.index('Lead');awaycol=header.index('Mavericks')
  if q not in starters:
   h=next(l for l in lines if l.startswith('SPURS Starters:')).split(':',1)[1].split();a=next(l for l in lines if l.startswith('Mavericks Starters:')).split(':',1)[1].split()
   starters[q]={home:{ident(home,n) for n in h},away:{ident(away,n) for n in a}}
   assert all(len(v)==5 for v in starters[q].values())
  for line_idx,line in enumerate(lines):
   m=re.match(r'^(\d\d:\d\d(?:\.\d)?|:\d\d\.\d)\s+',line)
   if not m:continue
   token=m[1];left=line[9:scorecol].strip();right=line[awaycol:].strip()
   # Text starts at its column's literal leading position, not headers' centered nickname.
   for tid,desc in [(home,left),(away,right)]:
    if not desc or desc.startswith('Start of Period') or desc.startswith('End of Period') or 'JUMP BALL' in desc:continue
    events.append({'period':q,'clock':token,'seconds':seconds(token),'team_id':tid,'description':desc,'page':page,'line':line_idx+1})
rebcounts=Counter();chances=Counter();clocks={};rebounds=[];pending=None;substitutions=[]
for q in (1,2):
 active={t:set(ps) for t,ps in starters[q].items()};previous=Fraction(720);duration=Counter();qevents=[e for e in events if e['period']==q]
 for e in qevents:
  at=e['seconds'];assert at<=previous,(q,e,previous)
  for tid,ps in active.items():
   assert len(ps)==5
   for pid in ps:duration[tid,pid]+=previous-at
  previous=at;desc=e['description'];tid=e['team_id']
  if desc.startswith('SUB:'):
   inc,out=re.fullmatch(r'SUB: (.+) FOR (.+)',desc).groups();pi,po=ident(tid,inc),ident(tid,out)
   assert po in active[tid] and pi not in active[tid],(e,active)
   active[tid].remove(po);active[tid].add(pi);substitutions.append({**e,'incoming':pi,'outgoing':po});continue
  if desc.endswith(' REBOUND'):
   name=desc.removesuffix(' REBOUND');teamreb=name in ('SPURS','Mavericks');pid=0 if teamreb else ident(tid,name)
   assert pending is not None,(e,'no preceding missed attempt')
   dead=(teamreb and at==0) or pending.get('nonterminal_ft',False) or pending.get('technical',False)
   if pid:assert pid in active[tid],(e,active)
   if not dead:
    for t,ps in active.items():
     for p in ps:chances[q,t,p]+=1
    if pid:rebcounts[q,tid,pid]+=1
   rebounds.append({**e,'player_id':pid,'dead_ball':dead,'preceding_miss':{k:v for k,v in pending.items() if k!='seconds'},'lineups':{str(t):sorted(ps) for t,ps in active.items()}})
   pending=None
  elif desc.startswith('MISS '):
   ft=re.search(r'Free Throw (\d) of (\d)',desc)
   pending={**e,'nonterminal_ft':bool(ft and ft[1]!=ft[2]),'technical':'Free Throw Technical' in desc}
  elif re.search(r'Free Throw|Jump Shot|Layup|Dunk|Hook Shot|Fadeaway|Tip Shot|Driving|TURNOVER',desc) and not desc.startswith('SUB:'):
   # A made terminal attempt/turnover clears a nonterminal missed-FT marker even
   # when the PDF omits the corresponding dead-ball team-rebound shell.
   if 'BLOCK' not in desc and 'STEAL' not in desc:pending=None
 # Allocate remaining clock to the literal end of period, even if final row is a continuation.
 for tid,ps in active.items():
  for pid in ps:duration[tid,pid]+=previous
 assert all(sum(s for (t,p),s in duration.items() if t==tid)==3600 for tid in teams)
 clocks[q]=duration
# Source scorer rows are parsed by fixed-table numeric tail, not inferred from reported rates.
scorer={};team_scorer={}
score_fields=['fieldGoalsMade','fieldGoalsAttempted','threePointersMade','threePointersAttempted','freeThrowsMade','freeThrowsAttempted','reboundsOffensive','reboundsDefensive','reboundsTotal','assists','foulsPersonal','steals','turnovers','blocks','plusMinusPoints','points']
for page,tag in [(0,'whole'),(1,'q1'),(2,'q2'),(3,'h1'),(4,'q3'),(6,'q4'),(7,'h2')]:
 lines=(PAGES/f'page-{page:02d}.txt').read_text().splitlines();tid=None
 for line in lines:
  if line.startswith('VISITOR:'):tid=away
  elif line.startswith('HOME:'):tid=home
  tm=re.match(r'^\s+(\d+:\d\d)\s+(.+)$',line)
  if tm and tid is not None and len(tm[2].split())==16 and all(re.fullmatch(r'-?\d+',v) for v in tm[2].split()):
   team_scorer[tag,tid]={'minutes':seconds(tm[1]),**dict(zip(score_fields,map(int,tm[2].split()))),'raw_line':line}
  m=re.match(r'^\d+\s+(.+?)\s+(?:[FCG]\s+)?(\d\d:\d\d)\s+(.+)$',line)
  if not m:continue
  pid=ident(tid,m[1].strip()) if norm(m[1].strip()) in alias[tid] else None
  if pid is None:
   # Full scorer names are an exact alias from the same retained player identity.
   pid=ident(tid,m[1].strip())
  numbers=m[3].split();assert len(numbers)==16,(tag,pid,numbers)
  v=list(map(int,numbers));scorer[tag,tid,pid]={'minutes':seconds(m[2]),'oreb':v[6],'dreb':v[7],'reb':v[8],**dict(zip(score_fields,v)),'raw_line':line}
for q in (1,2):
 tag='q'+str(q)
 for (t,p),s in clocks[q].items():
  expected=scorer.get((tag,t,p),{'minutes':0,'reb':0})
  assert abs(s-expected['minutes'])<=Fraction(1),(q,t,p,s,expected)
 for (tag0,t,p),v in scorer.items():
  if tag0==tag:assert rebcounts[q,t,p]==v['reb'],(tag,t,p,rebcounts[q,t,p],v)
# Exact literal PDF identity and original capture receipt, separate from any correction.
receipt_source=json.loads((CAP/'capture.json').read_bytes())
assert receipt_source['source_url']==receipt_source['response_url']=='https://statsdmz.nba.com/pdfs/20261104/20261104_DALSAS_book.pdf'
assert receipt_source['game_id']=='0022600184' and receipt_source['request_sha256']=='8ae14a5debf33fcdfbc99414d9a6efcc5a04501786cf922b379bcdd7966c771e'
assert receipt_source['http_status']==200 and receipt_source['attempts']==1 and receipt_source['redirects_followed']==0 and receipt_source['size_bytes']==len(pdf.read_bytes())==152520
assert receipt_source['sha256']==hashlib.sha256(pdf.read_bytes()).hexdigest() and int(receipt_source['response_headers']['Content-Length'])==152520
for page in range(20):
 txt=(PAGES/f'page-{page:02d}.txt').read_text();assert 'Wednesday, November 4, 2026' in txt and 'San Antonio' in txt
assert team_scorer['whole',away]['points']==111 and team_scorer['whole',home]['points']==112
changes=[];scorer_cells=0
with ZipFile(ROOT/'working/nba-tools-completion-program/source-evidence/current123-periods-20261107/collection.zip') as original:
 for tag in ('q1','q2','q3','q4','h1','h2'):
  document=json.loads(original.read(f'sources/boxscoretraditionalv3_0022600184_{tag}.json'))['boxScoreTraditional']
  for side in ('awayTeam','homeTeam'):
   team=document[side];tid=team['teamId']
   for field in score_fields:
    before=team['statistics'][field];after=team_scorer[tag,tid][field];scorer_cells+=1
    if before!=after:changes.append({'dataset':'team','game_id':22600184,'window':tag,'team_id':tid,'field':field,'before':before,'after':after})
   for person in team['players']:
    pid=person['personId'];expected=scorer.get((tag,tid,pid))
    if expected is None:
     assert person['statistics']['minutes']=='0:00' and all(person['statistics'][f]==0 for f in score_fields);continue
    for field in score_fields:
     before=person['statistics'][field];after=expected[field];scorer_cells+=1
     if before!=after:changes.append({'dataset':'player','game_id':22600184,'window':tag,'team_id':tid,'player_id':pid,'field':field,'before':before,'after':after})
assert len(changes)==8 and all(c['window'] in ('q2','h1') and c['team_id']==away and c['field'] in ('reboundsDefensive','reboundsTotal') and c['after']==c['before']+1 for c in changes)
assert all(c.get('player_id',1629023)==1629023 for c in changes)

output=[]
for tag,qs in [('q2',[2]),('h1',[1,2])]:
 for (tg,tid,pid),v in scorer.items():
  if tg!=tag:continue
  n=sum(rebcounts[q,tid,pid] for q in qs);den=sum(chances[q,tid,pid] for q in qs)
  assert n==v['reb'] and den>0
  output.append({'game_id':22600184,'window':tag,'team_id':tid,'player_id':pid,'numerator':n,'denominator':den,'exact':str(Fraction(n,den)),'reb_pct':float(Fraction(n,den))})
assert len(output)==38
# Use strings for all fractions in the durable literal proof.
def encode(value):
 if isinstance(value,Fraction):return str(value)
 raise TypeError(type(value).__name__)
receipt={'pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'qualified_reb_pct_cells':38,'count_corrections':changes,'scorer_numeric_cells_compared':scorer_cells,'scorer_rows':[{"window":tg,"team_id":t,"player_id":p,**v} for (tg,t,p),v in scorer.items()],'team_scorer_rows':[{"window":tg,"team_id":t,**v} for (tg,t),v in team_scorer.items()],'rates':output,'rebound_events':rebounds,'substitutions':substitutions,'period_player_clock_seconds':{q:{f'{t}/{p}':str(s) for (t,p),s in v.items()} for q,v in clocks.items()},'live_rebound_events_by_period':{q:sum(not r['dead_ball'] for r in rebounds if r['period']==q) for q in (1,2)},'nba_requests_executed':0,'production_writes':0}
(OUT/'book-rebound-oracle.json').write_text(json.dumps(receipt,indent=2,default=encode)+'\n');print(json.dumps({'rates':output,'live_rebound_events_by_period':receipt['live_rebound_events_by_period']},indent=2))
