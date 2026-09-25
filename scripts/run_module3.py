"""Module 3 — S3 delay injection: level-crossing incident (S1) vs OCS foreign-object incident (S2).

Usage: python scripts/run_module3.py -> outputs/figures/m3_*.png and outputs/results_module3.md
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

from golsim import load_trains
from golsim.config import CONFIG, load_signalling
from golsim.headway import station_headway_fixed, station_headway_moving
from golsim.passengers import PassengerModel, weighted_passenger_delay_min
from golsim.propagation import Incident, build_route, build_timetable, simulate, summarise

FIG = ROOT / "outputs" / "figures"
FIG.mkdir(parents=True, exist_ok=True)
ops = yaml.safe_load((CONFIG / "operations.yaml").read_text())
trains = load_trains(CONFIG / "rolling_stock.yaml")
FIXED, MOVING = load_signalling()
c, inc_cfg, sim = ops["corridor"], ops["incident"], ops["simulation"]
pm = PassengerModel.from_config(ops["passengers"])
window = sim["window_hours"] * 3600
threshold = sim["punctuality_threshold_min"] * 60

out = ["# Module 3 results — delay propagation (equal-spacing corridor approximation, ASM-15)\n",
       "Primary KPI: weighted passenger delay (OI-12). Train delay shown for reference.\n",
       "| Run | Incident | Weighted passenger delay (pax-min) | Trips | Late trips (>5 min) | Train delay (train-min) | "
       "Max delay (min) | Max delay leaving Union eastbound (min) | Last late arrival (min after start) |",
       "|---|---|---|---|---|---|---|---|---|"]
panels = []

for name, sc in ops["scenarios"].items():
    tr = trains[sc["train"]]
    route = build_route(tr, c["lakeshore_west_km"], c["lakeshore_west_sections"],
                        c["lakeshore_east_km"], c["lakeshore_east_sections"], c["line_speed_kmh"])
    v_app = 60 / 3.6
    h_min = (station_headway_fixed(tr, FIXED, v_app, c["intermediate_dwell_s"]) if sc["signalling"] == "fixed"
             else station_headway_moving(tr, MOVING, v_app, c["intermediate_dwell_s"]))
    h_min -= c["intermediate_dwell_s"]   # separation between consecutive departures excluding own dwell
    for hw in sc["headway_min"]:
        start = inc_cfg["start_after_first_departure_min"] * 60
        inc = Incident(inc_cfg["section_index_from_hamilton"], start,
                       start + inc_cfg["duration_min"] * 60, inc_cfg["blocks_both_directions"])
        for label, incident in (("baseline", None), ("incident", inc)):
            trips = build_timetable(route, hw * 60, window, c["intermediate_dwell_s"],
                                    sc["union_dwell_scheduled_s"], sc["terminal_turnback_min_s"])
            simulate(route, trips, incident, c["intermediate_dwell_s"], sc["union_dwell_min_s"],
                     sc["terminal_turnback_min_s"], h_min)
            m = summarise(route, trips, threshold)
            run = f"{name} @ {hw} min, {label}"
            wpd = weighted_passenger_delay_min(route, trips, pm)
            out.append(f"| {run} | {sc['incident']['type'] if incident else '—'} | {wpd:,.0f} | {m['trips']} | "
                       f"{m['late_trips']} | {m['total_delay_min']:.0f} | {m['max_delay_min']:.1f} | "
                       f"{m['max_delay_leaving_union_eastbound_min']:.1f} | {m['last_late_arrival_min']:.0f} |")
            if incident and hw == 15:
                panels.append((f"{name}: {sc['incident']['type']} (15-min service)", route, trips, inc))

# Space-time diagrams (S1 and S2 at 15-min service with incident)
fig, axes = plt.subplots(1, len(panels), figsize=(14, 6), sharey=True)
for ax, (title, route, trips, inc) in zip(axes, panels):
    n = len(route.km)
    for t in trips:
        order = list(range(n)) if t.direction == "E" else list(range(n - 1, -1, -1))
        xs, ys, xs0, ys0 = [], [], [], []
        for k, st in enumerate(order):
            xs += [t.arr[k] / 60, t.dep[k] / 60]; ys += [route.km[st]] * 2
            if t.stopped_in_section and t.stopped_in_section[0] == k:
                _, frac, s0, s1 = t.stopped_in_section
                nxt = order[k + 1]
                pos = route.km[st] + frac * (route.km[nxt] - route.km[st])
                xs += [s0 / 60, s1 / 60]; ys += [pos, pos]
            xs0 += [t.sched_arr[k] / 60, t.sched_dep[k] / 60]; ys0 += [route.km[st]] * 2
        color = "C0" if t.direction == "E" else "C1"
        ax.plot(xs0, ys0, color=color, lw=0.6, ls=":", alpha=0.6)
        ax.plot(xs, ys, color=color, lw=1.1)
    a, b = route.km[inc.section], route.km[inc.section + 1]
    ax.add_patch(Rectangle((inc.start_s / 60, a), (inc.end_s - inc.start_s) / 60, b - a,
                           color="red", alpha=0.3, label="Blocked section"))
    ax.axhline(route.km[route.union_idx], color="grey", lw=0.8, ls="--")
    ax.text(2, route.km[route.union_idx] + 1, "Union", fontsize=8)
    ax.set(title=title, xlabel="Time after first departure (min)", xlim=(0, 360))
    ax.plot([], [], "C0", label="Eastbound (actual)"); ax.plot([], [], "C1", label="Westbound (actual)")
    ax.plot([], [], "k:", label="Scheduled")
    ax.legend(fontsize=7, loc="upper right")
axes[0].set_ylabel("Distance from Hamilton GO Centre (km)")
fig.tight_layout(); fig.savefig(FIG / "m3_space_time.png", dpi=150); plt.close(fig)

(ROOT / "outputs" / "results_module3.md").write_text("\n".join(out) + "\n")
print("\n".join(out))
