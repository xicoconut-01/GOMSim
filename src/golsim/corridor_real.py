"""The real Hamilton GO Centre - Oshawa GO corridor from OSRD data (phase 9, v0.3).

Builds, from an OSRD export and the RailJSON topology:
  - the rebuilt track path with signals and detectors (railjson_path),
  - running profiles with the right driving rules: a driver on lineside signalling (S1: CR-012 margins and the
    CR-013 buffer-stop approach) or CBTC with ATO/ATP (S2: none of them),
  - a Module 3 Route (real stop positions and section times, CR-014 stop penalties),
  - minimum headways on the real layout: fixed block on the generated BAL signals, and moving block.
Westbound running times are taken equal to eastbound (ASM-23).
"""
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import railjson_path as rp
from .blocking import Blocking, Profile, TrainRun, build_blocking, requirements
from .braking import permitted_distance
from .dynamics import Corridor, buffer_stop_approach_limits, run_time
from .headway import MovingBlock
from .osrd_export import extract_stops, read_osrd_export, speed_limit_segments
from .propagation import Route, section_stop_penalty
from .rolling_stock import Train

UNION = "Toronto Union Station"


@dataclass
class RealCorridor:
    names: list[str]
    stops_m: list[float]
    length_m: float
    limits: list
    signals_m: list[float]
    detectors_m: list[float]
    leg_error_m: float

    @property
    def blocking(self) -> Blocking:
        return build_blocking(self.signals_m, self.detectors_m, self.length_m)


def load(export_csv: str | Path, topology_json: str | Path, union_track: str = "7") -> RealCorridor:
    df = read_osrd_export(str(export_csv))
    st = extract_stops(df)
    topo = rp.load_topology(str(topology_json))
    union_part = next((p["track"], p["position"]) for o in topo["operational_points"] if o.get("name") == UNION
                      for p in o["parts"] if p["local_track_name"] == union_track)

    class Graph(rp.TrackGraph):
        def __init__(self, t):
            super().__init__(t)
            self.op_parts["UNION"] = (*union_part, UNION)

    anchors = []
    for _, s in st.iterrows():
        rows = df[(df.pos_m.round(0) == round(s.pos_m)) & df.op.notna()]
        tn = ["UNION"] if UNION in s["name"] else [x for x in rows.trackName.dropna() if len(x) > 20]
        if tn:
            anchors.append((tn[0], s.pos_m))
    saved, rp.TrackGraph = rp.TrackGraph, Graph
    try:
        segs, checks, err = rp.rebuild_path(topo, anchors)
    finally:
        rp.TrackGraph = saved
    length = float(df.pos_m.iloc[-1])
    names = list(st["name"])
    stops = [float(x) for x in st.pos_m]
    stops[-1] = length
    return RealCorridor(names, stops, length, speed_limit_segments(df),
                        [p for p, _ in rp.project(segs, topo["signals"], directional=True)],
                        [p for p, _ in rp.project(segs, topo["detectors"], directional=False)], err)


def profile(rc: RealCorridor, train: Train, driver: bool, union_dwell_s: float = 60.0,
            union_min_s: float | None = None, dwell_s: float = 60.0, extra_stop: float | None = None) -> Profile:
    """Running profile. driver=True: lineside signalling with a driver (S1); False: CBTC with ATO/ATP (S2)."""
    stations = [{"name": n, "position_m": x, "dwell_s": 0} for n, x in zip(rc.names, rc.stops_m)]
    if extra_stop is not None:
        stations = sorted(stations + [{"name": "incident stop", "position_m": extra_stop, "dwell_s": 0}],
                          key=lambda s: s["position_m"])
    limits = rc.limits + (buffer_stop_approach_limits(rc.length_m) if driver else [])
    res = run_time(train, Corridor(stations, limits, [[0, rc.length_m, 0]]), ds=1.0,
                   driver_margins_m=(100.0, 50.0) if driver else (0.0, 0.0))
    um = union_dwell_s if union_min_s is None else union_min_s
    sched, mind = [], []
    for i, s in enumerate(stations):
        end = i in (0, len(stations) - 1) or s["name"] == "incident stop"
        sched.append(0.0 if end else (union_dwell_s if UNION in s["name"] else dwell_s))
        mind.append(0.0 if end else (um if UNION in s["name"] else dwell_s))
    return Profile(res.t, [s["position_m"] for s in stations], mind, sched, train.length_m, res.v)


def route(rc: RealCorridor, train: Train, driver: bool) -> Route:
    """Module 3 Route on the real corridor: real stops, section times and CR-014 stop penalties."""
    p = profile(rc, train, driver)
    run = [p.run(a, b) for a, b in zip(rc.stops_m[:-1], rc.stops_m[1:])]
    pen = []
    for a, b in zip(rc.stops_m[:-1], rc.stops_m[1:]):
        lim = [[max(x0, a) - a, min(x1, b) - a, v] for x0, x1, v in rc.limits if x1 > a and x0 < b]
        pen.append(section_stop_penalty(train, b - a, 0, limits=lim,
                                        driver_margins_m=(100.0, 50.0) if driver else (0.0, 0.0)))
    return Route(list(rc.names), [x / 1000 for x in rc.stops_m], run, rc.names.index(UNION), pen)


def min_headway_fixed(rc: RealCorridor, p: Profile, exclude_union: bool = True) -> tuple[float, float]:
    """Minimum headway of identical trains on the generated BAL signals: longest zone occupation.
    Returns (headway s, zone start m). Union zones can be excluded (platform capacity handled separately)."""
    bl = rc.blocking
    tr = TrainRun("h", 0.0).compute(p)
    u = rc.stops_m[rc.names.index(UNION)]
    best = (0.0, 0.0)
    for (a, b), (s, e) in zip(bl.zones, requirements(tr, p, bl)):
        if exclude_union and a - 2000 < u < b + 2000:
            continue
        best = max(best, (e - s, a))
    return best


def min_headway_moving(p: Profile, train: Train, mb: MovingBlock, exclude_union_m: float | None = None,
                       step_m: int = 10) -> tuple[float, float]:
    """Moving-block minimum headway: the follower at x needs the leader's tail beyond its stopping point."""
    tr = TrainRun("h", 0.0).compute(p)
    end = p.stops[-1]
    best = (0.0, 0.0)
    for x in range(0, int(end) - 1, step_m):
        if exclude_union_m is not None and abs(x - exclude_union_m) < 2000:
            continue
        v = float(p.v[x])
        need = x + permitted_distance(train, v) + mb.safety_margin_m + mb.position_uncertainty_m \
            + v * mb.reaction_time_s + train.length_m
        h = tr.head_time(p, min(need, end), leaving=True) - tr.head_time(p, x) + mb.system_processing_s
        best = max(best, (h, float(x)))
    return best
