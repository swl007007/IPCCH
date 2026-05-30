# Quickstart: Launch Forecast Scope

## Prerequisites

Run from the repository root with package imports available:

```bash
export PYTHONPATH=src
```

Do not run heavy training during automated validation unless explicitly requested.

## Inspect CLI

```bash
PYTHONPATH=src python scripts/modeling/run_launch_nowcasting_2026_04.py --help
```

Expected: help output includes `--scope {0,3,6}` with default scope 0 behavior.

## Validate default scope 0 behavior

```bash
PYTHONPATH=src python scripts/modeling/run_launch_nowcasting_2026_04.py \
  --validate-only \
  --scope 0 \
  --comprehensive-source "<path-to-source-csv>"
```

Expected:

- Scope 0 is accepted.
- Existing April 2026 same-period semantics remain intact.
- Output metadata can record `scope_months = 0` without breaking legacy output compatibility.

## Validate scope 3 semantics

```bash
PYTHONPATH=src python scripts/modeling/run_launch_nowcasting_2026_04.py \
  --validate-only \
  --scope 3 \
  --comprehensive-source "<path-to-source-csv>"
```

Expected:

- Feature period April 2026 targets July 2026.
- Launch prediction validation does not require July 2026 target or actual rows.
- Scoped training/evaluation validation uses `y(area_id, t)` with time-varying `X(area_id, t - 3 months)`.

## Validate scope 6 semantics

```bash
PYTHONPATH=src python scripts/modeling/run_launch_nowcasting_2026_04.py \
  --validate-only \
  --scope 6 \
  --comprehensive-source "<path-to-source-csv>"
```

Expected:

- Feature period April 2026 targets October 2026.
- Launch prediction validation does not require October 2026 target or actual rows.
- Scoped training/evaluation validation uses `y(area_id, t)` with time-varying `X(area_id, t - 6 months)`.

## Run targeted tests

```bash
PYTHONPATH=src pytest \
  tests/unit/test_launch_nowcasting.py \
  tests/unit/test_launch_visualizations.py \
  tests/unit/test_launch_comparison.py \
  tests/smoke/test_launch_cli.py
```

Expected coverage:

- CLI accepts only scopes 0, 3, 6.
- Scoped alignment direction is period-aware and area-aware.
- Static feature validation follows config-derived area-level invariance rules.
- Scope 3/6 launch predictions do not require future target/actual rows.
- Scope 0 actual-vs-predicted visualization remains available when actuals exist.
- Scope 3/6 predicted-only visualization works without future actuals.

## Output checks

After a scoped run, verify:

- Prediction outputs include feature period, target period, and scope metadata.
- Scope 3/6 paths or filenames do not overwrite scope 0.
- Actual-dependent metrics are marked unavailable, skipped, or omitted clearly when target-period actuals are missing.
- Forecast-only maps are still generated when actuals are unavailable.
