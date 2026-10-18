"""Independent raw-only oracle. Does not import or execute either interpreter."""
import hashlib,json
from pathlib import Path
import pandas as pd
ROOT=Path('/workspace/work/s4-local-replay/data/raw')
OUT=Path('/workspace/work/p2-language')
seasons=['2023-24','2025-26']; frames={}; sources={}
for season in seasons:
 for kind in ['team_game_stats','player_game_stats','player_game_availability']:
  path=ROOT/kind/(season+'_regular_season.csv');sources[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest();frames[kind,season]=pd.read_csv(path)

def spec(id,family,query,kind,subject,**kw):
 return dict(id=id,family=family,query=query,kind=kind,subject=subject,season_type='Regular Season',**kw)
cases=[
 spec('p2_s1_1','S1','Split Denver’s road record against Utah by season: 2023-24 and 2025-26.','team','DEN',seasons=seasons,opponent='UTA',home=False,split=True),
 spec('p2_s1_2','S1','For 2025-26 and 2023-24, give Milwaukee’s home record versus Chicago separately for each season.','team','MIL',seasons=seasons,opponent='CHI',home=True,split=True),
 spec('p2_s1_3','S1','Against Miami, what was New York’s away record in each of 2023-24 and 2025-26?','team','NYK',seasons=seasons,opponent='MIA',home=False,split=True),
 spec('p2_s1_4','S1','Show Minnesota’s record at home against Denver, split into 2025-26 and 2023-24.','team','MIN',seasons=seasons,opponent='DEN',home=True,split=True),
 spec('p2_s2_1','S2','Nikola Jokic averages versus Dallas in 2023-24 and 2025-26, only games with 28 or more points, by season.','player',203999,seasons=seasons,opponent='DAL',own_min=28,split=True),
 spec('p2_s2_2','S2','In 2025-26 and 2023-24 separately, average Jalen Brunson’s stats against Boston when he scores at least 24 points.','player',1628973,seasons=seasons,opponent='BOS',own_min=24,split=True),
 spec('p2_s2_3','S2','Against Oklahoma City, Anthony Edwards averages with at least 26 points, broken out for 2023-24 and 2025-26.','player',1630162,seasons=seasons,opponent='OKC',own_min=26,split=True),
 spec('p2_s2_4','S2','Give Derrick White’s averages by season for 2025-26 and 2023-24 versus New York, counting only his games with 15 or more points.','player',1628401,seasons=seasons,opponent='NYK',own_min=15,split=True),
 spec('p2_s3_1','S3','Denver’s 2023-24 road record when Denver scores at least 115 and its opponent scores under 115.','team','DEN',seasons=['2023-24'],home=False,own_min=115,opponent_lt=115),
 spec('p2_s3_2','S3','When their opponents score fewer than 108 points, Milwaukee’s home record scoring at least 108 in 2023-24.','team','MIL',seasons=['2023-24'],home=True,own_min=108,opponent_lt=108),
 spec('p2_s3_3','S3','On the road in 2023-24, Nikola Jokic’s averages when he scores at least 28 and the opposing team scores under 112.','player',203999,seasons=['2023-24'],home=False,own_min=28,opponent_lt=112),
 spec('p2_s3_4','S3','Jalen Brunson averages in 2023-24 home games where the opponents score under 105 and Brunson scores at least 27.','player',1628973,seasons=['2023-24'],home=True,own_min=27,opponent_lt=105),
 spec('p2_s4_1','S4','Against the Lakers, Boston’s record by season in 2023-24 and 2025-26 when Jayson Tatum does not play.','team','BOS',seasons=seasons,opponent='LAL',participation='without',split=True),
 spec('p2_s4_2','S4','For 2025-26 and 2023-24 separately, Boston’s record versus Los Angeles Lakers with Jayson Tatum playing.','team','BOS',seasons=seasons,opponent='LAL',participation='with',split=True),
 spec('p2_s4_3','S4','Derrick White’s averages against the Lakers without Jayson Tatum, separated into 2023-24 and 2025-26.','player',1628401,seasons=seasons,opponent='LAL',participation='without',split=True),
 spec('p2_s4_4','S4','In 2025-26 and 2023-24, show Derrick White’s averages by season against Los Angeles Lakers with Jayson Tatum.','player',1628401,seasons=seasons,opponent='LAL',participation='with',split=True),
 spec('p2_s5_1','S5','How did Denver fare scoring at least 114 points within its final 8 games of 2023-24?','team','DEN',seasons=['2023-24'],own_min=114,last_n=8,last_n_scope='window'),
 spec('p2_s5_2','S5','Denver’s record for its 8 most recent games scoring 114 or more points in 2023-24.','team','DEN',seasons=['2023-24'],own_min=114,last_n=8,last_n_scope='qualifying'),
 spec('p2_s5_3','S5','Average Nikola Jokic’s stats for games scoring at least 29 points within his final 9 appearances of 2023-24.','player',203999,seasons=['2023-24'],own_min=29,last_n=9,last_n_scope='window'),
 spec('p2_s5_4','S5','For his 9 most recent games with 29 or more points in 2023-24, what were Nikola Jokic’s averages?','player',203999,seasons=['2023-24'],own_min=29,last_n=9,last_n_scope='qualifying'),
]
for c in cases:
 buckets=[]
 for season in c['seasons']:
  t=frames['team_game_stats',season]; p=frames['player_game_stats',season]
  if c['kind']=='team': d=t[t.team_abbr.eq(c['subject'])].copy()
  else:
   d=p[p.player_id.eq(c['subject'])].copy().drop(columns='wl',errors='ignore').merge(t[['game_id','team_id','wl']],on=['game_id','team_id'],validate='many_to_one')
  d=d.merge(t[['game_id','team_id','pts']].rename(columns={'team_id':'opponent_team_id','pts':'opponent_pts_oracle'}),on=['game_id','opponent_team_id'],validate='many_to_one')
  if 'opponent' in c:d=d[d.opponent_team_abbr.eq(c['opponent'])]
  if 'home' in c:d=d[d.is_home.eq(int(c['home']))]
  if 'participation' in c:
   a=frames['player_game_availability',season]; a=a[a.player_id.eq(1628369)]
   state='played' if c['participation']=='with' else 'did_not_play'
   statecol='participation_state'
   if statecol not in a:print(a.columns);raise RuntimeError('state column')
   assert set(d.game_id)<=set(a.game_id), 'uncovered candidate game'
   d=d[d.game_id.isin(a.loc[a[statecol].eq(state),'game_id'])]
  d=d.sort_values(['game_date','game_id'],ascending=False)
  if c.get('last_n_scope')=='window':d=d.head(c['last_n'])
  if 'own_min' in c:d=d[d.pts.ge(c['own_min'])]
  if 'opponent_lt' in c:d=d[d.opponent_pts_oracle.lt(c['opponent_lt'])]
  if c.get('last_n_scope')=='qualifying':d=d.head(c['last_n'])
  keys=['game_id','team_id']+(['player_id'] if c['kind']=='player' else [])
  buckets.append(dict(season=season,count=len(d),wins=int(d.wl.eq('W').sum()),losses=int(d.wl.eq('L').sum()),ids=d[keys].astype(int).to_dict('records'),sums={s:float(d[s].sum()) for s in ['pts','reb','ast']},averages={s:(float(d[s].mean()) if len(d) else None) for s in ['pts','reb','ast']}))
 c['expected_buckets']=buckets;c['intended_routes']=[('team_split_summary' if c['kind']=='team' else 'player_split_summary') if c.get('split') else ('team_record' if c['kind']=='team' else 'player_game_summary')]
 c['meaningful_metadata']={k:v for k,v in c.items() if k in ['subject','seasons','season_type','opponent','home','own_min','opponent_lt','participation','last_n','last_n_scope']}
 if c.get('participation'):c['meaningful_metadata']['participation_player_id']=1628369
 print(c['id'],[(b['season'],b['count'],b['sums']['pts']) for b in buckets])
controls=[
 ('ambiguous_player','Williams averages versus Denver in 2023-24.','Clarify which Williams; do not pick an identity.'),
 ('ambiguous_subject','Compare his averages against Miami in 2023-24 and 2025-26.','No player antecedent; require identity clarification.'),
 ('ambiguous_team','Los Angeles record versus Sacramento in 2023-24.','Lakers versus Clippers unresolved; require team clarification.'),
 ('ambiguous_order','Denver record in the last games scoring at least 114 in 2023-24.','Missing requested last-N count; do not invent a window.'),
 ('injury_extra','Derrick White averages against the Lakers in 2025-26 when Jayson Tatum is injured.','Participation evidence cannot establish injury condition; no ordinary absence substitution.'),
 ('on_court_extra','Derrick White averages against the Lakers in 2023-24 while Jayson Tatum is on the court.','Whole-game participation cannot establish simultaneous on-court statistics.'),
 ('subjective_extra','Denver road record in 2023-24 when Nikola Jokic looks exhausted.','Subjective exhaustion unavailable; do not drop the clause.'),
 ('medical_extra','Boston record against the Lakers in 2025-26 when Derrick White is medically cleared.','Played or reported absence cannot establish medical clearance.'),
]
obj=dict(schema_version=1,reviewer='/root/availability_checker',candidate_frozen_sha256='31819d844129ffe7514cb915ce3699bac9bb41d484baef4fa6d527abe301cf6b',candidate_executed=False,data_generation='queue-d-production-0574735-20260716',availability_overlay='four qualified BOS-LAL reports; staged, unpublished',source_sha256=sources,valid_cases=cases,controls=[dict(id='p2_control_'+str(i+1),category=k,query=q,expected_behavior=b,exclude_from_positive_denominator=True,allow_wrong_accepted_answer=False) for i,(k,q,b) in enumerate(controls)])
(OUT/'holdouts.json').write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')
