"""Independent accepted-original-byte expectations; imports no app/loader code."""
import copy, hashlib, json
from pathlib import Path
from fractions import Fraction

ROOT=Path('/workspace/nbatools')
E=ROOT/'working/nba-tools-completion-program/source-evidence/current123-periods-20261107'
def read(name, expected):
    raw=(E/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==expected
    return json.loads(raw)
raw=read('independent-oracle.json','59fd69280de504dc656611988f074b49eeecb35e1830d1cbbb0db07f9e1bec1a')
book=read('independent-book-rebound-oracle.json','7d054703091f5f0334d2b01dd7bd978e619d2e36a11eead390fdb23cf0646698')
rows=copy.deepcopy(raw['canonical_player_rows'])
for change in book['count_corrections']:
    if change['dataset']!='player':continue
    target=[r for r in rows if (r['game_id'],r['team_id'],r['player_id'],r['window'])==(change['game_id'],change['team_id'],change['player_id'],change['window'])]
    assert len(target)==1
    field={'reboundsDefensive':'dreb','reboundsTotal':'reb'}[change['field']]
    assert target[0][field]==change['before'];target[0][field]=change['after']
for fact in book['rates']:
    target=[r for r in rows if (r['game_id'],r['team_id'],r['player_id'],r['window'])==(fact['game_id'],fact['team_id'],fact['player_id'],fact['window'])]
    assert len(target)==1
    target[0]['reb_pct']=float(Fraction(fact['numerator'],fact['denominator']))
keys=[(1630559,22600185,'q2'),(1630559,22600185,'h1'),(1629023,22600184,'q2'),(1629023,22600184,'h1'),(1641750,22600176,'q2'),(1642863,22600183,'h1'),(1630180,22600179,'ot'),(1629636,22600186,'ot')]
selected=[]
for key in keys:
    found=[r for r in rows if (r['player_id'],r['game_id'],r['window'])==key];assert len(found)==1
    selected.append(found[0])
# One aggregate spans all source-derived 16-new game rows, useful to detect
# accidental row/sample changes without importing expected values from a CSV.
aggregates=[]
for pid in [1630559,1629023,1630180,1629636]:
    for window in ['q1','q2','h1','ot']:
        sample=[r for r in rows if r['player_id']==pid and r['window']==window]
        if not sample:continue
        sums={f:sum(r[f] for r in sample) for f in ['pts','reb','ast','fgm','fga','fg3m','fg3a','ftm','fta','minutes']}
        denominator=2*(sums['fga']+0.44*sums['fta'])
        aggregates.append(dict(player_id=pid,window=window,game_ids=sorted(r['game_id'] for r in sample),games=len(sample),sums=sums,
            averages={f:sums[f]/len(sample) for f in ['pts','reb','ast','minutes']},
            ts_pct=sums['pts']/denominator if denominator else None,
            efg_pct=(sums['fgm']+0.5*sums['fg3m'])/sums['fga'] if sums['fga'] else None))
ledger=ROOT/'working/nba-tools-completion-program/source-evidence/rollover-2026-27/official-gamebooks-20261105/remaining-dependencies.json'
unknown=json.loads(ledger.read_bytes())['unknown_rates'];assert len(unknown)==484
result=dict(source_oracle_sha256=hashlib.sha256((E/'independent-oracle.json').read_bytes()).hexdigest(),book_oracle_sha256=hashlib.sha256((E/'independent-book-rebound-oracle.json').read_bytes()).hexdigest(),
    accepted_snapshot='535384a4710739a779f0772da4e3bcee023bd88bfed91be16d0103cdf9d8ff75',derived_from_app=False,selected_rows=selected,finite_new16_aggregates=aggregates,
    known_unknown_count=484,known_unknown_fields=sorted({r['field'] for r in unknown}),negative_witnesses=[r for r in unknown if r['player_id']==201142][:8],source_fetches=0,production_writes=0)
output=ROOT/'work/period-dependency-independent/source-oracles.json';output.write_text(json.dumps(result,indent=2)+'\n')
print(hashlib.sha256(output.read_bytes()).hexdigest())
print([(r['player_name'],r['game_id'],r['window'],r['pts'],r['reb'],r['ast']) for r in selected])
