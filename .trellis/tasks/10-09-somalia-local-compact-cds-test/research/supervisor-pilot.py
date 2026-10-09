import hashlib
import json
from pathlib import Path
import time
import numpy as np
import pandas as pd
import xgboost as xgb
from ipcch.origin_safe import SHARE_COLUMNS, CUMULATIVE_TARGETS, PRED_COLUMNS, REQUIRED_BATCH_ARTIFACTS

start=time.time()
root=Path('/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/2.source_code/Step5_Geo_RF_trial/IPCCH')
research=root/'.trellis/tasks/10-09-somalia-local-compact-cds-test/research'
results=root/'results/experiments/compact_climate_weather_oracle_v1_somalia_local'
run=results/'runs/compact_baseline/0m'
batch=run/'batches/2022'
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
pre=json.loads((research/'preflight-checkpoint.json').read_text())['preflight']
local_path=results/'inputs/compact_climate_weather_oracle_v1_somalia_local_manifest.json'
assert sha(local_path)==pre['historical']['local_manifest_sha256_if_written']
local=json.loads(local_path.read_text())
assert sha(local['local_code']['script'])==local['local_code']['sha256']==pre['local_code']['sha256']
for item in local['files'].values():
    assert sha(item['path'])==item['sha256']
record=json.loads((batch/'batch_record.json').read_text())
meta=json.loads((run/'run_metadata.json').read_text())
assert meta['status']=='PARTIAL' and meta['batches']==[record]
assert record['fingerprint']==meta['fingerprint']==pre['historical']['runs']['compact_baseline/0m']['local_fingerprint']
payload=meta['fingerprint_payload']
assert hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()==record['fingerprint']
assert meta['local_manifest']['sha256']==sha(local_path)
assert set(record['artifacts'])==set(REQUIRED_BATCH_ARTIFACTS)
for name,digest in record['artifacts'].items():
    assert sha(batch/name)==digest,name
parent=json.loads(Path(local['parent']['manifest']['path']).read_text())
entry=parent['horizons']['0']['arms']['compact_baseline']
features=entry['features']
assert len(features)==296 and features==meta['features']
assert sha(entry['dataset']['path'])==entry['dataset']['sha256']
data=pd.read_csv(entry['dataset']['path'],float_precision='round_trip',low_memory=False)
lookup=pd.read_csv(local['membership']['path'],keep_default_na=False)
members=set(lookup.loc[lookup.iso3=='SOM','area_id'].astype(int))
shares=data[list(SHARE_COLUMNS)].to_numpy(dtype=float)
valid=np.isfinite(shares).all(axis=1)&(shares>=0).all(axis=1)&(shares.sum(axis=1)>0)&data.overall_phase.isin([1,2,3,4,5]).to_numpy()
ords=data.year.to_numpy()*12+data.month.to_numpy()-1
fit=data.area_id.isin(members).to_numpy()&valid&(ords<=2022*12-1)
keys=['area_id','year','month']
fk=pd.read_csv(batch/'fit_keys.csv.gz',float_precision='round_trip')
assert fk[keys].equals(data.loc[fit,keys].reset_index(drop=True)) and len(fk)==901 and fk.area_id.nunique()==139
assert np.array_equal(fk.age_months.to_numpy(),2022*12-ords[fit])
assert np.allclose(fk.sample_weight,0.5**((2022*12-ords[fit])/24),atol=1e-15,rtol=0)
cohort=pd.read_csv(parent['cohort']['path'])
evaluate=cohort.eval_key.to_numpy()&data.area_id.isin(members).to_numpy()&(data.year.to_numpy()==2022)
pred=pd.read_csv(batch/'predictions.csv',float_precision='round_trip')
assert pred[keys].equals(data.loc[evaluate,keys].reset_index(drop=True)) and len(pred)==1129
assert np.array_equal(pred.overall_phase,data.loc[evaluate,'overall_phase'].to_numpy())
norm=shares[evaluate]/shares[evaluate].sum(axis=1,keepdims=True)
targets=np.column_stack([norm[:,i:].sum(axis=1) for i in range(1,5)])
assert np.allclose(pred[list(CUMULATIVE_TARGETS)],targets,atol=1e-12,rtol=0)
dm=xgb.DMatrix(data.loc[evaluate,features],feature_names=features,nthread=16)
replayed={}
checks=[]
for target,col in zip(CUMULATIVE_TARGETS,PRED_COLUMNS):
    booster=xgb.Booster()
    booster.load_model(str(batch/f'model_{target}.ubj'))
    assert booster.feature_names==features
    replayed[col]=booster.predict(dm).astype(float)
    error=float(np.max(np.abs(replayed[col]-pred[col].to_numpy(dtype=float))))
    assert error<=1e-6 and np.isfinite(replayed[col]).all()
    checks.append({'target':target,'model_sha256':sha(batch/f'model_{target}.ubj'),'features':len(features),'rounds':booster.num_boosted_rounds(),'max_abs_diff':error})
classes=np.ones(len(pred),dtype=int)
for k,col in zip(range(2,6),PRED_COLUMNS):
    classes[replayed[col]>=0.2]=k
assert np.array_equal(classes,pred.overall_phase_pred.to_numpy())
assert record['fit_origin_month']=='2022-01' and record['fit_label_cutoff_month']=='2021-12'
assert record['fit_rows']==901 and record['eval_rows']==1129
launch=root/'results/launch/nowcasting_2026_04_compact_cds_v1_somalia_local'
assert not (launch/'runs').exists() and not (launch/'inputs').exists()
assert (launch/'preflight/frozen_inventory_before.csv').read_bytes()==(results/'preflight/frozen_inventory_before.csv').read_bytes()
assert sum(1 for _ in results.rglob('model_*.ubj'))==4
out={'passed':True,'scope':'independent four-model H0/2022 pilot replay and complete fit/eval key/weight/target/schema checks',
     'manifest_sha256':sha(local_path),'fingerprint':record['fingerprint'],'fit_rows':len(fk),'fit_areas':int(fk.area_id.nunique()),'eval_rows':len(pred),
     'classes_exact':True,'models':checks,'elapsed_seconds':time.time()-start,'script_sha256':local['local_code']['sha256'],'full_task_acceptance':False}
(research/'supervisor-pilot-replay.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
