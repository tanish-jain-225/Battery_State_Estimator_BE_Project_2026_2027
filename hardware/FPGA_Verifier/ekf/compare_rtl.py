#!/usr/bin/env python3
"""Word-by-word comparison of rtl_ekf_trace.csv (XSim) vs golden_ekf_trace.csv.
usage: python3 compare_rtl.py golden_ekf_trace.csv rtl_ekf_trace.csv"""
import csv
import sys

g = list(csv.DictReader(open(sys.argv[1])))
r = list(csv.DictReader(open(sys.argv[2])))
cols = [c for c in g[0] if c not in ("step", "t")]
print(f"golden rows {len(g)}, RTL rows {len(r)}")
bad, first = {c: 0 for c in cols}, None
for a, b in zip(g, r):
    for c in cols:
        if a[c].strip().lower() != b[c].strip().lower():
            bad[c] += 1
            if first is None:
                first = (a["step"], c, a[c], b[c])
n = min(len(g), len(r))
for c in cols:
    print(f"  {c:5s} {n - bad[c]}/{n}")
if first:
    print("FIRST MISMATCH step %s field %s golden=%s rtl=%s" % first)
print("ALL STAGES BIT-EXACT" if not first and len(g) == len(r) else "MISMATCH")
