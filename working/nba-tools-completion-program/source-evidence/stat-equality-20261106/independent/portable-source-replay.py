"""Independent equality oracle: stdlib raw CSV/JSON selection, no runtime imports."""
import argparse,collections,csv,hashlib,json,pathlib,zipfile
SCRIPT=pathlib.Path(__file__).resolve()
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--repo',type=pathlib.Path,default=pathlib.Path.cwd())
parser.add_argument('--output',type=pathlib.Path,default=SCRIPT.parent/'source-replay')
args=parser.parse_args()
BASE=args.output.resolve();BASE.mkdir(parents=True,exist_ok=True)
REPO=args.repo.resolve()
FIX=REPO/'qa/fixtures/query_engine_sample/data/raw'
def csvrows(family,season='2025-26'):
 return list(csv.DictReader((FIX/family/(season+'_regular_season.csv')).open()))
def num(x):return float(x)
fp=csvrows('player_game_stats');ft=csvrows('team_game_stats')
for r in fp+ft:
 for k in ['game_id','team_id','player_id','opponent_team_id','is_home','is_away']:
  if k in r:r[k]=int(r[k]=='True') if r[k] in ['True','False'] else int(r[k])
 for k in ['pts','reb','ast','stl','blk','tov','fgm','fga','fg3m','fg3a','ftm','fta','minutes','plus_minus']:r[k]=num(r[k])
teammap={(r['game_id'],r['team_id']):r for r in ft}
for r in fp+ft:
 own=teammap[(r['game_id'],r['team_id'])];opp=teammap[(r['game_id'],r['opponent_team_id'])]
 for stat in ['pts','reb','ast','tov','fg3m']:
  r['team_'+stat]=own[stat];r['opponent_'+stat]=opp[stat]

def keys(rows):return [[r['game_id'],r['team_id'],r.get('player_id')] for r in sorted(rows,key=lambda r:(r['game_id'],r['team_id'],r.get('player_id',0))) ]
def calc(rows):
 return {'rows':len(rows),'nba_games':len({r['game_id'] for r in rows}),'players':len({r['player_id'] for r in rows if 'player_id' in r}),'wins':sum(r.get('wl',r.get('WL'))=='W' for r in rows),'losses':sum(r.get('wl',r.get('WL'))=='L' for r in rows),'keys':keys(rows),'sums':{s:sum(r[s] for r in rows) for s in ['pts','reb','ast','tov']},'means':{s:(sum(r[s] for r in rows)/len(rows) if rows else None) for s in ['pts','reb','ast','tov']}}
selectors=[
 ('fixture_ad_rebounds12',fp,lambda r:r['player_name']=='Anthony Davis' and r['reb']==12),
 ('fixture_curry_assists7',fp,lambda r:r['player_name']=='Stephen Curry' and r['ast']==7),
 ('fixture_tatum_points31',fp,lambda r:r['player_name']=='Jayson Tatum' and r['pts']==31),
 ('fixture_curry_fg3m4',fp,lambda r:r['player_name']=='Stephen Curry' and r['fg3m']==4),
 ('fixture_curry_tov0',fp,lambda r:r['player_name']=='Stephen Curry' and r['tov']==0),
 ('fixture_curry_tov0plus',fp,lambda r:r['player_name']=='Stephen Curry' and r['tov']>=0),
 ('fixture_curry_assists7_floor',fp,lambda r:r['player_name']=='Stephen Curry' and r['ast']>=7),
 ('fixture_curry_assists7_strictfloor',fp,lambda r:r['player_name']=='Stephen Curry' and r['ast']>7),
 ('fixture_curry_assists7_ceiling',fp,lambda r:r['player_name']=='Stephen Curry' and r['ast']<=7),
 ('fixture_curry_assists7_strictceiling',fp,lambda r:r['player_name']=='Stephen Curry' and r['ast']<7),
 ('fixture_curry_assists7_home',fp,lambda r:r['player_name']=='Stephen Curry' and r['ast']==7 and r['is_home']==1),
 ('fixture_curry_assists7_ownpts99',fp,lambda r:r['player_name']=='Stephen Curry' and r['ast']==7 and r['team_pts']>=99),
 ('fixture_league_pts27',fp,lambda r:r['pts']==27),
 ('fixture_league_pts27_ast5',fp,lambda r:r['pts']==27 and r['ast']>=5),
 ('fixture_team_pts102',ft,lambda r:r['pts']==102),
 ('fixture_team_opponentpts102',ft,lambda r:r['opponent_pts']==102),
 ('fixture_bos_pts102',ft,lambda r:r['team_abbr']=='BOS' and r['pts']==102),
 ('fixture_bos_opponentpts102',ft,lambda r:r['team_abbr']=='BOS' and r['opponent_pts']==102),
 ('fixture_player_teampts102',fp,lambda r:r['player_name']=='Stephen Curry' and r['team_pts']==102),
 ('fixture_player_opponentpts102',fp,lambda r:r['player_name']=='Stephen Curry' and r['opponent_pts']==102),
]
archive=REPO/'working/nba-tools-completion-program/source-evidence/multi-team-absence-20261106/archive-originals.zip'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='6e4b06650519da0b9bfc46269fff5e4f0c231949d8922585e7f4590fbac9d6a1'
with zipfile.ZipFile(archive) as z:
 def table(name,table):
  j=json.loads(z.read(name));t=next(r for r in j['resultSets'] if r['name']==table);return [dict(zip(t['headers'],r)) for r in t['rowSet']]
 teams=table('teams.json','LeagueGameFinderResults');teams=[r for r in teams if r['SEASON_ID']=='22022' and r['GAME_ID'].startswith('002')]
 players=table('players.json','LeagueGameLog')
 def normalize(r,player=False):
  d={k.lower():v for k,v in r.items()};d['game_id']=int(d['game_id']);d['season']='2022-23';d['is_home']=int(' vs. ' in d['matchup']);d['team_abbr']=d['team_abbreviation'];return d
 nt=[normalize(r) for r in teams];np=[normalize(r,True) for r in players]
 native_map={(r['game_id'],r['team_id']):r for r in nt}
 game_to_teams=collections.defaultdict(list)
 for r in nt:game_to_teams[r['game_id']].append(r)
 assert len(nt)==2460 and len(np)==25895 and len(game_to_teams)==1230
 for r in nt+np:
  own=native_map[(r['game_id'],r['team_id'])];opp=next(t for t in game_to_teams[r['game_id']] if t['team_id']!=r['team_id'])
  for stat in ['pts','reb','ast','tov','fg3m']:r['team_'+stat]=own[stat];r['opponent_'+stat]=opp[stat]
 selectors += [
 ('nba_looney_reb7',np,lambda r:r['player_id']==1626172 and r['reb']==7),
 ('nba_looney_reb7_teampts113',np,lambda r:r['player_id']==1626172 and r['reb']==7 and r['team_pts']==113),
 ('nba_curry_fg3m5',np,lambda r:r['player_id']==201939 and r['fg3m']==5),
 ('nba_curry_ast8',np,lambda r:r['player_id']==201939 and r['ast']==8),
 ('nba_gsw_pts113',nt,lambda r:r['team_abbr']=='GSW' and r['pts']==113),
 ('nba_gsw_opponentpts117',nt,lambda r:r['team_abbr']=='GSW' and r['opponent_pts']==117),
 ('nba_league_pts27',np,lambda r:r['pts']==27),
 ('nba_poeltl_missed_teampts112',nt,lambda r:r['game_id'] in {22200247,22200319,22200333,22200345,22200375,22200387,22200406,22200420,22200591} and r['team_id']==1610612759 and r['pts']==112),
 ]
source_hashes={str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [FIX/'player_game_stats/2025-26_regular_season.csv',FIX/'team_game_stats/2025-26_regular_season.csv',archive]}
oracle={'baseline':'d0744a435e90872e91a7e37b2b56bb59a60f3baa','checker':'/root/poeltl_source_checker; independent Codex session, exact backend model not exposed','source_hashes':source_hashes,'classification':'Controlled fixture arithmetic and qualified retained historical NBA raw-row arithmetic, kept separate','meaning':'Explicit equality sets both inclusive endpoints to the same count value; compare the same owner/stat/row grain. Equality never means >=, zero-plus never means exact zero. No rate or exact-time precision expansion.','cases':{name:calc([r for r in rows if pred(r)]) for name,rows,pred in selectors}}
# Multi-season independent expectations preserve filtering before grouping.
season_cases={}
for season in ['2024-25','2025-26']:
 raw=csvrows('player_game_stats',season)
 selected=[r for r in raw if r['player_name']=='Stephen Curry' and float(r['ast'])==7]
 for r in selected:
  for k in ['game_id','team_id','player_id']:r[k]=int(r[k])
  for k in ['pts','reb','ast','tov']:r[k]=float(r[k])
 season_cases[season]=calc(selected)
oracle['season_splits_curry_ast7']=season_cases
(BASE/'oracle.json').write_text(json.dumps(oracle,indent=2)+'\n')
print('oracle_sha256',hashlib.sha256((BASE/'oracle.json').read_bytes()).hexdigest())
for k,c in oracle['cases'].items():print(k,c['rows'],c['nba_games'],c['players'])
