import csv, hashlib, os, sys, time
from pathlib import Path
root = Path.cwd()
src = root.parent.parent.parent / "1.Source Data/assembled_IPCCH/model_ready"
dirs = [src / "origin_safe_climate_idp_v1", src / "origin_safe_weather_oracle_v1",
        root / "results/experiments/origin_safe_climate_idp_v1", root / "results/experiments/origin_safe_weather_oracle_v1"]
out = Path(sys.argv[1]); out.parent.mkdir(parents=True, exist_ok=True)
t0 = time.time(); n = 0
with open(out, "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["path", "bytes", "sha256"])
    for d in dirs:
        for p in sorted(d.rglob("*")):
            if p.is_file():
                h = hashlib.sha256()
                with open(p, "rb") as f:
                    for chunk in iter(lambda: f.read(1 << 22), b""): h.update(chunk)
                w.writerow([str(p), p.stat().st_size, h.hexdigest()]); n += 1
print(f"{n} files hashed in {time.time()-t0:.0f}s -> {out}")
