Status: DONE_WITH_CONCERNS

Commits:
- `5c2cb85` - `feat: write nowcast panel shapefile package`

Files changed:
- `src/ipcch/nowcast_panel_export.py`
- `tests/unit/test_nowcast_panel_export.py`

Verification:
- Failed as requested in the Windows-Python/geospatial path:
  - Command: `PYTHONDONTWRITEBYTECODE=1 /mnt/c/Users/swl00/AppData/Local/Microsoft/WindowsApps/python3.12.exe -c "import sys, pytest; sys.path.insert(0, 'src'); raise SystemExit(pytest.main(['tests/unit/test_nowcast_panel_export.py','-v']))"`
  - Output: `WSL (2 - ) ERROR: UtilBindVsockAnyPort:287: socket failed 1`
  - Result: blocked by the WSL bridge before pytest could start.
- Passed syntax check with system Python:
  - Command: `python3 -m py_compile src/ipcch/nowcast_panel_export.py tests/unit/test_nowcast_panel_export.py`
  - Output: no output, exit code 0.
- Passed non-geospatial functional subset with system Python:
  - Command: `python3 -c "import sys; sys.path.insert(0, 'src'); import pandas as pd; from pathlib import Path; from ipcch.nowcast_panel_export import build_panel, load_country_lookup, validate_output_conflicts, PANEL_FILENAME, SUMMARY_FILENAME, GEOMETRY_BASENAME, NowcastPanelExportError; pred = pd.DataFrame([{'test_year':2025,'area_id':'10','year':2025,'month':1,'date':'2025-01-01','overall_phase':2,'overall_phase_pred':3,'phase2_worse':0.4,'phase3_worse':0.2,'phase4_worse':0.0,'phase5_worse':0.0,'phase2_pred':0.5,'phase3_pred':0.25,'phase4_pred':0.1,'phase5_pred':0.0}]); lookup = pd.DataFrame([{'area_id':'10','iso3':'LSO','country':'Lesotho'}]); panel = build_panel(pred, lookup, ['LSO']); assert panel['iso3'].tolist()==['LSO']; out = validate_output_conflicts(Path('/tmp/nowcast-panel-export-check'), overwrite=True); assert out.panel_csv.name == PANEL_FILENAME and out.summary_json.name == SUMMARY_FILENAME and out.geometry_shp.name == f'{GEOMETRY_BASENAME}.shp'; print('subset-ok')"`
  - Output: `subset-ok`

Concerns:
- The requested Windows-Python pytest invocation could not run in this environment because the WSL bridge failed before Python started, so the new geopandas/shapely-backed tests were not executed here.
- The code paths for geometry joins and export packaging are implemented and syntax-checked, but the end-to-end geospatial test surface still needs a successful run in an environment where the Windows Python bridge works.

## Fix update

Commit hash: `6b2011a` (`fix: record repaired geometries in nowcast export`)

Files changed:
- `src/ipcch/nowcast_panel_export.py`
- `tests/unit/test_nowcast_panel_export.py`

Tests run:
- `"/mnt/c/Users/swl00/AppData/Local/Microsoft/WindowsApps/python3.12.exe" -c "import sys, pytest; sys.path.insert(0, 'src'); raise SystemExit(pytest.main(['tests/unit/test_nowcast_panel_export.py','-v']))"`
- `python3 -m py_compile src/ipcch/nowcast_panel_export.py tests/unit/test_nowcast_panel_export.py`

Output summary:
- Requested pytest command failed before Python startup with `WSL (2 - ) ERROR: UtilBindVsockAnyPort:287: socket failed 1`.
- `py_compile` completed successfully with exit code 0.

Concerns:
- The requested pytest surface still needs a working Windows-Python bridge or a geospatial-capable Python environment to execute the geopandas-backed unit tests.
