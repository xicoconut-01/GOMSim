"""VAL-05 — Oakville–Clarkson 30-min incident on the real corridor, eastbound, BAL blocking on generated signals.

Predicts, for S3a (S1-A, 60-min, Union 30 min with 10-min minimum work time) and S3b (S2, 15-min), which trains
the incident holds and by how much, including knock-on through the real block layout. The predicted holds are
then entered in OSRD; OSRD's conflict detection must show no multi-train conflict once they are applied, and
must show a conflict when a knock-on hold is reduced by more than 1 minute (VAL-05 criterion +/-1 min).

Usage: python scripts/val05_incident.py
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import val03_cross_validation as v
from golsim import load_trains, run_time
from golsim import railjson_path as rp
from golsim.blocking import Profile, TrainRun, apply_incident, build_blocking, propagate
from golsim.config import CONFIG
from golsim.dynamics import Corridor, buffer_stop_approach_limits

UP = Path(__file__).resolve().parents[1] / "data" / "osrd"
TOPO = rp.load_topology(str(UP / "lakeshore_topology.json"))


class Graph(rp.TrackGraph):
    def __init__(self, t):
        super().__init__(t)
        self.op_parts["UNION-7"] = ("23621505-0", 177.0, "Toronto Union Station")   # Union track 7


rp.TrackGraph = Graph


def setup(export: str):
    df = v.read_osrd_export(str(UP / export))
    st = v.extract_stops(df)
    anchors = []
    for _, s in st.iterrows():
        rows = df[(df.pos_m.round(0) == round(s.pos_m)) & df.op.notna()]
        tn = ["UNION-7"] if "Union" in s["name"] else [x for x in rows.trackName.dropna() if len(x) > 20]
        if tn:
            anchors.append((tn[0], s.pos_m))
    segs, checks, err = rp.rebuild_path(TOPO, anchors)
    sig = [p for p, _ in rp.project(segs, TOPO["signals"], directional=True)]
    det = [p for p, _ in rp.project(segs, TOPO["detectors"], directional=False)]
    return df, st, sig, det, err


def profile(df, st, train_key, union_sched, union_min, extra_stop=None):
    L = float(df.pos_m.iloc[-1])
    segl = v.speed_limit_segments(df)
    stations = [{"name": s["name"], "position_m": float(s.pos_m), "dwell_s": 0} for _, s in st.iterrows()]
    stations[-1]["position_m"] = L
    if extra_stop is not None:
        stations.append({"name": "incident stop", "position_m": float(extra_stop), "dwell_s": 0})
        stations.sort(key=lambda x: x["position_m"])
    tr = load_trains(CONFIG / "rolling_stock.yaml")[train_key]
    res = run_time(tr, Corridor(stations, segl + buffer_stop_approach_limits(L), [[0, L, 0]]), ds=1.0,
                   driver_margins_m=(100.0, 50.0))
    n = len(stations)
    names = [s["name"] for s in stations]
    dw = lambda nm: 0.0 if nm == "incident stop" else (union_sched if "Union" in nm else 60.0)
    dm = lambda nm: 0.0 if nm == "incident stop" else (union_min if "Union" in nm else 60.0)
    sched = [0.0] + [dw(nm) for nm in names[1:-1]] + [0.0]
    mind = [0.0] + [dm(nm) for nm in names[1:-1]] + [0.0]
    return Profile(res.t, [s["position_m"] for s in stations], mind, sched, tr.length_m, res.v), names


def fmt(t):
    t = int(round(t))
    return f"{t // 3600:02d}:{t % 3600 // 60:02d}:{t % 60:02d}"


def scenario(label, export, train_key, union_sched, union_min, first_dep, headway, n_trains, w0):
    df, st, sig, det, err = setup(export)
    p, names = profile(df, st, train_key, union_sched, union_min)
    bl = build_blocking(sig, det, p.stops[-1])
    oak = names.index("Oakville")
    w1 = w0 + 1800
    trains = [TrainRun(f"{label} #{k + 1}", first_dep + k * headway) for k in range(n_trains)]
    decel = load_trains(CONFIG / "rolling_stock.yaml")[train_key].service_decel
    mk = lambda pos: profile(df, st, train_key, union_sched, union_min, extra_stop=pos)[0]
    for tr in trains:
        apply_incident(tr, p, oak, w0, w1, make_profile=mk, service_decel=decel)
    propagate(trains, p, bl)
    lines = [f"## {label} — {train_key}, every {headway // 60} min, incident Oakville–Clarkson {fmt(w0)}–{fmt(w1)}",
             f"(path rebuilt on RailJSON, total leg error {err:.0f} m; {len(sig)} signals, {len(bl.zones)} zones)", ""]
    affected = []
    for tr in trains:
        delay_end = tr.arr[-1] - tr.sched_arr[-1]
        if delay_end > 1 or tr.section_holds:
            affected.append(tr)
    if not affected:
        lines.append("No train affected.")
    for tr in affected:
        tp = tr.prof or p
        tnames = names if tr.prof is None else [("incident stop" if abs(x - getattr(tr, "incident_stop", (None,))[0]) < 1 else
                                                 names[[round(y) for y in p.stops].index(round(x))]) for x in tp.stops]
        u = next(i for i, nm in enumerate(tnames) if "Union" in nm)
        lines.append(f"**{tr.name}** — scheduled departure Hamilton {fmt(tr.t0)}; delay at Union departure "
                     f"{(tr.dep[u] - tr.sched_dep[u]) / 60:.1f} min, at destination {(tr.arr[-1] - tr.sched_arr[-1]) / 60:.1f} min")
        for pos, d in tr.section_holds:
            lines.append(f"  - stopped inside the blocked section at {pos / 1000:.2f} km for {d / 60:.0f} min")
        if getattr(tr, "incident_stop", None):
            sp, k = tr.incident_stop
            lines.append(f"  - brakes to a stand inside the section at {sp / 1000:.3f} km "
                         f"({(sp - p.stops[names.index('Oakville')]):.0f} m after Oakville), arrives {fmt(tr.arr[k])}, "
                         f"restarts {fmt(tr.dep[k])}")
        lines.append("  - OSRD stopping times to enter (only stations that change):")
        for i, nm in enumerate(tnames[:-1]):
            dwell = tr.dep[i] - tr.arr[i]
            base = 0 if i == 0 else tp.sched_dwell[i]
            if abs(dwell - base) > 0.5:
                lines.append(f"    - {nm}: arrive {fmt(tr.arr[i])}, stop {int(dwell // 60):d} min {int(round(dwell % 60)):02d} s "
                             f"(normally {int(base // 60)} min), depart {fmt(tr.dep[i])}")
        lines.append("")
    return "\n".join(lines), trains, p, names


if __name__ == "__main__":
    out = ["# VAL-05 predictions (golsim, BAL blocking on OSRD generated signals, eastbound only)", ""]
    a, *_ = scenario("S3a", "osrd_S1_export.csv", "S1_diesel_pushpull", 1800, 600,
                     first_dep=0, headway=3600, n_trains=6, w0=5400)
    b, *_ = scenario("S3b", "osrd_S2_export.csv", "S2_bilevel_emu", 60, 60,
                     first_dep=60, headway=900, n_trains=16, w0=60 + 5400)
    text = "\n".join(out + [a, b])
    (ROOT / "outputs" / "val03" / "val05_predictions.md").write_text(text + "\n")
    print(text)
