"""Module 3 on the real corridor (v0.3): S3 disruption and S2 recovery options.

Replaces the equal-spacing approximation of v0.2 (ASM-15) with the OSRD-validated corridor:
real stop positions and section times, S1 driven on lineside signalling (CR-012, CR-013), S2 on CBTC with
ATO/ATP, CR-014 stop penalty for a train caught inside the blocked section, and minimum headways computed on
the real layout (S1 fixed block on the generated BAL signals, S2 moving block). Westbound = eastbound (ASM-23).
Incident: Oakville–Clarkson, 30 min, 90 min after the first departure, both directions (ASM-16..18).

Usage: python scripts/run_module3_real.py -> outputs/v03/*.md, outputs/v03/m3_real_space_time.png
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from golsim import corridor_real as cr
from golsim import load_trains
from golsim.config import CONFIG, load_signalling
from golsim.passengers import PassengerModel, weighted_passenger_delay_min
from golsim.propagation import Incident, build_timetable, fleet_size, simulate, summarise

DATA = ROOT / "data" / "osrd"
OUT = ROOT / "outputs" / "v03"
OUT.mkdir(parents=True, exist_ok=True)
ops = yaml.safe_load((CONFIG / "operations.yaml").read_text())
T = load_trains(CONFIG / "rolling_stock.yaml")
_, MB = load_signalling()
pm = PassengerModel.from_config(ops["passengers"])
sim, inc_cfg = ops["simulation"], ops["incident"]
WINDOW, THRESH = sim["window_hours"] * 3600, sim["punctuality_threshold_min"] * 60

rc = cr.load(DATA / "osrd_S2_export.csv", DATA / "lakeshore_topology.json")
oak = rc.names.index("Oakville")
start = inc_cfg["start_after_first_departure_min"] * 60
INC = Incident(oak, start, start + inc_cfg["duration_min"] * 60, inc_cfg["blocks_both_directions"])

# Scenario definitions: (label, train, driver, Union scheduled / minimum dwell, turnback, headways, signalling)
S1 = ops["scenarios"]["S1"]; S2 = ops["scenarios"]["S2"]
SCEN = [
    ("S1", "S1_diesel_pushpull", True, S1["union_dwell_scheduled_s"], S1["union_dwell_min_s"],
     S1["terminal_turnback_min_s"], [30, 15], "fixed"),
    ("S1-5", "S1_diesel_pushpull", True, 300, 300, S1["terminal_turnback_min_s"], [15], "fixed"),
    ("S2", "S2_bilevel_emu", False, S2["union_dwell_scheduled_s"], S2["union_dwell_min_s"],
     S2["terminal_turnback_min_s"], [15], "moving"),
]

lines = ["# Module 3 on the real corridor — golsim v0.3", "",
         f"Corridor: OSRD-validated path Hamilton GO Centre – Oshawa GO ({rc.length_m / 1000:.3f} km, "
         f"{len(rc.names)} stops). Incident Oakville–Clarkson {start // 60} to {(start + 1800) // 60} min after "
         "the first departure, both directions. Primary KPI: weighted passenger delay (OI-12).", "",
         "## Minimum headways on the real layout", "",
         "| Scenario | Signalling | Minimum headway (s) | Binding location (km) |", "|---|---|---|---|"]
heads, panels = {}, []
for lab, tk, drv, *_ , sig in SCEN:
    p = cr.profile(rc, T[tk], drv)
    h, x = cr.min_headway_fixed(rc, p) if sig == "fixed" else cr.min_headway_moving(p, T[tk], MB)
    heads[lab] = h
    lines.append(f"| {lab} | {'fixed block (generated BAL signals)' if sig == 'fixed' else 'moving block (CBTC)'} "
                 f"| {h:.0f} | {x / 1000:.1f} |")

lines += ["", "## Disruption (S3)", "",
          "| Run | Weighted pax delay (pax-min) | Late trips (>5 min) | Train delay (train-min) | "
          "Max delay (min) | Max delay leaving Union E (min) | Fleet (sets) | Terminal slack (min) |",
          "|---|---|---|---|---|---|---|---|"]
for lab, tk, drv, u_s, u_m, tb, hws, sig in SCEN:
    rt = cr.route(rc, T[tk], drv)
    for hw in hws:
        for name, inc in (("baseline", None), ("incident", INC)):
            trips = build_timetable(rt, hw * 60, WINDOW, 60, u_s, tb)
            fleet = fleet_size(trips)
            slack = min(t.sched_dep[0] - t.inbound.sched_arr[-1] for t in trips if t.inbound) - tb
            simulate(rt, trips, inc, 60, u_m, tb, heads[lab])
            m = summarise(rt, trips, THRESH)
            w = weighted_passenger_delay_min(rt, trips, pm)
            lines.append(f"| {lab} @ {hw} min, {name} | {w:,.0f} | {m['late_trips']} | {m['total_delay_min']:.0f} | "
                         f"{m['max_delay_min']:.1f} | {m['max_delay_leaving_union_eastbound_min']:.1f} | {fleet} | "
                         f"{slack / 60:.1f} |")
            if inc and hw == 15 and lab in ("S1", "S2"):
                panels.append((f"{lab} @ 15 min", rt, trips))

# Fair comparison: S1-5 with terminal slack comparable to S2 (next departure slot)
rt5 = cr.route(rc, T["S1_diesel_pushpull"], True)
for name, inc in (("baseline", None), ("incident", INC)):
    trips = build_timetable(rt5, 900, WINDOW, 60, 300, S1["terminal_turnback_min_s"], 0, 60)
    fleet = fleet_size(trips)
    slack = min(t.sched_dep[0] - t.inbound.sched_arr[-1] for t in trips if t.inbound) - S1["terminal_turnback_min_s"]
    simulate(rt5, trips, inc, 60, 300, S1["terminal_turnback_min_s"], heads["S1-5"])
    m = summarise(rt5, trips, THRESH)
    lines.append(f"| S1-5 @ 15 min, slack matched, {name} | {weighted_passenger_delay_min(rt5, trips, pm):,.0f} | "
                 f"{m['late_trips']} | {m['total_delay_min']:.0f} | {m['max_delay_min']:.1f} | "
                 f"{m['max_delay_leaving_union_eastbound_min']:.1f} | {fleet} | {slack / 60:.1f} |")

# Sensitivity of S1-5 to the fixed-block layout (generated signals are sparser than the real corridor)
import numpy as np
from golsim.blocking import TrainRun, build_blocking, requirements
p1 = cr.profile(rc, T["S1_diesel_pushpull"], True)
rt1 = cr.route(rc, T["S1_diesel_pushpull"], True)
u_m = rc.stops_m[rc.names.index(cr.UNION)]
def h_uniform(blk):
    pos = list(np.arange(0, rc.length_m, blk)); bl = build_blocking(pos, pos, rc.length_m)
    tr = TrainRun("h", 0).compute(p1)
    return max(e - s_ for (a, b), (s_, e) in zip(bl.zones, requirements(tr, p1, bl)) if not (a - 2000 < u_m < b + 2000))
lines += ["", "## Sensitivity: S1-5 @ 15 min against the fixed-block layout", "",
          "| Block layout | S1 minimum headway (s) | Weighted pax delay (pax-min) | Late trips | Train delay (train-min) |",
          "|---|---|---|---|---|"]
for name, h in (("Generated signals (OSRD)", heads["S1-5"]), ("Uniform 2.0 km", h_uniform(2000)),
                ("Uniform 1.5 km", h_uniform(1500)), ("Uniform 1.0 km", h_uniform(1000))):
    trips = build_timetable(rt1, 900, WINDOW, 60, 300, S1["terminal_turnback_min_s"])
    simulate(rt1, trips, INC, 60, 300, S1["terminal_turnback_min_s"], h)
    m = summarise(rt1, trips, THRESH)
    lines.append(f"| {name} | {h:.0f} | {weighted_passenger_delay_min(rt1, trips, pm):,.0f} | {m['late_trips']} | "
                 f"{m['total_delay_min']:.0f} |")

# S2 recovery options
rt = cr.route(rc, T["S2_bilevel_emu"], False)
lines += ["", "## S2 recovery options (15-min service, same incident)", "",
          "| Option | Weighted pax delay (pax-min) | Added journey (min) | Fleet (sets) | Late trips | Train delay (train-min) |",
          "|---|---|---|---|---|---|"]
tb = S2["terminal_turnback_min_s"]
t0 = build_timetable(rt, 900, WINDOW, 60, 60, tb)
natural = min(t.sched_dep[0] - t.inbound.sched_arr[-1] for t in t0 if t.inbound) - tb
jump = int(natural // 60) + 1
opts = [("No recovery", 0, 0, 0), ("Union +5 min", 300, 0, 0), ("Running +5 %", 0, 5, 0),
        (f"Terminal +{jump} min", 0, 0, jump * 60), (f"Union +5 min & terminal +{jump} min", 300, 0, jump * 60)]
base_j = None
rows = []
for name, ue, al, sl in opts:
    trips = build_timetable(rt, 900, WINDOW, 60, 60 + ue, tb, al, sl)
    j = trips[0].sched_arr[-1] - trips[0].sched_dep[0]
    base_j = base_j or j
    fleet = fleet_size(trips)
    simulate(rt, trips, INC, 60, 60, tb, heads["S2"])
    m = summarise(rt, trips, THRESH)
    rows.append((weighted_passenger_delay_min(rt, trips, pm), name, (j - base_j) / 60, fleet, m))
for w, name, add, fleet, m in sorted(rows):
    lines.append(f"| {name} | {w:,.0f} | {add:.1f} | {fleet} | {m['late_trips']} | {m['total_delay_min']:.0f} |")
lines.append(f"\nNatural terminal slack of the 15-min grid: {natural / 60:.1f} min above the minimum turnback.")

(OUT / "results_module3_real.md").write_text("\n".join(lines) + "\n")
print("\n".join(lines))

fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=True)
for ax, (title, rt, trips) in zip(axes, panels):
    n = len(rt.km)
    for t in trips:
        order = list(range(n)) if t.direction == "E" else list(range(n - 1, -1, -1))
        xs, ys = [], []
        for k, s in enumerate(order):
            xs += [t.arr[k] / 60, t.dep[k] / 60]; ys += [rt.km[s]] * 2
            if t.stopped_in_section and t.stopped_in_section[0] == k:
                _, frac, s0, s1 = t.stopped_in_section
                pos = rt.km[s] + frac * (rt.km[order[k + 1]] - rt.km[s])
                xs += [s0 / 60, s1 / 60]; ys += [pos, pos]
        ax.plot(xs, ys, color="C0" if t.direction == "E" else "C1", lw=0.9)
    ax.add_patch(Rectangle((INC.start_s / 60, rt.km[oak]), 30, rt.km[oak + 1] - rt.km[oak], color="red", alpha=0.3))
    ax.axhline(rt.km[rt.union_idx], color="grey", ls="--", lw=0.8)
    ax.set(title=f"{title}: incident Oakville–Clarkson", xlabel="Time after first departure (min)", xlim=(0, 360))
axes[0].set_ylabel("Distance from Hamilton GO Centre (km)")
fig.tight_layout(); fig.savefig(OUT / "m3_real_space_time.png", dpi=150); plt.close(fig)
