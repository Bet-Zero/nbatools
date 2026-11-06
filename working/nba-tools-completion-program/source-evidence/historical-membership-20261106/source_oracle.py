"""Independent listed-row oracle from immutable retained originals, no engine imports."""
import collections
import hashlib
import json
from pathlib import Path
import subprocess

REVISION = 'b835874e7c31dc29c38d62fcda263af404c881fe'
PREFIX = 'working/nba-tools-completion-program/source-evidence/k08-tatum-2023/'

def original(path):
    return subprocess.check_output(['git', 'show', REVISION + ':' + PREFIX + path])

def facts():
    manifest = json.loads(original('sources.json'))
    cells = {}
    source_hashes = {}
    games = {}
    for name, meta in manifest['files'].items():
        raw = original('sources/' + name)
        assert len(raw) == meta['size_bytes']
        assert hashlib.sha256(raw).hexdigest() == meta['sha256']
        assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == meta['git_blob_sha']
        source_hashes[name] = meta['sha256']
    for name in sorted(manifest['files']):
        if not name.startswith('boxscoresummaryv2_'):
            continue
        s = json.loads(original('sources/' + name))
        tables = {t['name']: [dict(zip(t['headers'], row)) for row in t['rowSet']] for t in s['resultSets']}
        game = tables['GameSummary'][0]
        gid = str(game['GAME_ID'])
        date = game['GAME_DATE_EST'][:10]
        assert game['GAME_STATUS_ID'] == 3
        sides = {int(game['HOME_TEAM_ID']), int(game['VISITOR_TEAM_ID'])}
        score = {int(r['TEAM_ID']): int(r['PTS']) for r in tables['LineScore']}
        trad = json.loads(original('sources/boxscoretraditionalv3_' + gid + '.json'))['boxScoreTraditional']
        assert str(trad['gameId']) == gid
        assert {int(trad['homeTeamId']),int(trad['awayTeamId'])} == sides
        games[gid] = {'date':date, 'home':int(game['HOME_TEAM_ID']), 'away':int(game['VISITOR_TEAM_ID']), 'score':score}
        for side in ('homeTeam','awayTeam'):
            team = trad[side]
            tid = int(team['teamId'])
            assert int(team['statistics']['points']) == score[tid]
            for row in team['players']:
                clock = row['statistics']['minutes']
                seconds = sum(int(v) * n for v,n in zip(clock.split(':'), (60,1))) if clock else None
                if seconds and seconds > 0:
                    assert not row['comment']
                    state = 'played'
                else:
                    assert row['comment'] in ("DNP - Coach's Decision", 'DND - Injury/Illness')
                    state = 'did_not_play'
                key = (gid, tid, int(row['personId']))
                assert key not in cells
                cells[key] = {'date':date, 'state':state, 'player_name':row['firstName']+' '+row['familyName'], 'points':row['statistics']['points'] if state=='played' else None}
        for row in tables['InactivePlayers']:
            tid = int(row['TEAM_ID'])
            assert tid in sides
            key = (gid, tid, int(row['PLAYER_ID']))
            assert key not in cells or cells[key]['state'] == 'did_not_play'
            cells[key] = {'date':date, 'state':'did_not_play','player_name':row['FIRST_NAME']+' '+row['LAST_NAME'],'points':None}
    return cells, games, source_hashes

if __name__ == '__main__':
    cells, games, sources = facts()
    counts = dict(collections.Counter(v['state'] for v in cells.values()))
    summary = {'revision':REVISION, 'original_files':len(sources), 'game_count':len(games), 'cells':len(cells),'states':counts,'source_hashes':sources, 'classification':'independent_original_listed_fact_checks_not_season_tenure_or_canonical_acceptance'}
    assert counts == {'played':173,'did_not_play':105}
    assert len(cells)==278
    Path('work/membership-review/original-source-receipt.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k!='source_hashes'},indent=2))
