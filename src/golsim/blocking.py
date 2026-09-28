"""Delay propagation with fixed-block (BAL) blocking times on the real corridor (phase 9, VAL-05).

Each train runs the same validated running profile; delays enter only as holds:
  - at stops: departure = max(scheduled departure, arrival + minimum dwell, hold forced by a conflict or incident)
  - inside a section: a train already in the blocked section when the incident starts stops for its duration
Conflicts use OSRD's BAL spacing rule (see scripts/val04_headway_real_signals.py): a zone is required from the
time the head reaches the sighting point of the warning signal until the tail clears the zone. A follower whose
requirement would start before an earlier train's requirement ends is held at the last stop before that
sighting point, which is where a real train would wait at a station for the signal to clear.
"""
from dataclasses import dataclass, field

import numpy as np


@dataclass
class Profile:
    """Running profile of one train type on the path: head running time t(s) at 1 m resolution, no dwell."""
    t_run: np.ndarray
    stops: list[float]            # stop positions (m), origin first, destination last
    min_dwell: list[float]        # minimum dwell per stop (s)
    sched_dwell: list[float]      # scheduled dwell per stop (s)
    length_m: float
    v: np.ndarray | None = None   # speed (m/s) at 1 m resolution, for the in-section stop

    def run(self, a: float, b: float) -> float:
        return float(self.t_run[int(round(b))] - self.t_run[int(round(a))])


@dataclass
class TrainRun:
    name: str
    t0: float                                          # scheduled departure from origin
    prof: "Profile | None" = None                      # own profile (e.g. with an in-section stop)
    forced_dep: dict = field(default_factory=dict)     # stop index -> earliest departure imposed
    section_holds: list = field(default_factory=list)  # (position m, duration s) stops inside a section
    arr: list = field(default_factory=list)
    dep: list = field(default_factory=list)
    sched_arr: list = field(default_factory=list)
    sched_dep: list = field(default_factory=list)

    def compute(self, p: Profile):
        self.arr, self.dep, self.sched_arr, self.sched_dep = [], [], [], []
        t = s = self.t0
        for i, x in enumerate(p.stops):
            if i:
                seg = p.run(p.stops[i - 1], x)
                t = self.dep[-1] + seg + sum(d for pos, d in self.section_holds if p.stops[i - 1] < pos < x)
                s = self.sched_dep[-1] + seg
            self.arr.append(t)
            self.sched_arr.append(s)
            sd = s + (0 if i == 0 else p.sched_dwell[i])
            self.sched_dep.append(sd)
            d = max(sd, t + (0 if i == 0 else p.min_dwell[i]), self.forced_dep.get(i, -1e18))
            self.dep.append(d)
        return self

    def head_time(self, p: Profile, x: float, leaving: bool = False) -> float:
        """Time the head reaches x (or leaves x, if a stop and leaving=True)."""
        x = min(max(x, 0.0), p.stops[-1])
        i = max(k for k, sx in enumerate(p.stops) if sx <= x + 1e-6)
        if abs(x - p.stops[i]) < 1.0:
            return self.dep[i] if leaving else self.arr[i]
        base = self.dep[i] + p.run(p.stops[i], x)
        return base + sum(d for pos, d in self.section_holds if p.stops[i] < pos < x)


@dataclass
class Blocking:
    zones: list      # (start m, end m)
    warn_pos: list   # sighting point of the warning signal for each zone (m)


def build_blocking(signal_pos, detector_pos, end, sight=400.0):
    sp = np.array(sorted(signal_pos))
    bounds = [0.0] + [d for d in sorted(detector_pos) if 0 < d < end] + [end]
    zones, warn = [], []
    for a, b in zip(bounds[:-1], bounds[1:]):
        if b - a < 1:
            continue
        k = np.searchsorted(sp, a + 0.5) - 1
        prev = sp[k - 1] if k >= 1 else 0.0
        zones.append((a, b))
        warn.append(max(prev - sight, 0.0))
    return Blocking(zones, warn)


def requirements(tr: TrainRun, p: Profile, bl: Blocking):
    p = tr.prof or p
    out = []
    for (a, b), w in zip(bl.zones, bl.warn_pos):
        out.append((tr.head_time(p, w), tr.head_time(p, min(b + p.length_m, p.stops[-1]), leaving=True)))
    return out


def apply_incident(tr: TrainRun, p: Profile, stop_before: int, w0: float, w1: float, make_profile=None,
                   service_decel: float = 0.9):
    """Blocked section = stops[stop_before] -> stops[stop_before + 1] during [w0, w1).

    A train already inside the section at w0 brakes to a stand (service braking from its speed at w0), waits,
    and restarts from standstill at w1 (CR-014). This needs its own profile with an extra stop, built by
    `make_profile(stop_position_m)`; without it the stop is approximated as a pause (legacy behaviour)."""
    tr.compute(p)
    d = tr.dep[stop_before]
    seg = p.run(p.stops[stop_before], p.stops[stop_before + 1])
    if w0 <= d < w1:
        tr.forced_dep[stop_before] = w1
    elif d < w0 < d + seg:
        a = p.stops[stop_before]
        target = p.t_run[int(round(a))] + (w0 - d)
        pos = float(np.searchsorted(p.t_run, target))
        if make_profile is not None and p.v is not None:
            v0 = float(p.v[int(round(pos))])
            stop_pos = min(pos + v0 * v0 / (2 * service_decel), p.stops[stop_before + 1] - 50.0)
            tr.prof = make_profile(stop_pos)
            k = tr.prof.stops.index(stop_pos) if stop_pos in tr.prof.stops else \
                int(np.argmin([abs(x - stop_pos) for x in tr.prof.stops]))
            tr.forced_dep[k] = w1
            tr.incident_stop = (stop_pos, k)
        else:
            tr.section_holds.append((pos, w1 - w0))
    return tr.compute(tr.prof or p)


def propagate(trains: list[TrainRun], p: Profile, bl: Blocking, max_iter: int = 200, margin_s: float = 0.0):
    """margin_s: extra separation added to every conflict-driven hold (0 = exact minimum)."""
    """Resolve spacing conflicts in departure order by holding followers at the last stop before the warning point."""
    trains = sorted(trains, key=lambda t: t.t0)
    for tr in trains:
        tr.compute(tr.prof or p)
    for j, fol in enumerate(trains):
        fp = fol.prof or p
        for _ in range(max_iter):
            req_f = requirements(fol, p, bl)
            worst = None
            for lead in trains[:j]:
                for z, ((sf, _), (_, el)) in enumerate(zip(req_f, requirements(lead, p, bl))):
                    if sf < el + margin_s - 1e-6 and (worst is None or z < worst[0]):
                        worst = (z, el + margin_s - sf)
                        break
            if worst is None:
                break
            z, need = worst
            w = bl.warn_pos[z]
            i = max(k for k, sx in enumerate(fp.stops[:-1]) if sx <= w + 1e-6)
            fol.forced_dep[i] = fol.dep[i] + need
            fol.compute(fp)
    return trains
