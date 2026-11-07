"""Independent paired-missing raw oracle. Stdlib only; no query/loader imports."""
import argparse,collections,csv,hashlib,io,json,pathlib,shutil,zipfile
P=pathlib.Path(__file__).resolve().parent;ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--repo',type=pathlib.Path,default=P/'baseline');ap.add_argument('--output',type=pathlib.Path,default=P);a=ap.parse_args();R=a.repo.resolve();O=a.output.resolve();O.mkdir(parents=True,exist_ok=True);E=R/'working/nba-tools-completion-program/source-evidence';source=[]
def sha(b):return hashlib.sha256(b).hexdigest()
def archive(rel,digest):
 p=E/rel;assert sha(p.read_bytes())==digest;source.append({'path':rel,'sha256':digest});return zipfile.ZipFile(p)
def rows(raw):return list(csv.DictReader(io.StringIO(raw.decode())))
def write_csv(p,rs,columns=None):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('w',newline='')as f:
  w=csv.DictWriter(f,fieldnames=columns or list(rs[0]));w.writeheader();w.writerows(rs)
def number(s):return float(s)if s not in ['',None]else None
def facts(rs,player=False):
 keys=sorted((int(r['game_id']),int(r['team_id']),*([int(r['player_id'])]if player else[]))for r in rs);assert len(keys)==len(set(keys));n=len(rs)
 sums={s:sum(number(r[s])for r in rs)for s in ['pts','reb','ast']}
 return {'keys':keys,'games':n,'wins':sum(r['wl']=='W'for r in rs),'losses':sum(r['wl']=='L'for r in rs),'sums':sums,'means':{s:v/n if n else None for s,v in sums.items()}}
# Retained original qualification/append acceptance is reused; this is not new source capture.
with archive('k08-composition/staging-acceptance-source.zip','4ce53f28bd44230138f000927d3ffa43dbe618759e265ce65e095b505ecb92cf')as z:
 prefix='acquired_data/composed-participation-stage/';obs={s:rows(z.read(prefix+'raw/player_game_availability/'+s+'_regular_season.csv'))for s in ['2023-24','2024-25','2025-26']};obs_bytes={s:z.read(prefix+'raw/player_game_availability/'+s+'_regular_season.csv')for s in obs}
 for s,rs in obs.items():assert len({(int(r['game_id']),int(r['player_id']))for r in rs})==len(rs)
with archive('k08-bos-remaining/coverage-source.zip','a7bd0c019daba938ac60fce80ced7b57953709b59f2ffc87fb910951e5f1401f')as z:
 p='acquired_data/bos-participation-coverage/';bos_teams=rows(z.read(p+'team82.csv'));bos_players=rows(z.read(p+'target-player-rows.csv'));binding=json.loads(z.read(p+'source-bindings.json'));assert binding['generation']=='availability-lebron-season-v1-20261031';assert binding['manifest_sha256']=='3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3'
with archive('k08-direct-dependencies/input-audit-source.zip','33f4a6d9a013da81f3f4c3c25f837c44cd7248de42f425b92e01af68b71cb67a')as z:
 p='acquired_data/direct-k08-participation-coverage/';lal_teams=rows(z.read(p+'2023-24-1610612747-team82.csv'));lal_players=rows(z.read(p+'2023-24-1610612747-target-player-rows.csv'));reciprocal=rows(z.read(p+'2023-24-1610612747-reciprocal-team164.csv'))
 assert len(lal_teams)==82
BOS=1610612738;LAL=1610612747;TATUM=1628369;BROWN=1627759;AD=203076;AR=1630559
states={s:{(int(r['game_id']),int(r['team_id']),int(r['player_id'])):r['participation_state']for r in rs}for s,rs in obs.items()}
# Qualified positive canonical appearances prove played; absence still requires explicit DNP.
for season,players in [('2025-26',bos_players),('2023-24',lal_players)]:
 for r in players:
  if float(r['minutes'])>0:
   key=int(r['game_id']),int(r['team_id']),int(r['player_id']);assert states[season].get(key)!='did_not_play';states[season][key]='played'
def pair(teams,season,club,pids):
 assert len(teams)==82 and len({int(t['game_id'])for t in teams})==82
 for pid in pids:assert len([t for t in teams if states[season].get((int(t['game_id']),club,pid))in ['played','did_not_play']])==82
 return[t for t in teams if all(states[season][int(t['game_id']),club,pid]=='did_not_play'for pid in pids)]
both=pair(bos_teams,'2025-26',BOS,[TATUM,BROWN]);zero=pair(lal_teams,'2023-24',LAL,[AD,AR]);cases={'bos_pair':facts(both),'lal_pair_zero':facts(zero),'bos_pair_home':facts([r for r in both if r['is_home'].lower()in['1','true','1.0']]),'bos_pair_away':facts([r for r in both if r['is_away'].lower()in['1','true','1.0']]),'bos_pair_pts111':facts([r for r in both if float(r['pts'])>=111]),'bos_pair_nov_feb':facts([r for r in both if '2025-11-01'<=r['game_date']<='2026-02-28'])}
for relation,pid,state in [('tatum_missing_brown_played',TATUM,'did_not_play'),('tatum_played_brown_missing',TATUM,'played')]:
 other='played'if state=='did_not_play'else'did_not_play';sample=[r for r in bos_teams if states['2025-26'][int(r['game_id']),BOS,TATUM]==state and states['2025-26'][int(r['game_id']),BOS,BROWN]==other];cases['bos_'+relation]=facts(sample)
# An isolated partial-core replay contains unchanged source observation bytes and authenticated canonical subsets.
# It is qualified only for the declared club/season slices, not a complete NBA dataset/publication.
core=O/'qualified-core';core.mkdir(parents=True,exist_ok=True)
for season,t,p in [('2025-26',bos_teams,bos_players),('2023-24',lal_teams,lal_players)]:
 write_csv(core/f'data/raw/team_game_stats/{season}_regular_season.csv',t);write_csv(core/f'data/raw/player_game_stats/{season}_regular_season.csv',p);write_csv(core/f'data/raw/games/{season}_regular_season.csv',[{k:r[k]for k in ['game_id','game_date','season','season_type','team_id','team_abbr','opponent_team_id','opponent_team_abbr','is_home','is_away']}for r in t]);f=core/f'data/raw/player_game_availability/{season}_regular_season.csv';f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(obs_bytes[season])
# Unfamiliar-club software oracle: committed synthetic fixture plus explicit declaration, never inferred DNP.
fixture=O/'controlled';shutil.copytree(R/'qa/fixtures/query_engine_sample',fixture,dirs_exist_ok=True);pf=fixture/'data/raw/player_game_stats/2025-26_regular_season.csv';tf=fixture/'data/raw/team_game_stats/2025-26_regular_season.csv';p=rows(pf.read_bytes());t=rows(tf.read_bytes());miami=sorted([r for r in t if r['team_abbr']=='MIA'],key=lambda r:(r['game_date'],int(r['game_id'])));games={int(r['game_id'])for r in miami};assert len(miami)>6;BAM,HERRO=202355,1629639;absences={BAM:{int(miami[i]['game_id'])for i in [0,1,2,5]},HERRO:{int(miami[i]['game_id'])for i in [0,1,3,5]}};synthetic=[]
for r in p:
 if r['team_abbr']=='MIA'and int(r['player_id'])in absences:
  synthetic.append({**{k:r[k]for k in ['game_id','game_date','season','season_type','team_id','player_id','player_name']},'participation_state':'did_not_play'if int(r['game_id'])in absences[int(r['player_id'])]else'played','coverage_scope':'controlled_fixture','source':'synthetic_test_observation','source_sha256':'','fixture_declaration':'Explicit controlled schedule, never missing-row inference or NBA evidence'})
write_csv(O/'controlled-observations.csv',synthetic)
write_csv(pf,[r for r in p if not(r['team_abbr']=='MIA'and int(r['player_id'])in absences and int(r['game_id'])in absences[int(r['player_id'])])])
bothids=absences[BAM]&absences[HERRO];c=[r for r in miami if int(r['game_id'])in bothids];cases['controlled_mia_pair']=facts(c);cases['controlled_mia_home']=facts([r for r in c if r['is_home'].lower()in ['true','1','1.0']]);cases['controlled_mia_date']=facts([r for r in c if r['game_date']<=miami[1]['game_date']]);cases['controlled_mia_player']=facts([{**r,'wl':next(x['wl']for x in miami if x['game_id']==r['game_id'])}for r in p if r['team_abbr']=='MIA'and int(r['player_id'])==202710 and int(r['game_id'])in bothids],True)
# S4 exact state identities are independently read from retained observed rows. Numeric old4report proof is reused explicitly.
s4={}
for season,gids,state in [('2023-24',[22300403,22300684],'played'),('2025-26',[22500338,22500823],'did_not_play')]:
 actual=[r for r in obs[season]if int(r['game_id'])in gids and int(r['player_id'])in [TATUM,BROWN]];assert len(actual)==4 and all(r['participation_state']==(state if int(r['player_id'])==TATUM else'played')for r in actual);s4[season]={'game_ids':gids,'Tatum_state':state,'Brown_state':'played','source_hashes':sorted({r['source_sha256']for r in actual})}
 selected=[r for r in (reciprocal if season=='2023-24'else bos_teams)if int(r['game_id'])in gids and int(r['team_id'])==BOS];assert len(selected)==2;s4[season]['team']=facts(selected)
 if season=='2025-26':s4[season]['player']=facts([{**r,'wl':next(x['wl']for x in selected if x['game_id']==r['game_id'])}for r in bos_players if int(r['player_id'])==BROWN and int(r['game_id'])in gids],True)
s4['2023-24']['player_numeric_reuse']={'games':2,'wins':1,'losses':1,'pts_mean':13.5,'reb_mean':6.5,'ast_mean':4.5,'source':'Previously independently accepted retained official4report/S4numeric receipts; not newly re-derived local Brown2023 CSV rows. PinnedR2base originalCSV/sourcehash check remains required.'}
oracle={'baseline':'477c7f13b81290ad1e291118d170e7300b630e0b','checker':'Independent Codex session /root/poeltl_source_checker; exact backend model unavailable','meaning':'Missing pair means AND of each named qualified whole-game did_not_play condition on same candidate club/game, never OR, medical cause, roster absence or simultaneous on-court absence. Complete requested coverage before filtering; retain unknown and membership distinctions. Fixed historical slices do not accept current thisseason freshness.','sources':source,'cases':cases,'s4':s4,'controlled_scope':{'classification':'synthetic_fixture_only','observations':'controlled-observations.csv','method':'Explicit fixture provider injected in checker only; original production qualifier is not weakened and no fabricated NBA source reference used.'},'qualified_core_scope':'Retained qualified canonical subsets/unchanged observationbytes forBOS2025-26 andLAL2023-24 only; partialNBAcore, no validation/publication claim. Source originals remain in retained archive and/or authenticatedbase.','production_writes':0}
(O/'oracle.json').write_text(json.dumps(oracle,indent=2)+'\n');(core/'offline-scope.json').write_text(json.dumps({'classification':oracle['qualified_core_scope'],'sources':source,'no_fetch':True},indent=2)+'\n');print('ORACLE_SHA',sha((O/'oracle.json').read_bytes()));print({k:(v['games'],v['wins'],v['losses'])for k,v in cases.items()});print('S4',s4)
