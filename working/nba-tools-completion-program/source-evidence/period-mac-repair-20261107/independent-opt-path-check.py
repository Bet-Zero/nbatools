from pathlib import Path
import os,subprocess,zipfile,json
root=Path('/workspace/nbatools')
base=root/'work/mac-independent/review/optpath-control'; base.mkdir(exist_ok=True)
package=root/'working/nba-tools-completion-program/source-evidence/period-mac-repair-20261107/NBA-Tools-Current123-Period-Capture-Mac-Fixed.zip'
with zipfile.ZipFile(package) as z: shell=z.read('Run Capture.command').decode()
for prefix in ('/opt/homebrew','/usr/local','/Library/Frameworks'):
    shell=shell.replace(prefix,str(base/'mac-root')+prefix)
script=base/'Run Capture.command';script.write_text(shell)
binpath=base/'bin';binpath.mkdir(exist_ok=True)
(binpath/'dirname').symlink_to('/usr/bin/dirname')
fake=base/'mac-root/opt/homebrew/opt/python@3.11/bin/python3.11'; fake.parent.mkdir(parents=True,exist_ok=True)
log=base/'calls.txt';fake.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> '+"'"+str(log)+"'"+'\nexit 0\n');fake.chmod(0o755)
r=subprocess.run(['/bin/sh',str(script)],input='\n',capture_output=True,text=True,env={**os.environ,'PATH':str(binpath),'VIRTUAL_ENV':''},timeout=10)
assert r.returncode==0,(r.stdout,r.stderr)
assert log.read_text().splitlines()==['-I -c import sys; assert sys.version_info >= (3, 8)','-I prepare_environment.py']
print(json.dumps({'controlled_optpath_shell':'PASS','mapping':'only Mac absolute prefixes mapped into scratch; other script bytes unchanged','selected':'/opt/homebrew/opt/python@3.11/bin/python3.11','helper_invocations':1,'nba_requests':0,'native_macos':False},indent=2))
