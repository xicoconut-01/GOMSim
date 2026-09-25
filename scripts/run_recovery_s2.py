"""S2 recovery-time study: how much schedule slack buys back the resilience S1 gets from its long Union dwell.

Options tested against the same 30-min OCS incident (ASM-17, ASM-18):
  U  Union recovery time      scheduled Union dwell = 60 s + r, minimum stays 60 s
  R  running-time allowance   every section scheduled at nominal x (1 + p%)
  T  terminal layover slack   scheduled turnback = minimum 300 s + slack
Costs: added scheduled journey time Hamilton GO Centre -> Oshawa GO, fleet size, Union platform demand.
Usage: python scripts/run_recovery_s2.py
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from golsim import load_trains
from golsim.config import CONFIG, load_signalling
from golsim.headway import platforms_needed, station_headway_moving
from golsim.passengers import PassengerModel, weighted_passenger_delay_min
from golsim.propagation import Incident, build_route, build_timetable, fleet_size, simulate, summarise

ops = yaml.safe_load((CONFIG / "operations.yaml").read_text())
c, inc_cfg, sim, sc = ops["corridor"], ops["incident"], ops["simulation"], ops["scenarios"]["S2"]
pm = PassengerModel.from_config(ops["passengers"])
tr = load_trains(CONFIG / "rolling_stock.yaml")[sc["train"]]
_, MOVING = load_signalling()
route = build_route(tr, c["lakeshore_west_km"], c["lakeshore_west_sections"],
                    c["lakeshore_east_km"], c["lakeshore_east_sections"], c["line_speed_kmh"])
v_app, dwell, hw = 60 / 3.6, c["intermediate_dwell_s"], 15 * 60
h_min = station_headway_moving(tr, MOVING, v_app, dwell) - dwell
start = inc_cfg["start_after_first_departure_min"] * 60
inc = Incident(inc_cfg["section_index_from_hamilton"], start, start + inc_cfg["duration_min"] * 60,
               inc_cfg["blocks_both_directions"])
window, threshold, turnback = sim["window_hours"] * 3600, sim["punctuality_threshold_min"] * 60, sc["terminal_turnback_min_s"]

options = [("S2 no recovery", 0, 0, 0)]
options += [(f"U +{r} min Union", r * 60, 0, 0) for r in (1, 2, 3, 5)]
options += [(f"R +{p}% running", 0, p, 0) for p in (3, 5, 7)]
# The 15-min grid already leaves a natural terminal layover above the 5-min minimum; slack below that
# changes nothing, so the terminal option is tested at values that move trips to the next departure slot.
options += [(f"T +{m} min terminal", 0, 0, m * 60) for m in (13, 28)]
options += [("U+5 min & T+13 min", 300, 0, 780)]

rows, base_journey = [], None
_t0 = build_timetable(route, hw, window, dwell, 60, turnback)
natural = min(t.sched_dep[0] - t.inbound.sched_arr[-1] for t in _t0 if t.inbound) - turnback
for name, union_extra, allowance, slack in options:
    trips = build_timetable(route, hw, window, dwell, 60 + union_extra, turnback, allowance, slack)
    journey = trips[0].sched_arr[-1] - trips[0].sched_dep[0]
    base_journey = base_journey or journey
    fleet = fleet_size(trips)
    simulate(route, trips, inc, dwell, 60, turnback, h_min)
    m = summarise(route, trips, threshold)
    m["wpd"] = weighted_passenger_delay_min(route, trips, pm)
    plat = platforms_needed(station_headway_moving(tr, MOVING, v_app, 60 + union_extra), hw)
    rows.append((name, (journey - base_journey) / 60, fleet, plat, m))

out = ["# S2 recovery-time study (30-min OCS incident, 15-min service)\n",
       "Options ranked by weighted passenger delay (OI-12).\n",
       "| Option | Weighted passenger delay (pax-min) | Added journey (min) | Fleet (sets) | Union platforms/dir | "
       "Late trips | Train delay (train-min) | Max delay (min) | Max delay leaving Union E (min) | Last late arrival (min) |",
       "|---|---|---|---|---|---|---|---|---|---|"]
for name, added, fleet, plat, m in sorted(rows, key=lambda r: r[4]["wpd"]):
    out.append(f"| {name} | {m['wpd']:,.0f} | {added:.1f} | {fleet} | {plat} | {m['late_trips']} | {m['total_delay_min']:.0f} | "
               f"{m['max_delay_min']:.1f} | {m['max_delay_leaving_union_eastbound_min']:.1f} | "
               f"{m['last_late_arrival_min']:.0f} |")
out.append(f"\nNatural terminal slack from the 15-min grid (no added slack): {natural / 60:.1f} min above the "
           f"{turnback / 60:.0f}-min minimum turnback.")
(ROOT / "outputs" / "results_recovery_s2.md").write_text("\n".join(out) + "\n")
print("\n".join(out))

fig, ax = plt.subplots(figsize=(8, 4.5))
markers = {"S2": "ko", "U ": "C0o", "R ": "C1s", "T ": "C2^", "U+": "C3D", "R+": "C4D"}
for name, added, fleet, plat, m in rows:
    style = next(v for k, v in markers.items() if name.startswith(k))
    ax.plot(added, m["wpd"] / 1000, style)
    ax.annotate(f"{name} ({fleet} sets)", (added, m["wpd"] / 1000), fontsize=7,
                xytext=(4, -11) if name.startswith(("R ", "T +28")) else (4, 3), textcoords="offset points")
ax.set(xlabel="Added scheduled journey time Hamilton GO Centre - Oshawa GO (min)",
       ylabel="Weighted passenger delay, OI-12 (thousand pax-min)",
       title="S2 recovery options: resilience vs journey-time cost")
fig.tight_layout(); fig.savefig(ROOT / "outputs" / "figures" / "m3_s2_recovery.png", dpi=150); plt.close(fig)
