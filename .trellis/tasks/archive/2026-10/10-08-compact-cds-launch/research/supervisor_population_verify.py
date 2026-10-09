"""Supervisor saved-output check using scalar arithmetic/math.fsum, no production reporting imports.

Run from repository root in the frozen model interpreter after reporting has completed.
The population ledger was independently matched to the complete pinned April source at the input checkpoint;
the production final verifier additionally rereads that original source. This check rehashes the ledger.
"""
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("results/launch/nowcasting_2026_04_compact_cds_v1")
REPORT = Path("reports/launch/nowcasting_2026_04_compact_cds_v1")
RESEARCH = Path(".trellis/tasks/10-08-compact-cds-launch/research")
MANIFEST = Path("../../../1.Source Data/assembled_IPCCH/model_ready/compact_cds_launch_v1/compact_cds_launch_v1_manifest.json")
NAMES = [f"phase{k}" for k in range(1, 6)] + ["p3plus", "p4plus"]
BASE, WEATHER = "compact_baseline", "compact_cds_weather"
KEY = {"area": "area_id", "country": "country", "region": "region", "global": "scope"}
FILES = {"area": "area_population_predictions", "country": "country_population_summary",
         "region": "regional_population_summary", "global": "global_population_summary"}
checks, maxima, checked = {}, {}, 0


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return pd.read_csv(path, float_precision="round_trip", keep_default_na=False, na_values=[""])


def match(name, actual, expected):
    global checked
    a, b = np.asarray(actual, dtype=float), np.asarray(expected, dtype=float)
    assert a.shape == b.shape, (name, a.shape, b.shape)
    assert np.array_equal(np.isnan(a), np.isnan(b)), (name, "undefined mask")
    mask = ~np.isnan(b)
    diff = float(np.max(np.abs(a[mask] - b[mask]))) if mask.any() else 0.0
    share = "share_" in name or "percent" in name or "pp_difference" in name
    atol, rtol = (1e-10, 0.0) if "percent" in name or "pp_difference" in name else (1e-12, 0.0) if share else (1e-6, 1e-12)
    assert np.allclose(a[mask], b[mask], atol=atol, rtol=rtol), (name, diff)
    maxima["map" if "percent" in name or "pp_difference" in name else "share" if share else "people"] = max(
        diff, maxima.get("map" if "percent" in name or "pp_difference" in name else "share" if share else "people", 0.0))
    checked += a.size


m = json.loads(MANIFEST.read_text())
ledger = m["ledgers"]["population"]
assert sha(ledger["path"]) == ledger["sha256"]
population = read(ledger["path"]).set_index("area_id")["estimated_population"].sort_index()
ids = population.index.tolist()
assert len(ids) == len(set(ids)) == 6188
assert all(math.isfinite(p) and p >= 0 for p in population)
lookup = read("../../../1.Source Data/assembled_IPCCH/country_area_id_lookup.csv").set_index("area_id")["country"].reindex(ids)
regions = read("data/reference/area_id_country_region_mapping.csv").set_index("area_id")["region"].reindex(ids)
assert lookup.notna().all() and regions.notna().all() and sorted(regions.unique().tolist()) == list(range(9))
reference = read("reports/launch/nowcasting_2026_04/population_projection/countries_2025_population_merged.csv").set_index("country")["population_2025_total"].astype(float)
countries = sorted(lookup.unique().tolist())
raw_totals = {c: math.fsum(float(population[a]) for a in ids if lookup[a] == c) for c in countries}
factors = {c: .95 * float(reference[c]) / raw_totals[c] if raw_totals[c] > 1.10 * float(reference[c]) else 1.0 for c in countries}
assert sum(v < 1 for v in factors.values()) == 19
effective = {a: float(population[a]) * factors[lookup[a]] for a in ids}
audit = read(ROOT / "population/country_population_cap_audit.csv").set_index("country").reindex(countries)
match("cap_factor", audit.cap_factor, [factors[c] for c in countries])
match("raw_population", audit.raw_population, [raw_totals[c] for c in countries])
match("effective_population", audit.effective_population, [raw_totals[c] * factors[c] for c in countries])
assert np.array_equal(audit.cap_applied, [factors[c] < 1 for c in countries])

tables = {level: read(ROOT / "population" / f"{name}.csv") for level, name in FILES.items()}
expected = {}
for arm in (BASE, WEATHER):
    for h, target in ((0, "2026-04"), (6, "2026-10"), (12, "2027-04")):
        source = BASE if h == 0 else arm
        pred = read(ROOT / "runs" / source / f"{h}m" / "predictions_raw.csv").set_index("area_id")
        assert pred.index.tolist() == ids and (pred.target_month == target).all()
        want = {}
        for a in ids:
            q = [float(pred.at[a, f"phase{k}_pred"]) for k in (2, 3, 4, 5)]
            assert all(map(math.isfinite, q))
            component = [1-q[0], q[0]-q[1], q[1]-q[2], q[2]-q[3], q[3]]
            clipped = [min(1.0, max(0.0, x)) for x in component]
            den = math.fsum(clipped)
            assert den > 0 and math.isfinite(den)
            shares = [x/den for x in clipped]
            shares += [math.fsum(shares[2:5]), math.fsum(shares[3:5])]
            row = {"population_raw": float(population[a]), "population_effective": effective[a]}
            row.update({f"share_{n}": s for n, s in zip(NAMES, shares)})
            for kind in ("raw", "effective"):
                row.update({f"count_{kind}_{n}": s * row[f"population_{kind}"] for n, s in zip(NAMES, shares)})
            want[a] = row
        area = tables["area"]
        area = area[(area.display_arm == arm) & (area.horizon == h)].set_index("area_id").sort_index()
        assert area.index.tolist() == ids and (area.target_month == target).all()
        assert (area.origin_month == "2026-04").all() and (area.population_reference_month == "2026-04").all()
        assert area.country.tolist() == lookup.tolist() and area.region.tolist() == regions.tolist()
        assert np.array_equal(area.shared_h0_fit, np.full(len(ids), h == 0))
        cls = np.ones(len(ids), dtype=int)
        for k in (2, 3, 4, 5):
            cls[pred[f"phase{k}_pred"].to_numpy() >= .2] = k
            match(f"raw_phase{k}_pred", area[f"raw_phase{k}_pred"], pred[f"phase{k}_pred"])
        assert np.array_equal(area.overall_phase_pred_raw, cls) and np.array_equal(area.crisis_raw_phase3plus, cls >= 3)
        for col in next(iter(want.values())):
            match(f"{arm}/H{h}/area/{col}", area[col], [want[a][col] for a in ids])
        expected[(arm, h, "area")] = want
        for level in ("country", "region", "global"):
            labels = countries if level == "country" else list(range(9)) if level == "region" else ["global (covered launch areas)"]
            groups = {label: [a for a in ids if (lookup[a] if level == "country" else regions[a] if level == "region" else labels[0]) == label] for label in labels}
            part = tables[level]
            part = part[(part.display_arm == arm) & (part.horizon == h)].set_index(KEY[level]).sort_index()
            assert part.index.tolist() == labels and (part.target_month == target).all()
            totals = {}
            for label, members in groups.items():
                row = {c: math.fsum(want[a][c] for a in members) for c in next(iter(want.values())) if not c.startswith("share_")}
                for kind in ("raw", "effective"):
                    row.update({f"share_{kind}_{n}": row[f"count_{kind}_{n}"]/row[f"population_{kind}"] if row[f"population_{kind}"] > 0 else math.nan for n in NAMES})
                totals[label] = row
            for col in next(iter(totals.values())):
                match(f"{arm}/H{h}/{level}/{col}", part[col], [totals[l][col] for l in labels])
            assert part.n_areas.tolist() == [len(groups[l]) for l in labels]
            assert part.n_zero_population_areas.tolist() == [sum(population[a] == 0 for a in groups[l]) for l in labels]
            assert part.n_capped_areas.tolist() == [sum(factors[lookup[a]] < 1 for a in groups[l]) for l in labels]
            expected[(arm, h, level)] = totals

for level, key in KEY.items():
    diff = read(ROOT / "population" / f"{level}_population_paired_differences.csv")
    for h in (0, 6, 12):
        b, w = expected[(BASE, h, level)], expected[(WEATHER, h, level)]
        labels = list(b)
        part = diff[diff.horizon == h].set_index(key).reindex(labels)
        assert len(part) == len(b) and not part.index.duplicated().any()
        for col in next(iter(b.values())):
            if col.startswith("population_"):
                match(f"H{h}/{level}/{col}", part[col], [b[l][col] for l in labels])
                continue
            delta = [w[l][col]-b[l][col] for l in labels]
            match(f"H{h}/{level}/delta_{col}", part[f"delta_{col}"], delta)
            if h == 0:
                assert np.all((part[f"delta_{col}"].to_numpy() == 0) | part[f"delta_{col}"].isna().to_numpy())

for level in ("country", "region", "global"):
    filename = f"{FILES[level]}.csv"
    assert sha(ROOT / "population" / filename) == sha(REPORT / "population" / filename)
checks["all_four_levels_all_phases_raw_and_effective_counts_shares_differences"] = True
checks["fixed_population_common_cap_and_full_coverage"] = True
checks["report_population_copies_byte_equal"] = True
result = {"passed": True, "method": "math.fsum and scalar clipped-component construction; no production reporting imports",
          "checked_utc": pd.Timestamp.now(tz="UTC").isoformat(), "manifest_sha256": sha(MANIFEST), "population_ledger_sha256": ledger["sha256"],
          "checked_cells": checked, "max_abs_differences": maxima, "checks": checks, "capped_countries": 19,
          "capped_areas": sum(factors[lookup[a]] < 1 for a in ids), "population_raw_total": math.fsum(population),
          "population_effective_total": math.fsum(effective.values()), "zero_population_areas": sum(population == 0)}
(RESEARCH / "supervisor-population-verification.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=1))
