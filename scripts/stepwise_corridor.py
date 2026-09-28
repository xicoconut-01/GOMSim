"""Stepwise attribution S1 -> S2 on the real corridor (geometry taken from a validated OSRD export).

Each step changes one thing, so every saving is attributable (CR-005):
  S1   diesel push-pull, driver on lineside signalling, Union 30 min
  S1a  as S1, Union 1 min                                  -> Union operation
  S1b  as S1a, bi-level EMU                                -> rolling stock
  S2   as S1b, CBTC with ATO/ATP                           -> driving and supervision (CR-012, CR-013)
Driver rules for lineside signalling: 100 m braking anticipation, 50 m acceleration postponement, and the
safety approach speed into the Oshawa buffer stop. Under CBTC with ATO/ATP none of them apply.
Usage: python scripts/stepwise_corridor.py <osrd_export.csv>
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import val03_cross_validation as v
from golsim import load_trains, run_time
from golsim.config import CONFIG
from golsim.dynamics import Corridor, buffer_stop_approach_limits

df = v.read_osrd_export(sys.argv[1])
stops = v.extract_stops(df)
segs = v.speed_limit_segments(df)
length = float(df["pos_m"].iloc[-1])
T = load_trains(CONFIG / "rolling_stock.yaml")


def journey(train, union_dwell_s, driver):
    st = []
    for i, (_, s) in enumerate(stops.iterrows()):
        dwell = 0 if i in (0, len(stops) - 1) else (union_dwell_s if "Union" in s["name"] else 60)
        st.append({"name": s["name"], "position_m": float(s.pos_m), "dwell_s": dwell})
    st[-1]["position_m"] = length
    limits = segs + (buffer_stop_approach_limits(length) if driver else [])
    r = run_time(train, Corridor(st, limits, [[0, length, 0]]), ds=1.0,
                 driver_margins_m=(100.0, 50.0) if driver else (0.0, 0.0))
    return r.total_running_s / 60, r.total_with_dwell_s / 60


steps = [("S1", "Diesel push-pull, driver, Union 30 min", T["S1_diesel_pushpull"], 1800, True, "—"),
         ("S1a", "Union dwell 30 min -> 1 min", T["S1_diesel_pushpull"], 60, True, "Union operation"),
         ("S1b", "Diesel push-pull -> bi-level EMU", T["S2_bilevel_emu"], 60, True, "Rolling stock"),
         ("S2", "Driver -> CBTC with ATO/ATP", T["S2_bilevel_emu"], 60, False, "Driving and supervision")]
out = [f"# Stepwise journey time, Hamilton GO Centre - Oshawa GO ({length/1000:.3f} km, OSRD-validated corridor)", "",
       "| Step | Change | Running (min) | Journey incl. dwell (min) | Saving vs previous (min) | Attributed to |",
       "|---|---|---|---|---|---|"]
prev = None
for code, change, tr, u, drv, attr in steps:
    run, tot = journey(tr, u, drv)
    out.append(f"| {code} | {change} | {run:.1f} | {tot:.1f} | {'' if prev is None else f'{prev - tot:.1f}'} | {attr} |")
    prev = tot
text = "\n".join(out) + "\n"
(ROOT / "outputs" / "val03" / "stepwise_corridor.md").write_text(text)
print(text)
