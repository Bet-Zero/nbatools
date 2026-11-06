"""Independent grouped-OR source oracle and coherent seven-row synthetic population."""
import argparse,collections,csv,hashlib,json,pathlib,shutil,zipfile
SCRIPT=pathlib.Path(__file__).resolve();ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--repo',type=pathlib.Path,default=pathlib.Path.cwd());ap.add_argument('--output',type=pathlib.Path,default=SCRIPT.parent/'source-replay');a=ap.parse_args();REPO=a.repo.resolve();OUT=a.output.resolve();OUT.mkdir(parents=True,exist_ok=True)
F=REPO/'qa/fixtures/query_engine_sample';root=OUT/'controlled'
if not root.exists():shutil.copytree(F,root)
def read(path):
 with path.open() as f:return list(csv.DictReader(f))
def write(path,rows):
 with path.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
raw=read(F/'data/raw/player_game_stats/2025-26_regular_season.csv');traw=read(F/'data/raw/team_game_stats/2025-26_regular_season.csv');graw=read(F/'data/raw/games/2025-26_regular_season.csv')
teams={r['team_abbr']:{k:r[k] for k in ['team_id','team_abbr','team_name']} for r in traw}
identities={'A':203999,'B':1628973,'C':1627750}
values=[(1,'A',25,12,0,-2),(2,'A',25,5,1,0),(3,'B',18,12,0,2),(4,'B',18,5,0,-2),(5,'C',20,10,0,0),(1,'C',30,11,2,2),(6,'A',0,0,0,0)]
# game,subjectclub,opponent,subjecthome,subjectwin. Shared-game subjects have coherent teams.
G={1:('DEN','GSW',True,True),2:('DEN','LAL',False,False),3:('NYK','GSW',True,False),4:('NYK','LAL',False,True),5:('DEN','LAL',True,False),6:('DEN','GSW',False,True)}
players=[];teamrows=[];games=[]
for gid,(club,opp,home,win) in G.items():
 date=f'2025-11-{gid:02d}'
 for own,other,is_home,is_win in [(club,opp,home,win),(opp,club,not home,not win)]:
  t=next(r.copy() for r in traw if r['team_abbr']==own);t.update(teams[own]);t.update(game_id=str(gid),game_date=date,opponent_team_id=teams[other]['team_id'],opponent_team_abbr=other,opponent_team_name=teams[other]['team_name'],is_home=str(is_home),is_away=str(not is_home),wl='W' if is_win else 'L',pts=100 if is_win else 90,fgm=40,fga=80,fg3m=10,fg3a=25,ftm=10 if is_win else 0,fta=10,plus_minus=10 if is_win else -10,minutes=240);teamrows.append(t)
  # Points100=40*2+10*1+10FT; points90=40*2+10*1. Other counts are controlled seed fields.
 g=graw[0].copy();g.update(game_id=str(gid),game_date=date,home_team_id=teams[club if home else opp]['team_id'],away_team_id=teams[opp if home else club]['team_id']);games.append(g)
for gid,who,pts,ast,tov,pm in values:
 club,opp,home,win=G[gid];r=next(r.copy() for r in raw if int(r['player_id'])==identities[who]);r.update(teams[club]);r.update(game_id=str(gid),game_date=f'2025-11-{gid:02d}',opponent_team_id=teams[opp]['team_id'],opponent_team_abbr=opp,opponent_team_name=teams[opp]['team_name'],is_home=str(home),is_away=str(not home),wl='W' if win else 'L',pts=pts,ast=ast,tov=tov,plus_minus=pm,fgm=pts//2,fga=max(pts//2,20),fg3m=0,fg3a=0,ftm=pts%2,fta=pts%2,minutes=30);players.append(r)
for family,rows in [('player_game_stats',players),('team_game_stats',teamrows),('games',games)]:write(root/'data/raw'/family/'2025-26_regular_season.csv',rows)
def normalized(rows):
 out=[]
 for r in rows:
  r=r.copy()
  for k in ['game_id','player_id','team_id','opponent_team_id']:
   if k in r:r[k]=int(r[k])
  for k in ['pts','ast','reb','tov','blk','plus_minus']:r[k]=float(r[k])
  if 'is_home' in r:r['is_home']=str(r['is_home']) in ['True','1']
  out.append(r)
 return out
C=normalized(players);T={(int(r['game_id']),int(r['team_id'])):r for r in teamrows}
for r in C:r['team_pts']=float(T[(r['game_id'],r['team_id'])]['pts']);r['opponent_pts']=float(T[(r['game_id'],r['opponent_team_id'])]['pts'])
def key(r):return (r['game_id'],r['team_id'],r['player_id'])
def audit(rows,left,right,scope=lambda r:True,outer=lambda r:True):
 base=[r for r in rows if scope(r)];l=[r for r in base if left(r)];rr=[r for r in base if right(r)];selected=[r for r in base if (left(r) or right(r)) and outer(r)];both=[r for r in base if left(r) and right(r)];counts=collections.Counter(r['player_id'] for r in selected)
 return {'base_rows':len(base),'left_keys':sorted(key(r) for r in l),'right_keys':sorted(key(r) for r in rr),'overlap_keys':sorted(key(r) for r in both),'left_only_keys':sorted(key(r) for r in l if not right(r)),'right_only_keys':sorted(key(r) for r in rr if not left(r)),'selected_keys':sorted(key(r) for r in selected),'player_games':len(selected),'nba_games':len({r['game_id'] for r in selected}),'distinct_players':len(counts),'player_occurrences':sorted(counts.items()),'selected_players':sorted(counts),'pts_sum':sum(r['pts'] for r in selected),'ast_sum':sum(r['ast'] for r in selected)}
L=lambda r:r['pts']>20;R=lambda r:r['ast']>10
cases={'controlled_union':audit(C,L,R),'controlled_team_DEN':audit(C,L,R,scope=lambda r:r['team_abbr']=='DEN'),'controlled_home':audit(C,L,R,scope=lambda r:r['is_home']),'controlled_away':audit(C,L,R,scope=lambda r:not r['is_home']),'controlled_opponent_GSW':audit(C,L,R,scope=lambda r:r['opponent_team_abbr']=='GSW'),'controlled_outer_zero_tov':audit(C,L,R,outer=lambda r:r['tov']==0),'controlled_outer_exact25pts':audit(C,L,R,outer=lambda r:r['pts']==25),'controlled_grouped_and_or':audit(C,lambda r:r['pts']>20 and r['tov']==0,lambda r:r['ast']>10 and r['tov']==0),'controlled_exact_or_signedzero':audit(C,lambda r:r['pts']==20,lambda r:r['plus_minus']==0),'controlled_zero':audit(C,lambda r:r['pts']>90,lambda r:r['ast']>90),'controlled_team_owned':audit(C,L,R,outer=lambda r:r['team_pts']==100),'controlled_crossgame_and_trap':audit(C,lambda r:r['pts']>20 and r['ast']>10,lambda r:False),'controlled_duplicate_or':audit(C,L,L),'controlled_date_scope':audit(C,L,R,scope=lambda r:'2025-11-02'<=r['game_date']<='2025-11-03')}
full=normalized(raw);cases['synthetic_full_limit']=audit(full,lambda r:r['pts']>=26,lambda r:r['ast']>=7)
archive=REPO/'working/nba-tools-completion-program/source-evidence/multi-team-absence-20261106/archive-originals.zip';assert hashlib.sha256(archive.read_bytes()).hexdigest()=='6e4b06650519da0b9bfc46269fff5e4f0c231949d8922585e7f4590fbac9d6a1'
with zipfile.ZipFile(archive) as z:
 def tab(n,t):
  j=json.loads(z.read(n));r=next(r for r in j['resultSets'] if r['name']==t);return [dict(zip(r['headers'],x)) for x in r['rowSet']]
 nt=[{k.lower():v for k,v in r.items()} for r in tab('teams.json','LeagueGameFinderResults') if r['SEASON_ID']=='22022' and r['GAME_ID'].startswith('002')];np=[{k.lower():v for k,v in r.items()} for r in tab('players.json','LeagueGameLog')]
 tm={(int(r['game_id']),r['team_id']):r for r in nt};bygame=collections.defaultdict(list)
 for r in nt:bygame[int(r['game_id'])].append(r)
 assert len(nt)==2460 and len(np)==25895
 for r in np:
  r['game_id']=int(r['game_id']);r['team_abbr']=r['team_abbreviation'];r['is_home']=' vs. ' in r['matchup'];r['team_pts']=tm[(r['game_id'],r['team_id'])]['pts'];opp=next(t for t in bygame[r['game_id']] if t['team_id']!=r['team_id']);r['opponent_team_abbr']=opp['team_abbreviation'];r['opponent_pts']=opp['pts']
 nl=lambda r:r['pts']>37;nr=lambda r:r['ast']>10
 cases.update({'native_union':audit(np,nl,nr),'native_scoped_GSW':audit(np,nl,nr,scope=lambda r:r['team_abbr']=='GSW'),'native_home':audit(np,nl,nr,scope=lambda r:r['is_home']),'native_opponent_BOS':audit(np,nl,nr,scope=lambda r:r['opponent_team_abbr']=='BOS'),'native_outer_zero_tov':audit(np,nl,nr,outer=lambda r:r['tov']==0),'native_grouped_and_or':audit(np,lambda r:r['pts']>37 and r['ast']>=7,lambda r:r['reb']>=18 and r['blk']>=3),'native_exact_or':audit(np,lambda r:r['pts']==29,lambda r:r['ast']==9),'native_team_owned':audit(np,nl,nr,outer=lambda r:r['team_pts']>=125),'native_opponent_owned':audit(np,nl,nr,outer=lambda r:r['opponent_pts']<110)})
sources={str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [F/'data/raw/player_game_stats/2025-26_regular_season.csv',F/'data/raw/team_game_stats/2025-26_regular_season.csv',F/'data/raw/games/2025-26_regular_season.csv',archive]}
oracle={'baseline':'cbf46c7d08c5e41f4bf87a4000d6fee4d698bd3a','checker':'/root/poeltl_source_checker; separate Codex session, exact backend model not exposed','sources':sources,'controlled_identities':identities,'controlled_raw_rows':C,'controlled_generated_hashes':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [root/'data/raw'/f/'2025-26_regular_season.csv' for f in ['player_game_stats','team_game_stats','games']]},'meaning':'Evaluate each OR branch independently on the same scoped raw player-game population; apply outer AND to union rows; deduplicate branch overlaps on(game_id,team_id,player_id), then project distinct player_id exactly once, without leaderboard limits or cross-game AND. Player-game, NBA-game, distinct-player counts remain separately labeled. Known zero requires qualified loaded nonempty scope; unavailable input cannot become zero.','cases':cases,'prospective_2023_24':{'source':'raw/player_game_stats/2023-24_regular_season.csv in existing pinned qualified R2 generation','row_predicate':'PTS > 40 OR AST > 12, regular season2023-24','count_grain':'distinct PLAYER_ID after rowwise union','total':None,'reason':'Complete qualified2023-24rows are not retained locally; frozen K03binding is limited named-player samples and cannot supply the global count.','known_subset':'K03-C1 Brunson exact11player-game keys independently retained in tests/k03_expected.json; no global extrapolation.'}}
(OUT/'oracle.json').write_text(json.dumps(oracle,indent=2)+'\n');print('ORACLE_SHA',hashlib.sha256((OUT/'oracle.json').read_bytes()).hexdigest())
for k,c in cases.items():print(k,'PG',c['player_games'],'NBA',c['nba_games'],'players',c['distinct_players'],'overlap',len(c['overlap_keys']))
