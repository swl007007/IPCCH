import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

root = Path('/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/2.source_code/Step5_Geo_RF_trial/IPCCH')
research = root / '.trellis/tasks/10-09-somalia-local-compact-cds-test/research'
files = ['scripts/modeling/run_somalia_local_compact_test.py', 'tests/unit/test_somalia_local_compact_test.py']
def hashes():
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in files}
command = ['/home/swl007007/.venvs/ipcch-geo/bin/python', '-m', 'pytest', 'tests/unit/test_somalia_local_compact_test.py', 'tests/unit/test_compact_launch.py', '-q', '-p', 'no:cacheprovider']
before = hashes()
started = time.time()
env = dict(os.environ, PYTHONPATH='src', PYTHONDONTWRITEBYTECODE='1', MPLBACKEND='Agg')
result = subprocess.run(command, cwd=root, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
after = hashes()
output = research / 'supervisor-focused-tests.log'
output.write_text(result.stdout, encoding='utf-8')
evidence = {'command': command, 'cwd': str(root), 'exit_code': result.returncode, 'elapsed_seconds': time.time()-started,
            'before_sha256': before, 'after_sha256': after, 'code_stable': before == after,
            'log': str(output), 'log_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
            'production_fitting': False, 'acceptance_scope': 'focused synthetic and frozen launch helper tests only'}
(research / 'supervisor-focused-tests.json').write_text(json.dumps(evidence, indent=2)+'\n', encoding='utf-8')
print(json.dumps(evidence, indent=2))
print(result.stdout[-4000:])
raise SystemExit(result.returncode if before == after else 2)
