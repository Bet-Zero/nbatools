"""Independent direct-original oracle; no application imports, no source fetches."""
import argparse, collections, hashlib, html, json, pathlib, stat, zipfile
from html.parser import HTMLParser
SCRIPT = pathlib.Path(__file__).resolve()
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--repo', type=pathlib.Path, help='Repository root (auto-discovered from script parents or cwd)')
parser.add_argument('--collection', type=pathlib.Path, default=SCRIPT.parent/'collection.zip', help='Exact captured ZIP; defaults to package-local collection.zip')
parser.add_argument('--archive', type=pathlib.Path, help='Exact retained native archive ZIP; defaults under --repo')
parser.add_argument('--output', type=pathlib.Path, default=SCRIPT.parent/'replay', help='Isolated output directory')
args = parser.parse_args()
REPO = args.repo
if REPO is None:
    REPO = next((p for p in [*SCRIPT.parents, pathlib.Path.cwd()] if (p/'pyproject.toml').is_file() and (p/'AGENTS.md').is_file()), None)
if REPO is None and args.archive is None:
    parser.error('Specify --repo or --archive outside a repository checkout')
ROOT = args.output.resolve()
ROOT.mkdir(parents=True, exist_ok=True)
ATTACHMENT = args.collection.resolve()
ARCHIVE = args.archive if args.archive else REPO/'working/nba-tools-completion-program/source-evidence/multi-team-absence-20261106/archive-originals.zip' 
sha = lambda b: hashlib.sha256(b).hexdigest()
class NextParser(HTMLParser):
    def __init__(self): super().__init__(); self.active=False; self.parts=[]
    def handle_starttag(self,t,a):
        if t=='script' and dict(a).get('id')=='__NEXT_DATA__': self.active=True
    def handle_endtag(self,t):
        if t=='script': self.active=False
    def handle_data(self,d):
        if self.active: self.parts.append(d)
def table(obj,name):
    r=next(x for x in obj['resultSets'] if x['name']==name)
    return [dict(zip(r['headers'],x,strict=True)) for x in r['rowSet']]
def authenticate_zip(path):
    b=path.read_bytes(); z=zipfile.ZipFile(path)
    assert z.testzip() is None
    assert len(z.namelist())==len(set(z.namelist()))
    for i in z.infolist():
        p=pathlib.PurePosixPath(i.filename)
        assert not p.is_absolute() and '..' not in p.parts and '\\' not in i.filename
        assert not stat.S_ISLNK(i.external_attr>>16)
    return z, {'bytes':len(b),'sha256':sha(b),'members':z.namelist()}
z,attached=authenticate_zip(ATTACHMENT)
assert attached['bytes']==111037 and attached['sha256']=='42134b026ae53e9ca3c731815f3290cc79937d14b5768c1f1eda9c9a7547361e'
original_receipt=z.read('receipt.json'); receipt=json.loads(original_receipt)
assert receipt['classification']=='original_capture_only_not_qualified'
(ROOT/'receipt.original.json').write_bytes(original_receipt)
articles=[]
for r in receipt['records']:
    b=z.read('sources/'+r['file']); assert len(b)==r['size_bytes'] and sha(b)==r['sha256'] and r['http_status']==200
    p=NextParser();p.feed(b.decode()); page=json.loads(''.join(p.parts))['props']['pageProps']['pageObject']
    articles.append({'file':r['file'],'sha256':sha(b),'url':r['url'],'title':page.get('title'),'date':page['date'],'modified':page['modified'],'body':[html.unescape(x['text']).strip() for x in page['contentStructured'] if 'text' in x]})
a,archive=authenticate_zip(ARCHIVE)
assert archive['sha256']=='6e4b06650519da0b9bfc46269fff5e4f0c231949d8922585e7f4590fbac9d6a1'
ar=json.loads(a.read('receipt.json')); pr=json.loads(a.read('pairs/receipt.json'))
for key in ['teams','players']:
    b=a.read(key+'.json'); assert len(b)==ar[key]['bytes'] and sha(b)==ar[key]['sha256']
for n,r in pr.items():
    b=a.read('pairs/'+n);assert len(b)==r['bytes'] and sha(b)==r['sha256']
teams=table(json.loads(a.read('teams.json')),'LeagueGameFinderResults')
teams=[x for x in teams if x['SEASON_ID']=='22022' and x['GAME_ID'].startswith('002')]
players=table(json.loads(a.read('players.json')),'LeagueGameLog')
assert all(x['SEASON_ID']=='22022' and x['GAME_ID'].startswith('002') for x in players)
by_game=collections.defaultdict(list)
for t in teams:by_game[t['GAME_ID']].append(t)
assert len(teams)==2460 and len(by_game)==1230 and all(len(x)==2 and len({t['TEAM_ID'] for t in x})==2 and len({t['GAME_DATE'] for t in x})==1 for x in by_game.values())
assert len({(t['GAME_ID'],t['TEAM_ID']) for t in teams})==len(teams)
assert len(players)==25895 and len({(x['GAME_ID'],x['PLAYER_ID']) for x in players})==len(players)
assert all(len([t for t in by_game[p['GAME_ID']] if t['TEAM_ID']==p['TEAM_ID'] and t['GAME_DATE']==p['GAME_DATE']])==1 for p in players)
assert set(collections.Counter(t['TEAM_ID'] for t in teams).values())=={82}
poeltl=[x for x in players if x['PLAYER_ID']==1627751]
assert all(x['PLAYER_NAME']=='Jakob Poeltl' and x['MIN']>0 for x in poeltl)
appearance={(p['GAME_ID'],p['TEAM_ID']):p for p in poeltl}
# Full-day intervals derived from the three official articles; intraday transfer date stays unknown.
def eligible(t):
    return (t['TEAM_ID']==1610612759 and '2022-10-18'<=t['GAME_DATE']<='2023-02-08') or (t['TEAM_ID']==1610612761 and '2023-02-10'<=t['GAME_DATE']<='2023-04-09')
eligible_games=sorted([x for x in teams if eligible(x)],key=lambda x:(x['GAME_DATE'],x['GAME_ID']))
dnps=[]
for t in eligible_games:
    if (t['GAME_ID'],t['TEAM_ID']) in appearance:continue
    gid=t['GAME_ID']; summary=json.loads(a.read(f'pairs/boxscoresummaryv2_{gid}.json')); traditional=json.loads(a.read(f'pairs/boxscoretraditionalv3_{gid}.json'))['boxScoreTraditional']
    s=table(summary,'GameSummary');assert len(s)==1
    s=s[0];assert s['GAME_ID']==gid and s['GAME_DATE_EST'][:10]==t['GAME_DATE'] and s['GAME_STATUS_ID']==3
    assert {s['HOME_TEAM_ID'],s['VISITOR_TEAM_ID']}=={x['TEAM_ID'] for x in by_game[gid]}
    assert traditional['gameId']==gid and {traditional['homeTeamId'],traditional['awayTeamId']}=={x['TEAM_ID'] for x in by_game[gid]}
    inactive=[p for p in table(summary,'InactivePlayers') if p['PLAYER_ID']==1627751]
    assert len(inactive)==1 and inactive[0]['TEAM_ID']==t['TEAM_ID'] and inactive[0]['FIRST_NAME']=='Jakob' and inactive[0]['LAST_NAME']=='Poeltl'
    assert not any(p['personId']==1627751 for k in ['homeTeam','awayTeam'] for p in traditional[k]['players'])
    for k in ['homeTeam','awayTeam']:
        tid=traditional[k]['teamId'];native={p['personId'] for p in traditional[k]['players'] if p['statistics']['minutes'] not in ('','0:00','0:00:00')}
        logs={p['PLAYER_ID'] for p in players if p['GAME_ID']==gid and p['TEAM_ID']==tid}
        assert native==logs,(gid,tid,native^logs)
    dnps.append({'game_id':gid,'date':t['GAME_DATE'],'team_id':t['TEAM_ID'],'matchup':t['MATCHUP'],'pts':t['PTS'],'explicit_evidence':'SummaryV2 InactivePlayers identity; TraditionalV3 no played row; exact played-player IDs match LeagueGameLog'})
assert set(appearance)=={(t['GAME_ID'],t['TEAM_ID']) for t in eligible_games if (t['GAME_ID'],t['TEAM_ID']) in appearance}
rows=[]
for t in eligible_games:
    rows.append({'game_id':t['GAME_ID'],'date':t['GAME_DATE'],'team_id':t['TEAM_ID'],'team':t['TEAM_ABBREVIATION'],'matchup':t['MATCHUP'],'pts':t['PTS'],'status':'played' if (t['GAME_ID'],t['TEAM_ID']) in appearance else 'explicit_dnp'})
# Independent controlled filters, including counts different from the already documented 9/0.
filters={}
for name,predicate in [('home',lambda x:'vs.' in x['matchup']),('away',lambda x:' @ ' in x['matchup']),('team_points_at_least_105',lambda x:x['pts']>=105),('team_points_under_105',lambda x:x['pts']<105),('against_lakers',lambda x:x['matchup'].endswith('LAL')),('november_only',lambda x:x['date'].startswith('2022-11'))]:
    selected=[x for x in rows if predicate(x)]; filters[name]={'eligible':[x['game_id'] for x in selected],'played':[x['game_id'] for x in selected if x['status']=='played'],'missed':[x['game_id'] for x in selected if x['status']=='explicit_dnp']}
counts={}
for team in ['SAS','TOR']:
    rs=[x for x in rows if x['team']==team];counts[team]={'eligible':len(rs),'played':sum(x['status']=='played' for x in rs),'explicit_dnp':sum(x['status']=='explicit_dnp' for x in rs),'unknown':0}
trade_day=[t for t in teams if t['GAME_DATE']=='2023-02-09' and t['TEAM_ID'] in [1610612759,1610612761]]
assert not trade_day
oracle={'checker':'/root/poeltl_source_checker; separate Codex checker session; exact backend model not exposed','baseline':'f06464577b105c039b1e543eaf91d2ed75d03699','attached':attached,'receipt_sha256':sha(original_receipt),'original_receipt_classification':receipt['classification'],'article_evidence':articles,'archive':archive,'raw_population':{'team_rows':len(teams),'unique_games':len(by_game),'player_rows':len(players),'all_30_teams_exactly_82_games':True},'qualified_full_day_intervals':[{'team':'SAS','start':'2022-10-18','end':'2023-02-08'},{'team':'TOR','start':'2023-02-10','end':'2023-04-09'}],'unresolved_date':'2023-02-09 intraday transaction; no full-day club assertion','candidate_club_games_on_unresolved_date':trade_day,'by_team':counts,'eligible_games':rows,'explicit_dnps':dnps,'filters':filters,'unknown_participation':[],'excluded_club_games':[{k:t[k] for k in ['GAME_ID','GAME_DATE','TEAM_ID','MATCHUP']} for t in sorted(teams,key=lambda t:(t['GAME_DATE'],t['GAME_ID'])) if t['TEAM_ID'] in [1610612759,1610612761] and not eligible(t)],'limitations':['Historical qualified staging only; no current freshness or production publication claim.','Retrospective tenure plus dated official transfer and re-signing, not appearance-derived tenure.','NBA-native endpoint structures share upstream origin; archive mirror is provenance custody, not independent upstream corroboration.','Explicit inactive observation proves nonparticipation, never medical injury cause.','No Feb9 date-only membership answer is certified.']}
(ROOT/'oracle.json').write_text(json.dumps(oracle,indent=2)+'\n')
print(json.dumps({'counts':counts,'totals':{'eligible':len(rows),'played':len(appearance),'explicit_dnp':len(dnps),'unknown':0},'trade_day_club_games':trade_day,'dnps':dnps,'filters':{k:{j:len(v) for j,v in d.items()} for k,d in filters.items()},'oracle_sha256':sha((ROOT/'oracle.json').read_bytes())},indent=2))
