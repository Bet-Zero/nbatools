"""Offline review of the exact frozen launcher package; no source requests."""
from pathlib import Path
from zipfile import ZipFile
import contextlib,hashlib,importlib.util,io,json,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent
E=OUT.parent
sha=lambda b:hashlib.sha256(b).hexdigest()
binding=json.loads((E/'package-binding.json').read_bytes())
package=E/binding['bundle_file']
assert sha(package.read_bytes())==binding['owner_bundle_sha256']=='5156e94b425ded08573ca8138d53d4a9cfb35e2aa856d3a902c654b4bb5b3e44'
request=json.loads((ROOT/binding['request_reference']).read_bytes())
assert sha((ROOT/binding['request_reference']).read_bytes())==binding['request_file_sha256']
checks=[]
with tempfile.TemporaryDirectory(prefix='period-checker-') as tmp:
 folder=Path(tmp)
 with ZipFile(package) as z:
  assert set(z.namelist())=={'run_capture.py','Run Capture.command','Run Capture.bat','READ ME.txt'}
  assert z.testzip() is None
  for name in z.namelist():assert not Path(name).is_absolute() and '..' not in Path(name).parts
  assert (z.getinfo('Run Capture.command').external_attr>>16)&0o111==0o111
  source=z.read('run_capture.py');assert sha(source)==binding['package_sha256']
  mac=z.read('Run Capture.command');win=z.read('Run Capture.bat');readme=z.read('READ ME.txt').decode()
  assert b'\r\n' in win and b'pip install' not in source+mac+win and b'git clone' not in source+mac+win
  assert 'installs nothing' in readme and 'even if capture stops or fails' in readme
  path=folder/'run_capture.py';path.write_bytes(source)
  command=folder/'Run Capture.command';command.write_bytes(mac)
  subprocess.run(['sh','-n',str(command)],check=True)
 spec=importlib.util.spec_from_file_location('independent_frozen_package',path)
 mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 assert mod.EMBEDDED_REQUEST==request
 assert mod.validate_request(mod.EMBEDDED_REQUEST)==mod.EMBEDDED_SHA256==binding['request_sha256']
 assert binding['collector_sha256']==sha((ROOT/'tools/collect_rollover_readiness_laptop.py').read_bytes())
 checks.append('exact package/source/raw+canonical request/collector hashes; 196 embedded jobs; safe four-member ZIP; Mac executable syntax; Windows CRLF; no installs')
 mod.version=lambda _: 'offline-review-not-source'
 mod.time.sleep=lambda _:None
 mod.time.monotonic=lambda:0
 calls=[]
 class Response:
  status_code=200
  def __init__(self,raw,failure=False):self.raw=raw;self.failure=failure
  def __enter__(self):return self
  def __exit__(self,*_):return False
  def iter_content(self,_):
   yield self.raw
   if self.failure:raise TimeoutError('offline injected timeout after retained partial bytes')
  def raise_for_status(self):pass
 class HTTP:
  headers={}
  def get_session(self):return self
  def get(self,**kwargs):
   calls.append(kwargs)
   assert kwargs['timeout']==30 and kwargs['allow_redirects'] is False and kwargs['stream'] is True
   return response_factory(len(calls),kwargs)
 http=HTTP()
 mod._client=lambda job:(http,'https://stats.nba.com/stats/'+job['endpoint'])
 response_factory=lambda n,kw:Response(b'{"qualified":false,"offline_response":1}' if n==1 else b'{"partial":',n==2)
 output=folder/'failure'
 with contextlib.redirect_stdout(io.StringIO()):report=mod.collect(output,request)
 assert len(calls)==2 and len(report['attempts'])==2 and len(report['unattempted_jobs'])==194
 assert report['attempts'][0]['transport_complete'] and not report['attempts'][1]['transport_complete']
 assert not report['canonical_period_accepted'] and report['production_writes']==0
 originals={j['source_file']:(output/j['source_file']).read_bytes() for j in request['jobs'][:2]}
 assert originals[request['jobs'][1]['source_file']]==b'{"partial":'
 with ZipFile(output/'collection.zip') as z:
  for name,raw in originals.items():assert z.read(name)==raw
  assert json.loads(z.read('acquisition.json'))==report
 with contextlib.redirect_stdout(io.StringIO()):again=mod.collect(output,request)
 assert len(calls)==2 and again['stop_reason']=='failure_return_output_do_not_retry'
 for name,raw in originals.items():assert (output/name).read_bytes()==raw
 checks.append('first valid JSON transport body and second partial timeout body remain byte-exact in loose files+portable ZIP; 194 exact unattempted jobs; rerun makes zero extra calls')
 calls.clear()
 response_factory=lambda n,kw:Response(json.dumps({'offline_response':n,'parameters':kw['params']}).encode())
 times=iter([0,0,0,1200])
 mod.time.monotonic=lambda:next(times)
 output=folder/'elapsed'
 with contextlib.redirect_stdout(io.StringIO()):first=mod.collect(output,request)
 assert len(calls)==1 and first['stop_reason']=='elapsed_limit' and len(first['unattempted_jobs'])==195
 saved=(output/request['jobs'][0]['source_file']).read_bytes()
 mod.time.monotonic=lambda:0
 # Tampering is detected before any additional request.
 (output/request['jobs'][0]['source_file']).write_bytes(b'changed')
 try:mod.collect(output,request)
 except ValueError as exc:assert 'Prior source bytes changed' in str(exc)
 else:raise AssertionError('tampered original accepted')
 assert len(calls)==1
 (output/request['jobs'][0]['source_file']).write_bytes(saved)
 with contextlib.redirect_stdout(io.StringIO()):complete=mod.collect(output,request)
 assert complete['transport_finished'] and len(calls)==196 and len(complete['attempts'])==196 and not complete['unattempted_jobs']
 assert (output/request['jobs'][0]['source_file']).read_bytes()==saved
 assert [dict(c['params']) for c in calls]==[j['parameters'] for j in request['jobs']]
 assert not complete['canonical_period_accepted'] and complete['production_writes']==0
 checks.append('elapsed stop preserves first response; tampering aborts before calls; safe continuation makes exactly 195 remaining calls; 196 total unique exact jobs; transport completion remains unqualified/unpublished')
result={'reviewer':'/root/period_source_checker','model':'not exposed by runtime','reviewed_revision':'66e8ab4c41f308f566ba38059809c37ccfc80c24','package_sha256':binding['owner_bundle_sha256'],'script_sha256':binding['package_sha256'],'source_requests':0,'offline_mock_calls':198,'checks':checks,'decision':'approved','scope':'Exact 196-job acquisition/transfer package only. No new source bytes or period source qualification; 98 windows remain missing. Existing 123-game v3 and prior application acceptance preserved.'}
(OUT/'frozen-package-review.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
