import json, sys
from fractions import Fraction
import numpy as np, pandas as pd
sys.path.insert(0, "src")
from ipcch import climate2015_features as cf, compact_features as cpf
pm = json.load(open("../../../1.Source Data/assembled_IPCCH/model_ready/origin_safe_climate_idp_v1/origin_safe_climate_idp_v1_manifest.json"))
it = pd.read_csv(pm["inputs"]["interim"]["path"], usecols=["admin_code", "year", "month", "WFP_Price", "GPP_mean", "sum_fatalities_violence"], float_precision="round_trip").rename(columns={"admin_code": "area_id"})
cl = pd.read_csv(pm["inputs"]["climate_monthly"]["path"], usecols=["admin_code", "year", "month", "cdd_month_ensmean"], float_precision="round_trip").rename(columns={"admin_code": "area_id"})
def exact_sd(v):
    v = [Fraction(a) for a in v if a == a]
    m = sum(v) / len(v); return float(sum((a - m) ** 2 for a in v) / (len(v) - 1)) ** 0.5
def exact_z(prior, cur):
    p = [Fraction(a) for a in prior if a == a]; m = sum(p) / len(p)
    sd = float(sum((a - m) ** 2 for a in p) / (len(p) - 1)) ** 0.5
    return float(Fraction(cur) - m) / sd
print("Rolling SD12 on the full real series of one area (pandas running sums vs per-window shift-centred vs exact Fraction):")
for area, col, y, m in ((4588, "WFP_Price", 2024, 11), (4151, "sum_fatalities_violence", 2025, 6), (101055, "GPP_mean", 2024, 9)):
    g = cf.Grid.from_long(it[it.area_id == area], [col], require_complete=False)
    j = y * 12 + m - 1 - g.first_ord
    x = g.values[col]
    print(f"  {col} area {area} {y}-{m:02d}: pandas {cf.rolling(x, 12, 6, 'std')[0, j]!r}  compact {cpf.trailing(x, 12, 6, 'std')[0, j]!r}  exact {exact_sd(x[0, j-11:j+1])!r}")
print("Same-month z of near-constant real cdd histories (old uncentred helper vs compact shift-centred vs exact Fraction):")
for area, y, m in ((101270, 2023, 11), (101274, 2024, 9), (101214, 2023, 1)):
    g = cf.Grid.from_long(cl[cl.area_id == area], ["cdd_month_ensmean"])
    x = g.values["cdd_month_ensmean"]; j = y * 12 + m - 1 - g.first_ord
    mean, std, _ = cf.same_month_history(x, g.first_ord)
    old = (x[0, j] - mean[0, j]) / std[0, j]
    prior = x[0, j - 12::-12][::-1]
    print(f"  area {area} {y}-{m:02d}: prior {[repr(v) for v in prior]} current {x[0, j]!r}")
    print(f"      old {old!r}  compact {cpf.same_month_z(x, g.first_ord)[0, j]!r}  exact {exact_z(prior, x[0, j])!r}")
