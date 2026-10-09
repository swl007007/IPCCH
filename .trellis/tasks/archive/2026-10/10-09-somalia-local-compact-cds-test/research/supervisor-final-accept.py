import csv
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

root = Path('/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/2.source_code/Step5_Geo_RF_trial/IPCCH')
task = root / '.trellis/tasks/10-09-somalia-local-compact-cds-test'
research = task / 'research'
def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()
def strict(path):
    def reject(value):
        raise ValueError(value)
    return json.loads(Path(path).read_text(), parse_constant=reject)
fresh = strict(research / 'supervisor-final-verify-command.json')
assert fresh['exit'] == 0 and fresh['code_stable'] and fresh['summary']['passed']
s = fresh['summary']
assert s['historical']['checks']['models_reloaded'] == 112 and s['launch']['checks']['models_reloaded'] == 20
assert s['historical']['checks']['batches'] == 28
assert s['historical']['checks']['metric_cells_replayed'] == 280 and s['historical']['checks']['delta_cells_replayed'] == 160
assert s['historical']['checks']['max_model_replay_abs_diff'] == s['launch']['checks']['max_model_replay_abs_diff'] == 0
assert s['frozen'] == {'frozen_files_checked': 491, 'frozen_files_changed': 0, 'frozen_files_missing': 0, 'frozen_files_added': 0}
hist = root / 'results/experiments/compact_climate_weather_oracle_v1_somalia_local'
launch = root / 'results/launch/nowcasting_2026_04_compact_cds_v1_somalia_local'
reports = [root / 'reports/compact_climate_weather_oracle_v1_somalia_local', root / 'reports/launch/nowcasting_2026_04_compact_cds_v1_somalia_local']
records = [hist / 'verification/verification.json', launch / 'verification.json']
items = [item for record in records for item in strict(record)['inventory']]
assert len(items) == 369 and len({x['path'] for x in items}) == len(items)
for item in items:
    p = Path(item['path'])
    assert p.stat().st_size == item['bytes'] and sha(p) == item['sha256'], p
actual = {str(p) for d in [hist, launch] + reports for p in d.rglob('*') if p.is_file()}
assert actual == {x['path'] for x in items} | {str(p) for p in records}
frozen = list(csv.DictReader((hist / 'preflight/frozen_inventory_before.csv').open()))
assert len(frozen) == 491 and len({x['path'] for x in frozen}) == 491
for item in frozen:
    p = Path(item['path'])
    assert p.stat().st_size == int(item['bytes']) and sha(p) == item['sha256'], p
for p in [reports[0] / 'model_run_codebook/IPCCH_compact_climate_weather_oracle_somalia_local_model_run_codebook_en.csv', reports[1] / 'model_run_codebook_en.csv']:
    text = p.read_text()
    assert 'This is an expected input, not a fitted result.' not in text
checkpoint = strict(research / 'final-execution-checkpoint.json')
assert checkpoint['executor']['session'] == '579e6ba5-f2a2-483c-b465-4b2e3cca1ed3'
assert checkpoint['verification']['passed']
for stage in checkpoint['stages']:
    assert stage['exit_status'] == 0 and stage['pins_unchanged']
    assert sha(task / stage['stdout']) == stage['stdout_sha256']
    assert sha(task / stage['stderr_log']) == stage['stderr_sha256']
tests = strict(research / 'supervisor-focused-tests.json')
assert tests['exit_code'] == 0 and tests['code_stable']
assert all(sha(root / p) == h for p, h in fresh['code_sha256'].items())
criteria = {
    'A1': 'Complete eligible SOM fit/eval/inference keys independently reconstructed; 905 members,4933 historical keys,5835 launch fitting rows,904 inference areas.',
    'A2': 'Seven historical runs/28 batches/112 models and five launch sets/20 models; complete fitted schema checks, shared H0.',
    'A3': 'All historical cohorts/truths/fit keys/targets/weights aligned; paired baseline feature cells independently checked.',
    'A4': 'Fresh 112-model replay difference0 and exact classes; all280 metrics/160 deltas, masks/reasons independently reproduced.',
    'A5': 'Complete launch projections, ordered5835 fit keys/targets/weights and904 inference rows, CDS prefixes/timing inherited from pinned accepted parents.',
    'A6': 'Fresh20-model replay difference0 and exact classes; independent phase shares/counts/population/cap/paired differences.',
    'A7': 'Seven PNGs individually viewed by supervisor; all11752 keyed plotted values and complete unique904-area geometry joins verified.',
    'A8': 'Actual fitted codebooks, reports, manifests/ledgers and complete369-item inventories rehashed;491 frozen artifacts independently rehashed unchanged.',
    'A9': 'Same verified Herdr Opus5.5(1M) session; command/exit/hash evidence checked; supervisor acceptance recorded; audit explicitly omitted by user.'
}
pins = {str(p.relative_to(root)): sha(p) for p in records + [research / 'supervisor-final-verify-command.json', research / 'final-execution-checkpoint.json', research / 'supervisor-historical-artifact-review.md', research / 'supervisor-launch-artifact-review.md', research / 'supervisor-audit-omission-check.json']}
data = {
    'status': 'accepted', 'acceptance_authority': 'Codex supervisor', 'accepted_utc': datetime.now(timezone.utc).isoformat(),
    'implementation_sha': 'e563b0bd2ac7fba1094c0e30f7f5d889a1c99fa4',
    'approved_plan_sha': '3ccf92a17dc94080ee2d2aa54618c2d123923d7a',
    'code_sha256': fresh['code_sha256'], 'criteria': {k: {'status': 'accepted', 'evidence': v} for k, v in criteria.items()},
    'fresh_verifier': {'exit': 0, 'elapsed_seconds': fresh['elapsed_seconds'], 'checks': s},
    'supervisor_inventory': {'files_rehashed': len(items), 'complete_current_output_files': len(actual), 'frozen_files_rehashed': len(frozen), 'seven_figures_visualized': sorted(p.name for p in (reports[1] / 'figures').glob('*.png'))},
    'evidence_sha256': pins, 'artifact_inventory': items,
    'focused_tests': {'passed': 32, 'evidence': 'research/supervisor-focused-tests.json', 'code_stable': True},
    'executor': {'name': 'somalia-local-executor', 'pane': 'w11:p4', 'terminal': 'term_65d6ae54981a13', 'session': checkpoint['executor']['session'], 'model': 'Opus 5.5 (1M context)'},
    'audit': 'No Trellis audit started; explicit user instruction. This acceptance is not an audit pass.',
    'reports': [str(reports[0] / 'report.md'), str(reports[1] / 'launch_summary.md')],
    'limitations': checkpoint['limitations'] + ['Independent saved-artifact consistency/replay, not independent retraining or a new upstream weather/reference/spatial certification. All pooled continuous R2 values are negative.'],
    'unrelated_dirty_paths_excluded': ['AGENTS.md', '.trellis/tasks/archive/2026-10/10-08-compact-cds-launch/research/final_verify_attempt1/superseded_figures/crisis_categorical_compact_cds_weather_12m_2027-04.png'],
    'next': 'Commit accepted evidence/spec update, then ordinary Trellis archive and journal; no push.'
}
(research / 'supervisor-final-acceptance.json').write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')
print(json.dumps({k: data[k] for k in ['status', 'accepted_utc', 'supervisor_inventory']}, indent=2))
