import hashlib, json, os, pathlib, runpy, subprocess, zipfile
from unittest.mock import patch
root=pathlib.Path('/workspace/nbatools')
scratch=root/'work/mac-independent/review/final-opt'; scratch.mkdir(exist_ok=True)
package=root/'working/nba-tools-completion-program/source-evidence/period-mac-repair-20261107/NBA-Tools-Current123-Period-Capture-Mac-Fixed.zip'
assert hashlib.sha256(package.read_bytes()).hexdigest()=='b6f4d4f156608008bd04b0573f13c1b8223b3bf75ddc2cc5dbad013e9f859e40'
original=root/'working/nba-tools-completion-program/source-evidence/period-acquisition-20261107/NBA-Tools-Current123-Period-Capture.zip'
location=scratch/'Actual extracted Mac with spaces'; location.mkdir(exist_ok=True)
with zipfile.ZipFile(package) as z,zipfile.ZipFile(original) as old:
    assert z.testzip() is None
    for name in ('run_capture.py','Run Capture.bat'): assert z.read(name)==old.read(name)
    assert z.getinfo('Run Capture.command').external_attr>>16==0o100755
    z.extractall(location)
mac_text=(location/'Run Capture.command').read_text()
for minor in (11,12,13):
    for prefix in ('/opt/homebrew','/usr/local'):
        assert f'{prefix}/opt/python@3.{minor}/bin/python3.{minor}' in mac_text
assert mac_text.index('/opt/homebrew/opt/python@3.11') < mac_text.index('python3.12')
ns=runpy.run_path(str(location/'prepare_environment.py'),run_name='offline_independent_review')
plan=json.loads((root/'working/nba-tools-completion-program/collection-requests/current123-new16-periods-20261107.json').read_bytes())
assert ns['REQUEST']==plan and len(plan['jobs'])==196
assert '"--no-cache-dir"' in (location/'prepare_environment.py').read_text()
assert hashlib.sha256((location/'prepare_environment.py').read_bytes()).hexdigest()=='d7ec68c28d6f0537b3a76c366c037f5596dc1e0cac7e8ef13e6876b20f35a65d'
assert hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':')).encode()).hexdigest()=='19cc7759dd2dec7676888538b574e3dd316d6b58712b2b30d42c9b92911a9a52'
# Re-run full real offline endpoint admission from the frozen helper, no NBA network.
details=ns['probe'](str(root/'.venv/bin/python'),location/'run_capture.py')
assert details=={'python':'3.12.14','nba_api':'1.11.4'},details
# Shell's first admitted runtime is the retained local venv, without owner PATH work.
venv=location/'.venv/bin'; venv.mkdir(parents=True,exist_ok=True)
log=scratch/'shell calls.txt'
fake=venv/'python'; fake.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> '+"'"+str(log)+"'"+'\nexit 0\n'); fake.chmod(0o755)
if log.exists():log.unlink()
result=subprocess.run(['sh',str(location/'Run Capture.command')],input='\n',text=True,capture_output=True,env={**os.environ,'PATH':'/usr/bin:/bin','VIRTUAL_ENV':''},timeout=10)
assert result.returncode==0,result.stderr
assert log.read_text().splitlines()==['-I -c import sys; assert sys.version_info >= (3, 8)','-I prepare_environment.py']
# Exercise final helper's real error path; no process allowed to reach transport.
main_globals=ns['main'].__globals__
with patch.dict(main_globals,{'prepare':lambda *args: (_ for _ in ()).throw(RuntimeError('controlled private setup refusal'))}):
    assert ns['main']()==1
output=location/'readiness-capture/collection.zip'; preserved=output.read_bytes()
with zipfile.ZipFile(output) as z:
    report=json.loads(z.read('acquisition.json')); manifest=json.loads(z.read('collection-manifest.json'))
    assert report['attempts']==[] and len(report['unattempted_jobs'])==196
    assert report['request']==plan and report['production_writes']==0 and report['canonical_period_accepted'] is False
    assert report['environment']['reason']=='controlled private setup refusal'
    assert report['stop_reason']=='environment_setup_failed_return_output_do_not_retry'
    for name, info in manifest['files'].items():
        raw=z.read(name); assert len(raw)==info['bytes']; assert hashlib.sha256(raw).hexdigest()==info['sha256']
with patch.dict(main_globals,{'prepare':lambda *args: (_ for _ in ()).throw(AssertionError('must not rerun'))}):
    assert ns['main']()==1
assert output.read_bytes()==preserved
# Checked fallback receipt explicitly says prep-time, not actual laptop/source timestamp.
with zipfile.ZipFile(location/'environment-failure.zip') as z:
    fallback=json.loads(z.read('acquisition.json'))
    assert fallback['attempts']==[] and len(fallback['unattempted_jobs'])==196
    assert fallback['environment']['receipt_time_basis']=='package_preparation_not_laptop_capture'
print(json.dumps({'verdict':'APPROVED','package_sha256':hashlib.sha256(package.read_bytes()).hexdigest(),'helper_sha256':hashlib.sha256((location/'prepare_environment.py').read_bytes()).hexdigest(),'actual_offline196_sdk':details,'collector_and_windows':'byte-identical toPR600','mac_shell':'actual sh executed with spacedpath+retainedlocalvenv; helper once','failures':'actual embeddedhelper produces hashvalid portable zeroattempt196unattempted receipt; existingbytes preserved and no retry','fallback':'prep-time provenance explicit','nba_requests_executed':0,'new_period_windows':0,'production_writes':0,'native_macos':'unavailable; Linuxshell/runtime checks only','checker':'/root/mac_environment_checker','backend_model':'unavailable'},indent=2))
