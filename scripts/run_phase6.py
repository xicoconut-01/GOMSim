"""Generate phase-6 results: running times, ATP supervision curves, headway comparison.

Usage: python scripts/run_phase6.py   -> figures in outputs/figures, summary in outputs/results.md
"""
import dataclasses
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from golsim import load_corridor, load_trains, run_time, supervision_curves
from golsim.braking import ebi_distance, permitted_distance
from golsim.config import CONFIG, load_signalling
from golsim.headway import (line_headway_fixed, line_headway_moving, platforms_needed,
                            station_headway_fixed, station_headway_moving)

FIG = ROOT / "outputs" / "figures"
FIG.mkdir(parents=True, exist_ok=True)
trains = load_trains(CONFIG / "rolling_stock.yaml")
S1, S2 = trains["S1_diesel_pushpull"], trains["S2_bilevel_emu"]
corridor = load_corridor(CONFIG / "corridor.yaml")
FIXED, MOVING = load_signalling()
LABEL = {"S1_diesel_pushpull": "S1 diesel push-pull", "S2_bilevel_emu": "S2 bi-level EMU"}
out = ["# Phase 6 results (synthetic reference section — not the real corridor)\n"]

# ---- Module 1a: running time on the reference section --------------------------------------
fig, ax = plt.subplots(figsize=(10, 4))
lim_s, lim_v = [], []
for a, b, lim in corridor.speed_limits:
    lim_s += [a / 1000, b / 1000]; lim_v += [lim, lim]
ax.plot(lim_s, lim_v, "k--", lw=1, label="Line speed limit")
out.append("## Running time (Module 1a)\n\n| Train | Section times (s) | Running (s) | With dwell (s) |\n|---|---|---|---|")
results = {}
for key, tr in trains.items():
    r = run_time(tr, corridor)
    results[key] = r
    ax.plot(r.s / 1000, r.v * 3.6, label=LABEL[key])
    out.append(f"| {LABEL[key]} | {', '.join(f'{x:.0f}' for x in r.section_times_s)} | "
               f"{r.total_running_s:.0f} | {r.total_with_dwell_s:.0f} |")
for st in corridor.stations:
    ax.axvline(st["position_m"] / 1000, color="grey", lw=0.5)
    ax.text(st["position_m"] / 1000, 5, st["name"], ha="center")
ax.set(xlabel="Position (km)", ylabel="Speed (km/h)", title="Speed profile, reference section")
ax.legend(loc="lower center", ncol=3); fig.tight_layout(); fig.savefig(FIG / "m1_speed_profile.png", dpi=150); plt.close(fig)

# Attribution: does the 210 km/h design speed matter for a Local? (ASM-10)
s2_150 = dataclasses.replace(S2, vmax_mps=150 / 3.6)
t210 = results["S2_bilevel_emu"].total_running_s
t150 = run_time(s2_150, corridor).total_running_s
# Which part of the EMU gain comes from acceleration vs braking?
s2_s1brake = dataclasses.replace(S2, service_decel=S1.service_decel)
t_s2_s1brake = run_time(s2_s1brake, corridor).total_running_s
t1 = results["S1_diesel_pushpull"].total_running_s
out.append(f"\n**ASM-10 check:** S2 running time with 210 km/h design speed = {t210:.0f} s, "
           f"capped at 150 km/h = {t150:.0f} s (difference {t210 - t150:+.0f} s).\n")
out.append(f"**Gain decomposition (S1 -> S2 = {t1 - t210:.0f} s):** traction/acceleration "
           f"{t1 - t_s2_s1brake:.0f} s, service braking {t_s2_s1brake - t210:.0f} s.\n")

# ---- Module 1b: ATP supervision curves -----------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True, sharex=True)
out.append("## ATP supervision (Module 1b)\n\n| Train | From (km/h) | EBD (m) | EBI (m) | SBI (m) | Permitted (m) |\n|---|---|---|---|---|---|")
for ax, (key, tr) in zip(axes, trains.items()):
    c = supervision_curves(tr, v_max_kmh=150)
    for d, name, style in [(c.d_ebd, "EBD", "r-"), (c.d_ebi, "EBI", "r--"), (c.d_sbi, "SBI", "C1-"),
                           (c.d_warning, "Warning", "y-"), (c.d_permitted, "Permitted", "g-")]:
        ax.plot(d, c.v_mps * 3.6, style, label=name)
    ax.set(title=LABEL[key], xlabel="Distance to End of Authority (m)")
    ax.legend(fontsize=8)
    for kmh in (80, 120, 150):
        i = int(np.argmin(np.abs(c.v_mps * 3.6 - kmh)))
        out.append(f"| {LABEL[key]} | {kmh} | {c.d_ebd[i]:.0f} | {c.d_ebi[i]:.0f} | "
                   f"{c.d_sbi[i]:.0f} | {c.d_permitted[i]:.0f} |")
axes[0].set_ylabel("Speed (km/h)"); axes[0].invert_xaxis()
fig.tight_layout(); fig.savefig(FIG / "m1_atp_curves.png", dpi=150); plt.close(fig)

# ---- Module 2a: line headway vs speed --------------------------------------------------------
speeds = np.arange(30, 146, 5)
cases = [("S1 fixed block", lambda v: line_headway_fixed(S1, FIXED, v)),
         ("S2 fixed block", lambda v: line_headway_fixed(S2, FIXED, v)),
         ("S2 moving block (CBTC)", lambda v: line_headway_moving(S2, MOVING, v))]
fig, ax = plt.subplots(figsize=(8, 4))
out.append("\n## Line headway (Module 2a)\n\n| Case | Minimum (s) | at speed (km/h) | at 145 km/h (s) |\n|---|---|---|---|")
for name, f in cases:
    h = np.array([f(v / 3.6) for v in speeds])
    ax.plot(speeds, h, label=name)
    i = int(np.argmin(h))
    out.append(f"| {name} | {h[i]:.0f} | {speeds[i]} | {h[-1]:.0f} |")
ax.set(xlabel="Line speed (km/h)", ylabel="Minimum headway (s)", title="Plain-line headway")
ax.legend(); fig.tight_layout(); fig.savefig(FIG / "m2_line_headway.png", dpi=150); plt.close(fig)

# Sensitivity to the position reporting interval (OI-02: 500 ms under CBTC; the ETCS divergence sheet
# quotes a cyclic report of typically 5 s under ETCS L2)
out.append("\n**Reporting-interval sensitivity (S2 moving block, OI-02):**\n\n"
           "| Report interval (s) | Line headway at 110 km/h (s) | Station headway, 60 s dwell (s) |\n|---|---|---|")
for ti in (0.5, 1.0, 2.0, 5.0):
    mb = dataclasses.replace(MOVING, report_interval_s=ti)
    out.append(f"| {ti} | {line_headway_moving(S2, mb, 110 / 3.6):.1f} | "
               f"{station_headway_moving(S2, mb, 60 / 3.6, 60):.1f} |")

# ---- Module 2b: station headway at Union and platform demand ---------------------------------
v_app = 60 / 3.6       # approach speed into Union (assumption)
service = 15 * 60      # S2 target frequency, 15-min two-way (OPEN-02, partly closed)
rows = [("S1: fixed, 30 min Union dwell", station_headway_fixed(S1, FIXED, v_app, 1800)),
        ("S1a: fixed, 60 s dwell", station_headway_fixed(S1, FIXED, v_app, 60)),
        ("S1b: EMU, fixed, 60 s dwell", station_headway_fixed(S2, FIXED, v_app, 60)),
        ("S2: EMU, CBTC, 60 s dwell", station_headway_moving(S2, MOVING, v_app, 60))]
out.append("\n## Union station headway and platform demand at 15-min service (Module 2b)\n\n"
           "| Variant | Station headway (s) | Platform tracks per direction |\n|---|---|---|")
for name, h in rows:
    out.append(f"| {name} | {h:.0f} | {platforms_needed(h, service)} |")
fig, ax = plt.subplots(figsize=(8, 3.5))
ax.barh([r[0] for r in rows][::-1], [r[1] / 60 for r in rows][::-1], color=["C3", "C1", "C0", "C2"][::-1])
ax.axvline(service / 60, color="k", ls="--", lw=1, label="15-min service headway")
ax.set(xlabel="Station headway at Union (min)", title="Stepwise attribution at Union")
ax.legend(); fig.tight_layout(); fig.savefig(FIG / "m2_union_station_headway.png", dpi=150); plt.close(fig)

(ROOT / "outputs" / "results.md").write_text("\n".join(out) + "\n")
print("\n".join(out))
