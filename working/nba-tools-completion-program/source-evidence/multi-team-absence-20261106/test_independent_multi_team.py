"""Independent controlled populations; no real NBA memberships are asserted."""
import hashlib
import shutil
from pathlib import Path

import pandas as pd
import pytest

from nbatools.data_source import reset_data_source_cache
from nbatools.query_service import execute_natural_query, execute_structured_query

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]
SEASON = '2025-26'
PID = 1628369
NAME = 'Jayson Tatum'
IDS = {'BOS': 1610612738, 'DEN': 1610612743, 'GSW': 1610612744}

@pytest.fixture
def population(tmp_path, monkeypatch):
    root = tmp_path / 'independent-controlled'
    shutil.copytree('qa/fixtures/query_engine_sample', root)
    monkeypatch.setenv('DATA_SOURCE', 'local')
    monkeypatch.setenv('NBATOOLS_DATA_ROOT', str(root))
    suffix = f'{SEASON}_regular_season.csv'
    teams = pd.read_csv(root/'data/raw/team_game_stats'/suffix)
    path = root/'data/raw/player_game_stats'/suffix
    original_players = pd.read_csv(path)
    template = original_players.loc[original_players.player_id.eq(PID)].iloc[0].to_dict()
    source = b'INDEPENDENT CONTROLLED FIXTURE ONLY: no NBA tenure assertion'
    digest = hashlib.sha256(source).hexdigest()
    sourcepath = root/'data/raw/player_team_membership_sources'/f'{digest}.source'
    sourcepath.parent.mkdir(parents=True, exist_ok=True)
    sourcepath.write_bytes(source)
    def write(intervals, missed, absent_observations=()):
        records, appearances = [], []
        memberships = []
        for club, first, last in intervals:
            memberships.append(dict(season=SEASON,player_id=PID,player_name=NAME,
                team_id=IDS[club],start_date=first,end_date=last,membership_state='member',
                coverage_scope='explicit_dated_nba_membership',
                source='https://www.nba.com/independent-controlled-fixture',source_sha256=digest))
            for row in teams.loc[teams.team_abbr.eq(club) & teams.game_date.between(first,last)].to_dict('records'):
                item = template | {key:value for key,value in row.items() if key in template}
                item['minutes'] = 24
                gid = int(item['game_id'])
                if gid not in absent_observations:
                    records.append(item | dict(participation_state='did_not_play' if gid in missed else 'played',
                        coverage_scope='listed_player_rows_only', source='nba_official_finalbox:20251116_BOSDEN', source_sha256='a'*64))
                    if gid not in missed:
                        appearances.append(item)
        pd.concat([original_players.loc[~original_players.player_id.eq(PID)],pd.DataFrame(appearances)]).to_csv(path,index=False)
        apath = root/'data/raw/player_game_availability'/suffix
        apath.parent.mkdir(parents=True,exist_ok=True)
        pd.DataFrame(records).to_csv(apath,index=False)
        mpath = root/'data/raw/player_team_membership'/f'{SEASON}.csv'
        mpath.parent.mkdir(parents=True,exist_ok=True)
        pd.DataFrame(memberships).to_csv(mpath,index=False)
        reset_data_source_cache()
    yield root, teams, write
    reset_data_source_cache()

THREE = [('BOS','2025-10-01','2025-11-15'),('DEN','2025-11-16','2025-12-31'),('GSW','2026-01-01','2026-10-31')]
MISSED = {368,373,374,383,397}

def ids(result):
    return {int(row['game_id']) for row in result.result.to_dict().get('sections',{}).get('finder',[])}

def coverage(result):
    return result.result.metadata['membership_coverage']

def test_three_club_exact_ids_and_arithmetic(population):
    root, teams, write = population
    write(THREE, MISSED)
    result = execute_natural_query('How many games did Jayson Tatum miss in 2025-26?')
    assert result.result_status == 'ok', result.metadata
    assert ids(result) == MISSED
    assert result.result.to_dict()['sections']['count'] == [{'count':5}]
    assert 'NBA' in result.metadata['answer_phrase']
    c = coverage(result)
    counts = {r['team_abbr']:r['did_not_play'] for r in c['by_team']}
    assert counts == {'BOS':2,'DEN':2,'GSW':1}
    assert c['complete'] and c['missed_games']==5
    assert sum(r['played']+r['did_not_play']+r['not_member']+r['unknown'] for r in c['by_team']) == len(c['games'])
    for r in c['games']:
        if r['team_abbr']=='BOS' and r['game_date']>'2025-11-15':
            assert r['participation_state']=='not_member'
        if r['team_abbr']=='DEN' and r['game_date']<'2025-11-16':
            assert r['participation_state']=='not_member'

@pytest.mark.parametrize('kwargs,expected',[
    ({'team':'DEN'}, {374,383}),
    ({'opponent':'DEN'}, {373,397}),
    ({'home_only':True}, {374,397}),
    ({'away_only':True}, {368,373,383}),
    ({'start_date':'2025-11-16','end_date':'2025-12-31'}, {374,383}),
    ({'stat':'pts','min_value':80}, {373,397}),
])
def test_independent_filters_actual_ids(population,kwargs,expected):
    _, _, write=population
    write(THREE,MISSED)
    r=execute_structured_query('game_finder',season=SEASON,membership_player=NAME,limit=1000,**kwargs)
    assert r.result_status=='ok',r.metadata
    assert ids(r)==expected
    assert coverage(r)['missed_games']==len(expected)

def test_zero_appearance_original_club_still_counted(population):
    _, _, write=population
    write([THREE[0],('DEN','2025-11-16','2026-10-31')],{363,368,373})
    r=execute_natural_query('How many games did Jayson Tatum miss in 2025-26?')
    assert r.result_status=='ok',r.metadata
    assert ids(r)=={363,368,373}
    assert r.result.to_dict()['sections']['count']==[{'count':3}]
    assert 'NBA' in r.metadata['answer_phrase']
    assert {x['team_abbr']:x['did_not_play'] for x in coverage(r)['by_team']}=={'BOS':3,'DEN':0}

def test_unknown_participation_keeps_required_id_and_withholds_total(population):
    _, _, write=population
    write(THREE,MISSED,absent_observations={374})
    r=execute_natural_query('How many games did Jayson Tatum miss in 2025-26?')
    assert r.result_status=='no_result' and r.result_reason=='no_data',r.metadata
    c=coverage(r)
    assert c['missed_games'] is None and c['verified_missed_games']==4
    assert any(x['game_id']==374 and x['participation_state']=='unknown' for x in c['games'])
    assert sum(x['unknown'] for x in c['by_team'])==1

def test_unknown_membership_transition_keeps_required_game(population):
    root, _, write=population
    write(THREE,MISSED,absent_observations={374})
    p=root/f'data/raw/player_team_membership/{SEASON}.csv'
    rows=pd.read_csv(p)
    rows.loc[rows.team_id.eq(IDS['DEN']),'start_date']='2025-11-17'
    rows.to_csv(p,index=False)
    reset_data_source_cache()
    r=execute_natural_query('How many games did Jayson Tatum miss in 2025-26?')
    assert r.result_status=='no_result',r.metadata
    c=coverage(r)
    assert c['missed_games'] is None and '2025-11-16' in c['unknown_membership_dates']
    assert any(x['game_id']==374 and x['participation_state']=='unknown' for x in c['games'])

def test_single_club_retained(population):
    _, _, write=population
    write([('BOS','2025-10-01','2026-10-31')],{368,373})
    r=execute_natural_query('How many games did Jayson Tatum miss in 2025-26?')
    assert r.result_status=='ok',r.metadata
    assert ids(r)=={368,373}
    assert r.result.to_dict()['sections']['count']==[{'count':2}]
    assert 'Boston Celtics' in r.metadata['answer_phrase']

@pytest.mark.parametrize('question',[
    'How many games did Jayson Tatum miss in 2025-26 when his team scored at least 80 points?',
    'How many games did Jayson Tatum miss in 2025-26 with 80+ team points?',
])
def test_natural_team_stat_preserves_missed_subject(population,question):
    _, _, write=population
    write(THREE,MISSED)
    r=execute_natural_query(question)
    assert r.result_status=='ok',r.metadata
    assert ids(r)=={373,397}
    assert r.result.to_dict()['sections']['count']==[{'count':2}]
    assert r.metadata['route']=='game_finder'
