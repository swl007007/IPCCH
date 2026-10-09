import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BUILD = REPO_ROOT / "scripts" / "preprocessing" / "build_compact_cds_launch_inputs.py"
RUN = REPO_ROOT / "scripts" / "modeling" / "run_compact_cds_launch.py"


def cli(script, *args):
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT / "src")}
    return subprocess.run([sys.executable, str(script), *args], cwd=REPO_ROOT, text=True, capture_output=True, check=False, env=env)


def test_run_cli_requires_an_explicit_stage():
    r = cli(RUN)
    assert r.returncode == 2 and "choose --validate-only" in r.stderr


def test_run_cli_refuses_existing_launch_namespaces_before_anything_else(tmp_path):
    r = cli(RUN, "--input-manifest", str(tmp_path / "m.json"), "--results-root", str(tmp_path / "nowcasting_2026_04" / "x"), "--validate-only")
    assert r.returncode != 0 and "existing launch namespace" in (r.stderr + r.stdout)
    assert not (tmp_path / "nowcasting_2026_04").exists()


def test_validate_only_with_an_incomplete_manifest_fails_and_writes_nothing(tmp_path):
    manifest = tmp_path / "m.json"
    manifest.write_text(json.dumps({"version": "compact_cds_launch_v1", "status": "BUILDING"}))
    out = tmp_path / "results"
    r = cli(RUN, "--input-manifest", str(manifest), "--results-root", str(out), "--reports-root", str(tmp_path / "reports"), "--validate-only")
    assert r.returncode == 1 and "not a COMPLETE" in r.stderr
    assert not out.exists() and not (tmp_path / "reports").exists()


def test_assemble_requires_an_accepted_weather_cube(tmp_path):
    r = cli(BUILD, "--assemble-only", "--input-root", str(tmp_path / "inputs"))
    assert r.returncode != 0 and "--weather-cube" in (r.stderr + r.stdout)
    cube = tmp_path / "cds_weather_cube.csv"
    cube.write_text("area_id\n1\n")
    (tmp_path / "cds_weather_provenance.json").write_text(json.dumps({"status": "REJECTED"}))
    r = cli(BUILD, "--assemble-only", "--input-root", str(tmp_path / "inputs"), "--weather-cube", str(cube))
    assert r.returncode != 0 and "not ACCEPTED" in (r.stderr + r.stdout)
    assert not (tmp_path / "inputs").exists()


def test_weather_stage_refuses_a_legacy_namespace(tmp_path):
    r = cli(BUILD, "--weather-only", "--weather-root", str(tmp_path / "compact_climate_weather_oracle_v1"))
    assert r.returncode != 0 and "legacy namespace" in (r.stderr + r.stdout)
