import hashlib
import json
from pathlib import Path
import subprocess
import sys
import pandas as pd
import numpy as np

root = Path('/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/2.source_code/Step5_Geo_RF_trial/IPCCH')
task = root / '.trellis/tasks/10-09-somalia-local-compact-cds-test'
research = task / 'research'
checkpoint = json.loads((research / 'preflight-checkpoint.json').read_text())
pre = checkpoint['preflight']
keys = ['area_id', 'year', 'month']
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
assert sys.executable == '/home/swl007007/.venvs/ipcch-geo/bin/python'
assert checkpoint['commands'][-1]['exit'] == 0
assert checkpoint['commands'][-1]['stdout_sha256'] == sha(research / 'preflight_validate_stdout.json')
assert checkpoint['commands'][-1]['log_sha256'] == sha(research / 'preflight_validate.log')
assert json.loads((research / 'preflight_validate_stdout.json').read_text()) == pre
for path, digest in {**checkpoint['code'], **checkpoint['frozen_code_and_config_sha256']}.items():
    assert sha(root / path) == digest, path
test = json.loads((research / 'supervisor-focused-tests.json').read_text())
assert test['exit_code'] == 0 and test['code_stable'] and test['after_sha256'] == checkpoint['code']
assert sha(test['log']) == test['log_sha256']
git = '/mnt/c/Program Files/Git/cmd/git.exe'
for name in ['prd.md', 'design.md', 'implement.md', 'expected_runs.csv', 'approval.md']:
    rel = f'.trellis/tasks/10-09-somalia-local-compact-cds-test/{name}'
    old = subprocess.run([git, 'show', f'3ccf92a:{rel}'], cwd=root, check=True, stdout=subprocess.PIPE).stdout
    assert old == (task / name).read_bytes(), name
    assert hashlib.sha256(old).hexdigest() == pre['historical']['spec_sha256'][f'approved_spec/{name}']
lookup = pd.read_csv(pre['membership']['path'], keep_default_na=False)
assert sha(pre['membership']['path']) == pre['membership']['sha256']
members = set(lookup.loc[lookup.iso3 == 'SOM', 'area_id'].astype(int))
assert len(members) == 905
source = Path(pre['membership']['path']).parent
hm = json.loads((source / 'model_ready/compact_climate_weather_oracle_v1/compact_climate_weather_oracle_v1_manifest.json').read_text())
cohort = pd.read_csv(hm['cohort']['path'])
assert sha(hm['cohort']['path']) == hm['cohort']['sha256']
som = cohort.area_id.isin(members)
ev = cohort.loc[som & cohort.eval_key]
assert len(ev) == 4933 and ev.area_id.nunique() == 905 and not ev.duplicated(keys).any()
annual = {int(y): len(g) for y, g in ev.groupby('year')}
assert annual == {2022:1129, 2023:1217, 2024:711, 2025:1876}
ords = cohort.year.to_numpy()*12 + cohort.month.to_numpy()-1
fit_proof = {}
for rid, entry in pre['historical']['runs'].items():
    h = int(rid.split('/')[1][:-1])
    for year in range(2022, 2026):
        cut = year*12-max(h,1)
        fit = cohort.loc[som & cohort.share_valid & (ords <= cut)]
        reported = entry['years'][str(year)]
        assert len(fit) == reported['fit_rows'] and fit.area_id.nunique() == reported['fit_areas']
        fit_proof[f'{rid}/{year}'] = {'rows':len(fit),'areas':int(fit.area_id.nunique()),'cutoff_ordinal':cut}
lm_path = Path(pre['launch']['parent_manifest']['path'])
assert sha(lm_path) == pre['launch']['parent_manifest']['sha256']
lm = json.loads(lm_path.read_text())
want_launch = cohort.loc[som & cohort.share_valid & (ords < 2026*12+3), keys].reset_index(drop=True)
assert len(want_launch) == 5835
launch_proof = {}
for rid, entry in lm['runs'].items():
    if rid not in pre['launch']['runs']:
        continue
    selection = pd.read_csv(entry['fit_selection']['path'], float_precision='round_trip')
    local = selection.loc[selection.area_id.isin(members)].reset_index(drop=True)
    assert local[keys].equals(want_launch), rid
    u = local.year.to_numpy()*12+local.month.to_numpy()-1
    assert np.array_equal(local.fit_ord.to_numpy(),u)
    assert np.array_equal(local.age_months.to_numpy(),2026*12+3-u)
    assert np.allclose(local.sample_weight,0.5**((2026*12+3-u)/24),atol=1e-15,rtol=0)
    inference = pd.read_csv(entry['inference']['path'],usecols=keys)
    ids = inference.loc[inference.area_id.isin(members)].area_id.astype(int)
    assert len(ids)==904 and ids.nunique()==904 and members-set(ids)=={3146}
    assert len(entry['features']) == pre['launch']['runs'][rid]['feature_count']
    launch_proof[rid]={'fit_rows':len(local),'fit_areas':int(local.area_id.nunique()),'inference_areas':len(ids)}
pop = pd.read_csv(lm['ledgers']['population']['path'], float_precision='round_trip')
pop = pop.loc[pop.area_id.isin(members)]
assert len(pop)==904 and set(pop.area_id.astype(int))==members-{3146}
total = float(pop.estimated_population.sum())
assert total==62695007
factor=0.95*19654739/total
assert abs(factor-pre['launch']['checks']['cap_factor']) < 1e-15
assert abs(float((pop.estimated_population*factor).sum())-18672002.05)<1e-6
assert not any(Path(p).exists() for p in pre['roots_exist'])
out={'passed':True,'scope':'independent checkpoint hashes, approved-spec bytes, complete keyed cohorts, cutoff counts, April weights, population and no local roots',
     'production_fitting':False,'code_sha256':checkpoint['code'],'frozen_code_configs_checked':len(checkpoint['frozen_code_and_config_sha256']),
     'members':len(members),'historical_eval_rows':len(ev),'annual_rows':annual,'historical_fit_counts':fit_proof,'launch':launch_proof,
     'population_raw':total,'population_factor':factor,'population_effective':float((pop.estimated_population*factor).sum()),
     'limits':'raw GRIB/provider/vintage verification remains inherited; complete matrices were checked by frozen parent/local preflight gates'}
(research/'supervisor-preflight-check.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
