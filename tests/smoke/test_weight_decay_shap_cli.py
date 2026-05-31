import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "modeling" / "run_deep_feature_weight_decay_forecasting.py"


def run_cli(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_help_includes_shap_options():
    result = run_cli("--help")
    assert result.returncode == 0
    help_text = result.stdout
    for option in (
        "--enable-shap",
        "--variable-crosswalk-path",
        "--variable-crosswalk-key",
        "--crosswalk-feature-column",
        "--crosswalk-category-column",
        "--shap-sample",
        "--allow-unmapped-shap-features",
        "--save-raw-shap",
        "--raw-shap-max-rows",
        "--allow-large-raw-shap",
    ):
        assert option in help_text


def test_help_has_no_local_absolute_dropbox_defaults():
    result = run_cli("--help")
    assert result.returncode == 0
    assert "C:\\Users" not in result.stdout
    assert "IFPRI Dropbox" not in result.stdout


def test_shap_disabled_does_not_require_crosswalk_path(tmp_path):
    dataset = tmp_path / "missing_dataset.csv"
    result = run_cli("--dataset", str(dataset), "--dry-run")
    assert result.returncode != 0
    assert "six_category_feature_crosswalk" not in result.stderr


def test_shap_enabled_resolves_crosswalk_before_training(tmp_path):
    dataset = tmp_path / "missing_dataset.csv"
    missing_crosswalk = tmp_path / "missing_crosswalk.csv"
    result = run_cli(
        "--dataset",
        str(dataset),
        "--enable-shap",
        "--variable-crosswalk-path",
        str(missing_crosswalk),
        "--dry-run",
    )
    assert result.returncode != 0
    assert str(missing_crosswalk) in result.stderr


def test_explicit_crosswalk_path_overrides_key(tmp_path):
    dataset = tmp_path / "missing_dataset.csv"
    missing_crosswalk = tmp_path / "explicit_missing_crosswalk.csv"
    result = run_cli(
        "--dataset",
        str(dataset),
        "--enable-shap",
        "--variable-crosswalk-key",
        "not_a_real_key",
        "--variable-crosswalk-path",
        str(missing_crosswalk),
        "--dry-run",
    )
    assert result.returncode != 0
    assert str(missing_crosswalk) in result.stderr
    assert "not_a_real_key" not in result.stderr


def test_raw_export_flags_are_visible_in_help():
    result = run_cli("--help")
    assert result.returncode == 0
    assert "--save-raw-shap" in result.stdout
    assert "--raw-shap-max-rows" in result.stdout
    assert "--allow-large-raw-shap" in result.stdout
