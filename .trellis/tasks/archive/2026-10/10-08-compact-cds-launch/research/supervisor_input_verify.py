"""Independent saved-input checks; run with the frozen model interpreter after assembly."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

repo = Path.cwd()
root = (repo / '../../../1.Source Data/assembled_IPCCH/model_ready/compact_cds_launch_v1').resolve()
manifest_path = root / 'compact_cds_launch_v1_manifest.json'
manifest = json.loads(manifest_path.read_text())
expected_runs = ['compact_baseline/0m', 'compact_baseline/6m', 'compact_baseline/12m',
                 'compact_cds_weather/6m', 'compact_cds_weather/12m']
assert manifest['status'] == 'COMPLETE' and set(manifest['runs']) == set(expected_runs)
assert manifest['training_label_cutoff_exclusive'] == '2026-04-01'
assert manifest['inference_ipc_history_max_month'] == '2026-03'
contract = pd.read_csv(root / 'approved_spec/expected_feature_contract.csv', keep_default_na=False)
contract_positions = [json.loads(x) if x else {} for x in contract['expected_model_positions']]
keys = ['area_id', 'year', 'month']
origin = 2026 * 12 + 3
cutoff = origin - 1
matrices, fits, checks = {}, {}, {}
population = pd.read_csv(manifest['ledgers']['population']['path'], float_precision='round_trip')
ids = population['area_id'].to_numpy()
assert len(ids) == 6188 and len(set(ids)) == 6188 and np.array_equal(ids, np.sort(ids))
assert np.isfinite(population['estimated_population']).all() and (population['estimated_population'] >= 0).all()
assert (population['estimated_population'] == 0).sum() == 6
for rid in expected_runs:
    entry = manifest['runs'][rid]
    expected = [str(contract.iloc[i]['predictor']) for _, i in sorted(
        (pos[rid], i) for i, pos in enumerate(contract_positions) if rid in pos)]
    assert entry['features'] == expected
    assert len(expected) == (308 if 'weather' in rid else 296)
    for role in ('inference', 'fit_selection', 'training_dataset'):
        item = entry[role]
        assert hashlib.sha256(Path(item['path']).read_bytes()).hexdigest() == item['sha256']
    matrix = pd.read_csv(entry['inference']['path'], float_precision='round_trip', low_memory=False)
    fit = pd.read_csv(entry['fit_selection']['path'], float_precision='round_trip')
    assert list(matrix) == keys + expected and np.array_equal(matrix['area_id'], ids)
    year, month = ((2027, 4) if entry['horizon'] == 12 else (2026, 10) if entry['horizon'] == 6 else (2026, 4))
    assert (matrix['year'] == year).all() and (matrix['month'] == month).all()
    for col in expected:
        if col.startswith('year_') or col.startswith('month_'):
            prefix, value = col.split('_')
            assert (matrix[col].astype(int) == int(int(value) == (year if prefix == 'year' else month))).all()
    assert matrix['popdensity'].isna().sum() == 4880
    fit_ord = fit['year'].to_numpy() * 12 + fit['month'].to_numpy() - 1
    assert fit_ord.max() == cutoff and (fit_ord < origin).all()
    assert np.array_equal(fit['fit_ord'], fit_ord) and np.array_equal(fit['age_months'], origin - fit_ord)
    assert np.allclose(fit['sample_weight'], 0.5 ** ((origin - fit_ord) / 24), atol=1e-15, rtol=0)
    assert len(fit) == 49532 and not fit[keys].duplicated().any()
    matrices[rid], fits[rid] = matrix, fit
    checks[rid] = {'areas': len(matrix), 'features': len(expected), 'fit_rows': len(fit), 'popdensity_na': 4880}
base = matrices['compact_baseline/0m']
noncal = [c for c in base if c not in keys and not c.startswith(('year_', 'month_'))]
for rid in expected_runs:
    assert base[noncal].equals(matrices[rid][noncal])
    assert fits[rid].equals(fits['compact_baseline/0m'])
for h in (6, 12):
    assert matrices[f'compact_cds_weather/{h}m'].iloc[:, :299].equals(matrices[f'compact_baseline/{h}m'])

source = (repo / '../../../1.Source Data/assembled_IPCCH/interim/IPCCH_2026_target_corrected_nino34_wbfood.csv').resolve()
labels = pd.read_csv(source, usecols=['admin_code', 'year', 'month', 'overall_phase'])
labels['ord'] = labels['year'] * 12 + labels['month'] - 1
labels = labels[(labels['ord'] <= cutoff) & labels['overall_phase'].isin([1, 2, 3, 4, 5])]
labels = labels.sort_values(['admin_code', 'ord'], ascending=[True, False])
labels['rank'] = labels.groupby('admin_code').cumcount() + 1
for h in (0, 6, 12):
    history = pd.read_csv(manifest['ledgers'][f'history_h{h}']['path'], float_precision='round_trip')
    assert np.array_equal(history['area_id'], ids)
    for rank in (1, 2, 3):
        selected = labels[labels['rank'] == rank].set_index('admin_code').reindex(ids)
        assert np.array_equal(history[f'history_{rank}_source_ord'], selected['ord'], equal_nan=True)
        assert np.array_equal(base[f'overall_phase_history_{rank}'], selected['overall_phase'], equal_nan=True)
    idp = pd.read_csv(manifest['ledgers'][f'idp_h{h}']['path'], float_precision='round_trip')
    assert np.array_equal(idp['area_id'], ids) and (idp['origin_ord'] == origin).all()
    assert (idp['idp_report_ord'].dropna() <= origin).all()
seasons = pd.read_csv(manifest['ledgers']['season']['path'])
assert np.array_equal(seasons['area_id'], ids) and (seasons['origin_ord'] == origin).all()
assert (seasons['season_cutoff_date'] == '2026-05-01').all()
for rank in (1, 2):
    assert (pd.to_datetime(seasons[f'gs_last{rank}_end_exclusive'].dropna()) <= pd.Timestamp('2026-05-01')).all()

provenance_path = Path(manifest['weather']['provenance']['path'])
provenance = json.loads(provenance_path.read_text())
assert provenance['status'] == 'ACCEPTED' and provenance['temperature_convention'] == 'end_inclusive'
assert provenance['overlap_gate']['passed']
assert provenance['support']['forecast_members'] == list(range(51))
assert provenance['support']['hindcast_members'] == {str(y): 25 for y in range(1993, 2017)}
for item in provenance['convention_evidence'].values():
    assert isinstance(item, dict) and hashlib.sha256(Path(item['path']).read_bytes()).hexdigest() == item['sha256']
cube = pd.read_csv(manifest['weather']['cube']['path'], float_precision='round_trip').set_index('area_id')
oracle = [c for c in matrices['compact_cds_weather/6m'] if c.startswith('oracle_')]
assert np.isfinite(cube[oracle]).all().all()
assert np.array_equal(matrices['compact_cds_weather/6m'][oracle], cube.reindex(ids)[oracle], equal_nan=True)
assert matrices['compact_cds_weather/6m'][oracle].equals(matrices['compact_cds_weather/12m'][oracle])
result = {'stage': 'supervisor_real_input_checkpoint', 'passed': True,
          'manifest': {'path': str(manifest_path), 'sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest()},
          'runs': checks, 'history': 'latest three phases independently reselected from pinned source through March2026',
          'weather': 'accepted full cube; exact keyed oracle substitution; both evidence comparisons preserved',
          'population_raw': float(population['estimated_population'].sum()),
          'future_perturbation': manifest['checks']['perturbation'], 'fitting_gate': 'eligible for sharedH0 pilot only'}
out = repo / '.trellis/tasks/10-08-compact-cds-launch/research/supervisor-input-acceptance.json'
out.write_text(json.dumps(result, indent=2, default=str))
print(json.dumps(result, indent=2, default=str))
