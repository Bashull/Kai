#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations
import argparse, json, pathlib, sys

ap=argparse.ArgumentParser()
ap.add_argument("result")
ap.add_argument("--max-p95-age-ms",type=float,default=250.0)
ap.add_argument("--max-max-age-ms",type=float,default=1000.0)
a=ap.parse_args()
p=pathlib.Path(a.result); d=json.loads(p.read_text())
checks={
 "transport_failures_zero": d.get("transport_failures")==0,
 "unhealthy_samples_zero": d.get("unhealthy_samples")==0,
 "restart_delta_zero": (d.get("restart_count") or {}).get("delta")==0,
 "frame_age_p95": ((d.get("frame_age_ms") or {}).get("p95") is not None and (d["frame_age_ms"]["p95"]<=a.max_p95_age_ms)),
 "frame_age_max": ((d.get("frame_age_ms") or {}).get("max") is not None and (d["frame_age_ms"]["max"]<=a.max_max_age_ms)),
 "samples_present": int(d.get("samples") or 0)>=250,
}
out={"profile":"balanced","pass":all(checks.values()),"thresholds":{"max_p95_age_ms":a.max_p95_age_ms,"max_max_age_ms":a.max_max_age_ms,"min_samples":250},"checks":checks,"observed":d}
print(json.dumps(out,indent=2))
sys.exit(0 if out["pass"] else 2)
