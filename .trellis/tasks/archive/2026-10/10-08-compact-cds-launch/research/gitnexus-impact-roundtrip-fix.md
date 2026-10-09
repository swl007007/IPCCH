# GitNexus impact for the save_csv/same_frame round-trip fix (2026-10-09 ~06:50 UTC)

impact(same_frame, upstream, repo IPCCH): Target not found (src/ipcch/compact_launch.py is new and not in the GitNexus index); risk UNKNOWN-by-index.
Executor note: the edit was applied before this impact call (record of order); callers below are all inside the new module, its verifier and the focused tests. No existing/indexed symbol was edited.

```
src/ipcch/compact_launch.py:509:        xn, yn = _numeric_or_none(x), _numeric_or_none(y)
src/ipcch/compact_launch.py:523:    if not same_frame(check, frame.reset_index(drop=True)):
src/ipcch/compact_launch.py:587:            "training_dataset": entry["dataset"], "fit_selection": save_csv(fit, input_root / "training" / f"fit_selection_{tag}.csv"),
src/ipcch/compact_launch.py:589:            "inference": save_csv(matrices[(arm, horizon)], input_root / "inference" / f"inference_{tag}.csv"),
src/ipcch/compact_launch.py:595:    out["ledgers"] = {f"history_h{h}": save_csv(led["history"][h], input_root / "ledgers" / f"history_h{h}.csv") for h in TARGETS}
src/ipcch/compact_launch.py:596:    out["ledgers"].update({f"idp_h{h}": save_csv(led["idp"][h], input_root / "ledgers" / f"idp_h{h}.csv") for h in TARGETS})
src/ipcch/compact_launch.py:597:    out["ledgers"]["season"] = save_csv(led["season"], input_root / "ledgers" / "season_h_all_origin_2026_04.csv")
src/ipcch/compact_launch.py:598:    out["ledgers"]["population"] = save_csv(led["population"], input_root / "ledgers" / "population_april_2026.csv")
src/ipcch/compact_launch.py:875:        written[names[level]] = save_csv(table, pop_dir / f"{names[level]}.csv")
src/ipcch/compact_launch.py:877:        written[f"{level}_paired_differences"] = save_csv(diff, pop_dir / f"{level}_population_paired_differences.csv")
src/ipcch/compact_launch.py:878:    written["country_population_cap_audit"] = save_csv(audit, pop_dir / "country_population_cap_audit.csv")
src/ipcch/compact_launch.py:1140:        if not same_frame(inf, pd.read_csv(manifest["runs"][rid]["inference"]["path"], float_precision="round_trip", low_memory=False)):
tests/unit/test_compact_launch.py:173:    info = cl.save_csv(frame, tmp_path / "cap.csv")
tests/unit/test_compact_launch.py:176:    assert cl.same_frame(back, frame)
tests/unit/test_compact_launch.py:177:    assert not cl.same_frame(back.assign(x=[1.0, 2.0]), frame)
tests/unit/test_compact_launch.py:180:    info = cl.save_csv(ledger, tmp_path / "ledger.csv")
tests/unit/test_compact_launch.py:182:    assert back["history_1_source_area_id"].dtype.kind == "f" and cl.same_frame(back, ledger)
tests/unit/test_compact_launch.py:183:    assert not cl.same_frame(back.assign(history_1_source_area_id=[0.0, np.nan, 8.0]), ledger)
tests/unit/test_compact_launch.py:184:    assert not cl.same_frame(back.assign(label=["a", "NB", np.nan]), ledger)
```

## Revision 2 (supervisor: narrower read-back dtype fix), ~06:55 UTC

Actual order: impact(save_csv, upstream, repo IPCCH) was run BEFORE this revision -> "Target 'save_csv' not found" (module not indexed;
risk UNKNOWN-by-index). Then the edit: `_numeric_or_none` removed; `same_frame` restored to its numeric-bitwise / text form;
`save_csv` read-back check now passes `dtype=str` for every column that is not numeric in the in-memory frame (object/string;
read_csv already returns such columns as text, so datetime/categorical behaviour is unchanged). CSV bytes written are unchanged;
`keep_default_na=False, na_values=[""]` kept. Object int/None source-ID columns now compare by their exact written text
("0" vs "0", missing vs missing); leading-zero labels such as "01" stay distinct from "1"; literal "NA" survives.
Regression: tests/unit/test_compact_launch.py::test_save_csv_keeps_literal_na_and_true_missing (object int/None IDs, "NA",
"01"/"007", 1e-10 numeric change rejected). Focused suites: 32 passed (unit compact_launch + smoke CLI + weather unit).
Attempt 2 (comparator `_numeric_or_none`) was stopped by SIGTERM before writing ledgers; log preserved as
results/launch/.../logs/assemble_attempt2_superseded_stopped.log.
