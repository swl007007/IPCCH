"""C0: hash every file under the 12 allowlisted source roots (read-only). Output CSV."""
import csv, hashlib, os, sys
from pathlib import Path
REPO = Path(sys.argv[1]); SRC = Path(sys.argv[2]); OUT = Path(sys.argv[3])
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()
rows = []
for r in csv.DictReader(open(SRC)):
    root = REPO / r["result_root"]
    for dp, dns, fns in os.walk(root):
        dns.sort()
        for fn in sorted(fns):
            p = Path(dp) / fn
            rows.append({"source_key": r["source_key"], "path": str(p.relative_to(REPO)), "bytes": p.stat().st_size, "sha256": sha(p)})
with open(OUT, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["source_key", "path", "bytes", "sha256"]); w.writeheader(); w.writerows(rows)
print(len(rows), "files")
