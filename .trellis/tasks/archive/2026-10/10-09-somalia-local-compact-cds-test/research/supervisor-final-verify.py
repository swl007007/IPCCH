import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

root=Path('/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/2.source_code/Step5_Geo_RF_trial/IPCCH')
research=root/'.trellis/tasks/10-09-somalia-local-compact-cds-test/research'
pins=json.loads((research/'preflight-checkpoint.json').read_text())['code']
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
assert all(sha(root/p)==d for p,d in pins.items())
records=[root/'results/experiments/compact_climate_weather_oracle_v1_somalia_local/verification/verification.json',
         root/'results/launch/nowcasting_2026_04_compact_cds_v1_somalia_local/verification.json']
for stage,path in zip(['historical','launch'],records):
    assert path.exists() and json.loads(path.read_text())['passed']
    shutil.copyfile(path,research/f'executor-final-verification-{stage}.json')
command=['/home/swl007007/.venvs/ipcch-geo/bin/python','scripts/modeling/run_somalia_local_compact_test.py','--verify']
env=dict(os.environ,PYTHONPATH='src',PYTHONDONTWRITEBYTECODE='1',MPLBACKEND='Agg',PATH='/tmp/ipcch-windows-git-bin:'+os.environ['PATH'])
start=time.time()
with (research/'supervisor-final-verify-stdout.json').open('w') as out, (research/'supervisor-final-verify.log').open('w') as err:
    result=subprocess.run(command,cwd=root,env=env,stdout=out,stderr=err)
summary=json.loads((research/'supervisor-final-verify-stdout.json').read_text())
stable=all(sha(root/p)==d for p,d in pins.items())
evidence={'command':command,'cwd':str(root),'exit':result.returncode,'elapsed_seconds':time.time()-start,'code_stable':stable,
          'code_sha256':pins,'summary':summary,'stdout_sha256':sha(research/'supervisor-final-verify-stdout.json'),
          'log_sha256':sha(research/'supervisor-final-verify.log'),'verification_records':{str(p):sha(p) for p in records},
          'scope':'fresh independent supervisor execution of all132-model, metric, population, map and frozen-parent verification; no fitting'}
(research/'supervisor-final-verify-command.json').write_text(json.dumps(evidence,indent=2)+'\n')
print(json.dumps(evidence,indent=2))
assert result.returncode==0 and stable and summary['passed']
assert summary['historical']['checks']['models_reloaded']==112 and summary['launch']['checks']['models_reloaded']==20
