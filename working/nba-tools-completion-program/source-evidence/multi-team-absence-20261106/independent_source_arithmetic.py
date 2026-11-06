"""Replay retained originals directly; do not use application loaders/classifiers."""
import hashlib
import json
from pathlib import Path

ROOT = Path('work/multi-team/poeltl-originals')
OUT = Path('work/multi-team-review/independent-source-arithmetic.json')
PID = 1627751
SAS, TOR = 1610612759, 1610612761

def read(path): return json.loads(path.read_text())
def table(doc,name=None):
    sets=doc['resultSets']
    row=next(s for s in sets if name is None or s['name']==name)
    return [dict(zip(row['headers'],values,strict=True)) for values in row['rowSet']]

def verify(path,receipt):
    raw=path.read_bytes()
    assert len(raw)==receipt['bytes']
    assert hashlib.sha256(raw).hexdigest()==receipt['sha256']
    if 'git_blob_sha' in receipt:
        assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==receipt['git_blob_sha']

receipt=read(ROOT/'receipt.json')
for family in ('teams','players'):verify(ROOT/f'{family}.json',receipt[family])
for name,item in read(ROOT/'pairs/receipt.json').items():verify(ROOT/'pairs'/name,item)
teamrows=[r for r in table(read(ROOT/'teams.json')) if r['SEASON_ID']=='22022' and str(r['GAME_ID']).startswith('00222')]
assert len(teamrows)==2460
assert len({(r['GAME_ID'],r['TEAM_ID']) for r in teamrows})==2460
assert all(sum(r['TEAM_ID']==club for r in teamrows)==82 for club in {r['TEAM_ID'] for r in teamrows})
for gid in {r['GAME_ID'] for r in teamrows}:
    pair=[r for r in teamrows if r['GAME_ID']==gid]
    assert len(pair)==2 and pair[0]['GAME_DATE']==pair[1]['GAME_DATE']
    assert set(r['WL'] for r in pair)=={'W','L'}
    # No broad statistical qualification outside the selected player population.

eligible=[r for r in teamrows if (r['TEAM_ID']==SAS and r['GAME_DATE']<='2023-02-08') or (r['TEAM_ID']==TOR and r['GAME_DATE']>='2023-02-10')]
assert len(eligible)==81
statistical_failures=[]
for r in eligible:
    other=next(x for x in teamrows if x['GAME_ID']==r['GAME_ID'] and x['TEAM_ID']!=r['TEAM_ID'])
    if r['PTS']-other['PTS']!=r['PLUS_MINUS']:
        statistical_failures.append(dict(game_id=r['GAME_ID'],team=r['TEAM_ABBREVIATION'],pts=r['PTS'],opponent_pts=other['PTS'],reported_plus_minus=r['PLUS_MINUS'],computed_margin=r['PTS']-other['PTS']))
assert statistical_failures==[dict(game_id='0022200138',team='SAS',pts=101,opponent_pts=126,reported_plus_minus=-20.0,computed_margin=-25)]
assert sum(r['TEAM_ID']==SAS for r in eligible)==55
assert sum(r['TEAM_ID']==TOR for r in eligible)==26
assert not any(r['TEAM_ID'] in (SAS,TOR) and r['GAME_DATE']=='2023-02-09' for r in teamrows)
players=[r for r in table(read(ROOT/'players.json')) if r['PLAYER_ID']==PID and r['SEASON_ID']=='22022']
assert len(players)==72 and len({r['GAME_ID'] for r in players})==72
assert sum(r['TEAM_ID']==SAS for r in players)==46 and sum(r['TEAM_ID']==TOR for r in players)==26
assert all(float(r['MIN'])>0 for r in players)
played={(r['GAME_ID'],r['TEAM_ID']) for r in players}
assert played <= {(r['GAME_ID'],r['TEAM_ID']) for r in eligible}
missed=sorted([r for r in eligible if (r['GAME_ID'],r['TEAM_ID']) not in played],key=lambda r:r['GAME_DATE'])
assert len(missed)==9
assert {r['GAME_ID'] for r in missed}=={'0022200247','0022200319','0022200333','0022200345','0022200375','0022200387','0022200406','0022200420','0022200591'}
for row in missed:
    gid=row['GAME_ID']; summary=read(ROOT/f'pairs/boxscoresummaryv2_{gid}.json')
    identity=table(summary,'GameSummary'); assert len(identity)==1
    assert identity[0]['GAME_ID']==gid and identity[0]['GAME_STATUS_ID']==3
    assert identity[0]['GAME_DATE_EST'].startswith(row['GAME_DATE'])
    inactive=[r for r in table(summary,'InactivePlayers') if r['PLAYER_ID']==PID]
    assert len(inactive)==1 and inactive[0]['TEAM_ID']==SAS
    traditional=read(ROOT/f'pairs/boxscoretraditionalv3_{gid}.json')['boxScoreTraditional']
    assert traditional['gameId']==gid and SAS in (traditional['homeTeamId'],traditional['awayTeamId'])
    own=next(traditional[side] for side in ('homeTeam','awayTeam') if traditional[side]['teamId']==SAS)
    stat=own['statistics']
    summary_own=next(x for x in table(summary,'LineScore') if x['TEAM_ID']==SAS)
    assert row['PTS']==stat['points']==summary_own['PTS']
    assert stat['points']==2*stat['fieldGoalsMade']+stat['threePointersMade']+stat['freeThrowsMade']
    assert stat['points']==sum(p['statistics']['points'] for p in own['players'])
    assert summary_own['PTS']==sum(summary_own[key] for key in summary_own if key.startswith('PTS_QTR') or key.startswith('PTS_OT'))
    positive=[p for side in ('homeTeam','awayTeam') for p in traditional[side]['players'] if p['personId']==PID]
    assert not any(p['statistics'].get('minutes') not in ('',None,'0:00','00:00') for p in positive)

facts=[{key:r[key] for key in ('GAME_ID','GAME_DATE','TEAM_ABBREVIATION','MATCHUP','WL','PTS')} for r in missed]
report=dict(review='independent standard-library replay of retained source bytes; membership dates require separate official tenure qualification',
    input_hashes={k:v['sha256'] for k,v in receipt.items() if isinstance(v,dict)},
    initial_statistical_validation_failures=statistical_failures,
    population=dict(league_team_rows=2460,league_games=1230,candidate_club_rows=164,eligible_games=81,played=72,explicit_inactive=9,excluded_club_games=83,
    SAS=dict(eligible=55,played=46,missed=9),TOR=dict(eligible=26,played=26,missed=0)),
    missed_games=facts,
    eligible_ids_by_team={club:sorted(r['GAME_ID'] for r in eligible if r['TEAM_ABBREVIATION']==club) for club in ('SAS','TOR')},
    filtered_ids=dict(home=[r['GAME_ID'] for r in missed if ' vs. ' in r['MATCHUP']],away=[r['GAME_ID'] for r in missed if ' @ ' in r['MATCHUP']],
        november=[r['GAME_ID'] for r in missed if r['GAME_DATE'].startswith('2022-11')],december=[r['GAME_ID'] for r in missed if r['GAME_DATE'].startswith('2022-12')],
        january=[r['GAME_ID'] for r in missed if r['GAME_DATE'].startswith('2023-01')],pts_at_least_110=[r['GAME_ID'] for r in missed if r['PTS']>=110],
        against_lakers=[r['GAME_ID'] for r in missed if r['MATCHUP'].endswith('LAL')]),
    missed_game_team_arithmetic=dict(wins=sum(r['WL']=='W' for r in missed),losses=sum(r['WL']=='L' for r in missed),pts=sum(r['PTS'] for r in missed),ppg=sum(r['PTS'] for r in missed)/len(missed)))
OUT.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
