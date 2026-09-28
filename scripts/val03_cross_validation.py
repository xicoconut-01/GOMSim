"""VAL-03 — cross-validate golsim against an OSRD simulation export (phase 9).

Input equivalence: the golsim corridor is rebuilt from the OSRD export itself — stop positions from the points
where OSRD holds the train at standstill, and the speed-limit profile from OSRD's speedLimit column. That column
holds the line limit at the head of the train; OSRD applies the train-length rule internally, so golsim applies
its own train-length rule with the real train length (checked on the S1 run: Hamilton GO Centre - Aldershot
differs by -4.2 % without the rule and -0.4 % with it). Gradients are zero in both tools (OSM carries no slope
data). Dwell is excluded: only running time between stops is compared.

Criteria (validation plan, VAL-03):
  CV-1 end-to-end running time within +/-3 %
  CV-2 each interstation running time within +/-5 % or +/-10 s, whichever is larger
  CV-3 each interstation maximum speed within +/-5 km/h

Usage: python scripts/val03_cross_validation.py <osrd_export.csv> <train_key> [out_prefix]
"""
import io
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from golsim import load_trains, run_time
from golsim.config import CONFIG
from golsim.dynamics import Corridor, buffer_stop_approach_limits


from golsim.osrd_export import extract_stops, read_osrd_export, speed_limit_segments  # noqa: E402


def main(csv_path: str, train_key: str, out_prefix: str):
    df = read_osrd_export(csv_path)
    stops = extract_stops(df)
    segs = speed_limit_segments(df)
    length = float(df["pos_m"].iloc[-1])
    stations = [{"name": s["name"] or f"stop@{s.pos_m/1000:.3f}km", "position_m": float(s.pos_m), "dwell_s": 0}
                for _, s in stops.iterrows()]
    stations[-1]["position_m"] = length
    # Terminal on a buffer-stop track: OSRD applies its safety approach speed (30 km/h over the last 200 m,
    # 10 km/h over the last 100 m). Detected from the export: a 10 km/h crawl in the last 300 m.
    tail = df[(df["pos_m"] > length - 300) & ((df["speed"] - 10.0).abs() < 0.05)]
    buffer_stop = bool(len(tail) >= 2 and tail["pos_m"].max() - tail["pos_m"].min() > 50)
    if buffer_stop:
        segs = segs + buffer_stop_approach_limits(length)
    corridor = Corridor(stations, segs, [[0, length, 0]])

    train = load_trains(CONFIG / "rolling_stock.yaml")[train_key]
    # OSRD applies its DriverBehaviour (brake 100 m before, accelerate 50 m after a limit) on BAL/BAPR track;
    # the GOMSim rolling stock runs on BAL in OSRD, so golsim applies the same margins for equivalence.
    res = run_time(train, corridor, ds=1.0, driver_margins_m=(100.0, 50.0))

    rows = []
    for k in range(len(stops) - 1):
        a, b = stops.iloc[k], stops.iloc[k + 1]
        t_osrd = b.arr - a.dep
        t_gol = res.section_times_s[k]
        seg = df[(df["pos_m"] >= a.pos_m - 1) & (df["pos_m"] <= b.pos_m + 1)]
        m = (res.s >= a.pos_m) & (res.s <= b.pos_m)
        v_osrd, v_gol = seg["speed"].max(), res.v[m].max() * 3.6
        diff = t_gol - t_osrd
        tol = max(0.05 * t_osrd, 10.0)
        rows.append({"from": a["name"], "to": b["name"], "km": (b.pos_m - a.pos_m) / 1000,
                     "osrd_s": t_osrd, "golsim_s": t_gol, "diff_s": diff, "diff_pct": 100 * diff / t_osrd,
                     "cv2_pass": abs(diff) <= tol, "vmax_osrd": v_osrd, "vmax_golsim": v_gol,
                     "cv3_pass": abs(v_gol - v_osrd) <= 5.0})
    r = pd.DataFrame(rows)
    tot_o, tot_g = r["osrd_s"].sum(), r["golsim_s"].sum()
    cv1 = abs(tot_g - tot_o) / tot_o * 100

    out = ROOT / "outputs" / "val03"
    out.mkdir(parents=True, exist_ok=True)
    r.to_csv(out / f"{out_prefix}_sections.csv", index=False)
    lines = [f"# VAL-03 cross-validation — {train_key}", "",
             f"OSRD export: {Path(csv_path).name}; path length {length/1000:.3f} km; {len(stops)} stops; "
             f"terminal on buffer stop: {'yes (safety approach speed applied)' if buffer_stop else 'no'}.", "",
             f"**CV-1** end-to-end running time: OSRD {tot_o:.0f} s, golsim {tot_g:.0f} s, "
             f"difference {100*(tot_g-tot_o)/tot_o:+.2f} % -> {'PASS' if cv1 <= 3 else 'FAIL'} (limit +/-3 %)",
             f"**CV-2** interstation times: {r['cv2_pass'].sum()} of {len(r)} within tolerance -> "
             f"{'PASS' if r['cv2_pass'].all() else 'FAIL'}",
             f"**CV-3** interstation max speed: {r['cv3_pass'].sum()} of {len(r)} within +/-5 km/h -> "
             f"{'PASS' if r['cv3_pass'].all() else 'FAIL'}", "",
             "| From | To | km | OSRD (s) | golsim (s) | Diff (s) | Diff (%) | CV-2 | Vmax OSRD | Vmax golsim | CV-3 |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for _, x in r.iterrows():
        lines.append(f"| {x['from']} | {x['to']} | {x.km:.2f} | {x.osrd_s:.0f} | {x.golsim_s:.0f} | {x.diff_s:+.0f} | "
                     f"{x.diff_pct:+.1f} | {'pass' if x.cv2_pass else 'FAIL'} | {x.vmax_osrd:.0f} | {x.vmax_golsim:.0f} | "
                     f"{'pass' if x.cv3_pass else 'FAIL'} |")
    (out / f"{out_prefix}_report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))

    fig, ax = plt.subplots(figsize=(14, 4.5))
    ax.plot(df["position"], df["speedLimit"], "k--", lw=0.8, label="Line speed limit (OSRD export)")
    ax.plot(df["position"], df["speed"], lw=1.2, label="OSRD")
    ax.plot(res.s / 1000, res.v * 3.6, lw=1.0, alpha=0.8, label="golsim")
    ax.set(xlabel="Distance from Hamilton GO Centre (km)", ylabel="Speed (km/h)",
           title=f"VAL-03 speed profiles — {train_key}")
    ax.legend(loc="lower right"); fig.tight_layout()
    fig.savefig(out / f"{out_prefix}_speed_profiles.png", dpi=150); plt.close(fig)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "s1")
