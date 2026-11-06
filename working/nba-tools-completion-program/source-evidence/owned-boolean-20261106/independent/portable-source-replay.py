"""Independent raw-row ownership oracle; stdlib only, no application imports."""
import argparse,collections,csv,hashlib,json,pathlib,subprocess,sys,zipfile
P=pathlib.Path(__file__).resolve().parent;ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--repo',type=pathlib.Path,default=P/'baseline');ap.add_argument('--output',type=pathlib.Path,default=P);a=ap.parse_args();R=a.repo.resolve();O=a.output.resolve();O.mkdir(parents=True,exist_ok=True)
prior=R/'working/nba-tools-completion-program/source-evidence/distinct-player-or-20261106/independent';original=json.loads((prior/'oracle.json').read_text());assert hashlib.sha256((prior/'oracle.json').read_bytes()).hexdigest()=='9915885cc7afa1ba96cb47e8d38aa621c808a41ed3146b6c35ad96aeb596afd6'
subprocess.run([sys.executable,str(prior/'portable-source-replay.py'),'--repo',str(R),'--output',str(O/'prior-replay')],check=True,stdout=subprocess.DEVNULL)
assert hashlib.sha256((O/'prior-replay/oracle.json').read_bytes()).hexdigest()=='9915885cc7afa1ba96cb47e8d38aa621c808a41ed3146b6c35ad96aeb596afd6'
F=O/'prior-replay/controlled';stats=['pts','reb','ast','tov','fg3m','fg3a','fgm','fga','ftm','fta','oreb','dreb','stl','blk','pf','plus_minus']
def read_csv(p):return list(csv.DictReader(p.open()))
def normalize(r):
 r=r.copy()
 for k in ['game_id','team_id','player_id','opponent_team_id']:
  if k in r:r[k]=int(r[k])
 for s in stats:
  if s in r:r[s]=float(r[s])
 return r
cp=[normalize(r) for r in read_csv(F/'data/raw/player_game_stats/2025-26_regular_season.csv')];ct=[normalize(r) for r in read_csv(F/'data/raw/team_game_stats/2025-26_regular_season.csv')]
archive=R/'working/nba-tools-completion-program/source-evidence/multi-team-absence-20261106/archive-originals.zip';assert hashlib.sha256(archive.read_bytes()).hexdigest()=='6e4b06650519da0b9bfc46269fff5e4f0c231949d8922585e7f4590fbac9d6a1'
with zipfile.ZipFile(archive) as z:
 def table(file,name):
  s=next(r for r in json.loads(z.read(file))['resultSets'] if r['name']==name);return [dict(zip(s['headers'],r)) for r in s['rowSet']]
 np=[normalize({k.lower():v for k,v in r.items()}) for r in table('players.json','LeagueGameLog')];nt=[normalize({k.lower():v for k,v in r.items()}) for r in table('teams.json','LeagueGameFinderResults') if r['SEASON_ID']=='22022' and r['GAME_ID'].startswith('002')]
 for r in np+nt:r['team_abbr']=r['team_abbreviation'];r['is_home']=' vs. ' in r['matchup']
 assert len(np)==25895 and len(nt)==2460

def join(players,teams):
 lookup={(r['game_id'],r['team_id']):r for r in teams};bygame=collections.defaultdict(list)
 assert len(lookup)==len(teams)
 for t in teams:bygame[t['game_id']].append(t)
 assert all(len(ts)==2 and len({t['team_id'] for t in ts})==2 for ts in bygame.values())
 for p in players:
  own=lookup[(p['game_id'],p['team_id'])];opp=next(t for t in bygame[p['game_id']] if t['team_id']!=p['team_id']);assert p['game_date']==own['game_date']==opp['game_date']
  p['opponent_team_abbr']=opp['team_abbr'];p['is_home']=str(own['is_home']) in ['True','1'];p['wl']=own['wl']
  for stat in stats:p['team_'+stat]=own[stat];p['opponent_'+stat]=opp[stat]
 return players
cp=join(cp,ct);np=join(np,nt)
def facts(rows,pred,scope=lambda r:True):
 selected=[r for r in rows if scope(r) and pred(r)];occ=collections.Counter(r['player_id'] for r in selected)
 return {'keys':sorted((r['game_id'],r['team_id'],r['player_id']) for r in selected),'player_games':len(selected),'nba_games':len({r['game_id'] for r in selected}),'distinct_players':len(occ),'player_ids':sorted(occ),'occurrences':sorted(occ.items()),'wins':sum(r['wl']=='W' for r in selected),'losses':sum(r['wl']=='L' for r in selected),'sums':{s:sum(r[s] for r in selected) for s in ['pts','reb','ast','tov','team_pts','opponent_pts']},'means':{s:sum(r[s] for r in selected)/len(selected) if selected else None for s in ['pts','reb','ast','tov']}}
base=lambda r:r['pts']>20 or r['ast']>10
cases={
 'carry_controlled_team_owned':facts(cp,lambda r:base(r) and r['team_pts']==100),
 'c_player_or_team':facts(cp,lambda r:r['pts']>20 or r['team_pts']==100),
 'c_player_or_opponent':facts(cp,lambda r:r['pts']>20 or r['opponent_pts']==100),
 'c_nested_owners':facts(cp,lambda r:(r['pts']>20 and r['team_pts']==100) or(r['ast']>10 and r['opponent_pts']==100)),
 'c_outer_opponent':facts(cp,lambda r:base(r) and r['opponent_pts']==100),
 'c_both_owner_or':facts(cp,lambda r:(r['team_pts']==100 or r['opponent_pts']==100) and r['pts']>=20),
 'c_team_exact_zero':facts(cp,lambda r:r['team_pts']==0 or r['pts']>90),
 'c_scoped_den':facts(cp,lambda r:r['pts']>20 or r['team_pts']==100,scope=lambda r:r['team_abbr']=='DEN'),
 'c_scoped_opponent':facts(cp,lambda r:r['pts']>20 or r['team_pts']==100,scope=lambda r:r['opponent_team_abbr']=='GSW'),
 'c_strict_team':facts(cp,lambda r:r['pts']>20 or r['team_pts']>100),
 'c_inclusive_team':facts(cp,lambda r:r['pts']>20 or r['team_pts']>=100),
 'carry_native_team_owned':facts(np,lambda r:(r['pts']>37 or r['ast']>10) and r['team_pts']>=125),
 'carry_native_opponent_owned':facts(np,lambda r:(r['pts']>37 or r['ast']>10) and r['opponent_pts']<110),
 'n_player_or_team':facts(np,lambda r:r['pts']>37 or r['team_pts']>=125),
 'n_player_or_opponent':facts(np,lambda r:r['pts']>37 or r['opponent_pts']<100),
 'n_nested_owners':facts(np,lambda r:(r['pts']>37 and r['team_ast']>=30) or(r['reb']>=12 and r['opponent_pts']<=100)),
 'n_equality_mixed':facts(np,lambda r:(r['pts']==29 or r['team_ast']==30) and r['opponent_tov']==12),
 'n_team_threes_outer':facts(np,lambda r:(r['pts']>37 or r['ast']>10) and r['team_fg3m']>=18),
 'n_scoped_gsw':facts(np,lambda r:(r['reb']>=12 or r['team_pts']==113) and r['opponent_pts']>=110,scope=lambda r:r['team_abbr']=='GSW'),
 'n_curry_threes':facts(np,lambda r:r['fg3m']==5 or r['team_ast']>=33,scope=lambda r:r['player_id']==201939),
 'n_looney_reb':facts(np,lambda r:(r['pts']>10 or r['ast']>=4) and r['team_reb']>=50,scope=lambda r:r['player_id']==1626172),
 'n_poeltl_team':facts(np,lambda r:r['reb']>=12 or r['team_pts']==110,scope=lambda r:r['player_id']==1627751),
 'n_known_zero':facts(np,lambda r:r['pts']>100 or r['team_pts']>300),
 'n_zero_team_tov_or_player':facts(np,lambda r:r['team_tov']==0 or r['pts']==0),
 'n_team_tov_floor_or_player':facts(np,lambda r:r['team_tov']>=0 or r['pts']==0),
}
for new,old in [('carry_controlled_team_owned','controlled_team_owned'),('carry_native_team_owned','native_team_owned'),('carry_native_opponent_owned','native_opponent_owned')]:
 c=cases[new];prev=original['cases'][old];assert set(map(tuple,c['keys']))==set(map(tuple,prev['selected_keys'])) and c['player_games']==prev['player_games'] and c['distinct_players']==prev['distinct_players']
sources={'prior_oracle_sha256':'9915885cc7afa1ba96cb47e8d38aa621c808a41ed3146b6c35ad96aeb596afd6','native_archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}
oracle={'baseline':'b6edb9e3b14268c92bfab91fec4129252bfb94b7','checker':'/root/poeltl_source_checker; independent Codex session, exact backend model not exposed','sources':sources,'controlled_root':'prior-replay/controlled','meaning':'Each leaf retains player/team/opponent owner and grouping; all owner values join exact same(game_id,team_id) canonical team rows, opponent is the other club. Owner labels must survive inside OR branches versus outside AND. Filter one scoped base before evaluating rowwise; project playerID only after union. Exact/zero/floor/strict bounds unchanged; missing or conflicting required context cannot become false/zero/partial total.','carry_forward_original_ids':['controlled_team_owned','native_team_owned','native_opponent_owned'],'cases':cases}
(O/'oracle.json').write_text(json.dumps(oracle,indent=2)+'\n');print('ORACLE_SHA',hashlib.sha256((O/'oracle.json').read_bytes()).hexdigest())
for k,c in cases.items():print(k,c['player_games'],c['nba_games'],c['distinct_players'])
