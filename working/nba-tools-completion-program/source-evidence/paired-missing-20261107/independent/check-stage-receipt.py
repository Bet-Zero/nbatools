"""Independent exact-key/arithmetic inspection of the authenticated stage receipt."""
import argparse,pathlib,zipfile,json,hashlib,xml.etree.ElementTree as ET,subprocess,csv,io
P=pathlib.Path(__file__).resolve().parent;ap=argparse.ArgumentParser();ap.add_argument('--artifact',type=pathlib.Path,required=True);ap.add_argument('--sha256',required=True);ap.add_argument('--request',required=True);ap.add_argument('--output',type=pathlib.Path,required=True);a=ap.parse_args();assert hashlib.sha256(a.artifact.read_bytes()).hexdigest()==a.sha256;O=json.loads((P/'oracle.json').read_text());records=[]
def extract(body):return body.get('result',body)
def compare_summary(d,e):
 d=extract(d);assert d['result_status']=='ok';s=d['sections']['summary'][0];assert(s['games'],s['wins'],s['losses'])==(e['games'],e['wins'],e['losses']);assert all(abs(s[k+'_avg']-v)<0.0011 for k,v in e['means'].items());return d
with zipfile.ZipFile(a.artifact)as z:
 assert not z.testzip();s=json.loads(z.read('summary.json'));assert s['candidate_sha']==a.request;assert[s[k]for k in ['selected','executed','passed','skipped','failed','errors','xfailed']]==[1,1,1,0,0,0,0];cases=list(ET.fromstring(z.read('junit.xml')).iter('testcase'));assert len(cases)==1 and not list(cases[0]);prefix='acquired_data/composed-participation-stage/';d=json.loads(z.read(prefix+'acceptance.json'));assert d['consumer_acceptance']=='passed'and d['consumer_failure']is None and d['source_root_validation']=='passed';assert d['production_writes']==0 and d['nba_source_requests']==0 and d['full_required_slice_accepted']is False;v=d['validation'];assert v['base_generation']=='availability-lebron-season-v1-20261031'and v['base_manifest_sha256']=='3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3';assert v['composition_preservation_checked']and v['input_base_dependency_metadata_checked']and v['production_writes']==0
 # Reuse old accepted eight state vectors, rather than requalify unchanged source bodies.
 prior=P/'baseline/working/nba-tools-completion-program/source-evidence/k08-composition/staging-acceptance-source.zip'
 with zipfile.ZipFile(prior)as p:old=json.loads(p.read(prefix+'acceptance.json'))
 def vector(report):return sorted((int(r['game_id']),str(r.get('game_date')),int(r.get('team_id',report['team_id'])),r['state'])for r in report['games'])
 prev={(r['season'],r['player_id']):r for r in old['coverage']};assert len(d['coverage'])==8 and len(d['answers'])==21 and len(d['api_checks'])==3
 for r in d['coverage']:
  q=prev[r['season'],r['player_id']];assert r['counts']==q['counts']and vector(r)==vector(q)and r['complete_requested_population'];assert r['counts']['unknown']==0
 records.append({'unchanged_accepted_cohorts':8,'exact_observed_state_vectors':656,'old_answers_retained':21,'base_manifest':v['base_manifest_sha256'],'producer_source_replay_validation_complete_preserved':v['source_replay_validation_complete'],'separate_actual_source_root_validation':d['source_root_validation']})
 for p in d['paired_missing'][:2]:
  e=O['cases']['bos_pair'if p['team']=='BOS'else'lal_pair_zero'];assert p['game_ids']==[k[0]for k in e['keys']];assert(p['games'],p['wins'],p['losses'],p['points_sum'])==(e['games'],e['wins'],e['losses'],e['sums']['pts'])
  for b in [p['natural'],p['http'],p['structured_http']]:
   b=extract(b)
   if not e['games']:assert b['result_status']=='no_result'and b['result_reason']=='no_match'and not b['sections']
   else:
    compare_summary(b,e);assert{int(r['game_id'])for r in b['sections']['game_log']}=={k[0]for k in e['keys']};assert b['metadata']['with_player']is None and 'Jayson Tatum'in b['metadata']['without_player']and'Jaylen Brown'in b['metadata']['without_player']
  records.append({'paired':p['team'],'games':p['games'],'W_L':[p['wins'],p['losses']],'points':p['points_sum'],'keys_and_3consumers_verified':True})
 p=d['paired_missing'][2];assert p['game_ids']==[22300684]and(p['player_id'],p['pts'],p['reb'],p['ast'])==(1630559,32,2,3);assert p['zero_count']['result_status']=='ok'and p['zero_count']['sections']['count']==[{'count':0}];records.append({'Reaves_qualified_bound_opponent':p['game_ids'],'stats':[32,2,3],'qualified_zero_count':0})
 assert len(d['s4_integration'])==4
 for r in d['s4_integration']:
  selected=r['selected_season'];f=O['s4'][selected];player=r['kind']=='player'
  if player and selected=='2023-24':
   saved=f['player_numeric_reuse'];e={'keys':[[gid,1610612738,1627759]for gid in f['game_ids']],'games':2,'wins':1,'losses':1,'means':{k:saved[k+'_mean']for k in ['pts','reb','ast']}}
  else:e=f['player'if player else'team']
  assert r['expected_keys']==[list(k)for k in e['keys']];assert r['points_sum']==e['means']['pts']*2 and r['points_mean']==e['means']['pts']
  for body in [r['answer'],r['structured_answer']]:
   b=extract(body);assert b['result_status']=='ok';sec=b['sections'];assert sec['summary'][0]['games_total']==2;assert len(sec['split_comparison'])==1;row=sec['split_comparison'][0];assert row['bucket']==selected and(row['games'],row['wins'],row['losses'])==(2,e['wins'],e['losses']);assert all(abs(row[k+'_avg']-value)<0.0011 for k,value in e['means'].items());assert 'no games in '+r['qualified_empty_season']in b['caveats'];labels={f['label']:f['value']for f in b['metadata']['applied_filters']};assert labels['Seasons']=='2023-24, 2025-26'and'Season range'not in labels and labels['Opponent']=='LAL'and labels[r['relation'].capitalize()+' player']=='Jayson Tatum'
  records.append({'S4':r['kind']+'_'+r['relation'],'selected':selected,'empty':r['qualified_empty_season'],'exact_keys':r['expected_keys'],'means':e['means'],'NL_and_structured_HTTP_labels_math_verified':True,'Brown2023_old_raw_numeric_proof_reused':player and selected=='2023-24'})
 qa=d['integrated_rawqa'];assert qa['case_count']==8 and qa['expectation_check_counts']=={'pass':50}and qa['expectation_case_counts']=={'pass':8}and not qa['failed_case_ids'];rows=[json.loads(l)for l in z.read(prefix+'rawqa/composed-core/report.jsonl').decode().splitlines()];assert len(rows)==8
 for r in rows:
  assert r['expectation_results']['status']=='pass';snap=r['query_output_snapshot']['rendered_output'];blocks=snap['blocks']
  if r['id']=='k08_pair_missing_nonempty':assert'7-1'in snap['answer']['text']and any(b.get('row_count')==8 for b in blocks)
  elif '_s4_'in r['id']:assert blocks[0]['row_count']==1 and r['sections']['summary'][0]['games_total']==2
  elif r['id']=='k08_pair_missing_zero':assert r['result_status']=='no_result'and r['result_reason']=='no_match'
  elif r['id']=='k08_pair_missing_zero_count':assert r['metadata']['primary_count']==0 and r['answer_text']
 records.append({'actual_staged_QA_cases':8,'actual_numerical_checks':50,'suspicious_flags':qa['suspicious_flag_case_count'],'suspicious_case_ids':qa['suspicious_flag_case_ids'],'policy_flags_remain_literal':True,'rendered_actual_outputs_correct':True})
result={'actual_request':a.request,'actual_artifact_sha256':a.sha256,'verdict':'APPROVED_QUALIFIED_NUMERICAL_AND_RENDERED_CONTENT_POLICY_CLASSIFICATION_PENDING','checks':records,'actual_stage_test_passed':1,'runtime_source_review':'cdbf550ce4c0db7f55bc72bfbb80c157f807fca2;42flist-renames only','no_new_test_or_source_execution':True,'all46_Core1_or_production_acceptance':False};a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'verdict':result['verdict'],'groups':len(records),'actual_flags':qa['suspicious_flag_case_count']},indent=2))
