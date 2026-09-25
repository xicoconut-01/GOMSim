"""Module 3 — delay propagation on the through-running Hamilton GO Centre - Union - Oshawa GO Local service.

Event-based (max-plus) model: every departure is the latest of
    scheduled departure, arrival + minimum dwell, previous same-direction departure + minimum headway,
and every arrival is the latest of
    entry + section running time (+ incident blockage), previous same-direction arrival + minimum headway.
Trains cannot overtake (Local-only, ASM-04). Rolling stock circulates end to end: a trip cannot start before
its inbound set has arrived and completed the minimum turnback (OPEN-04).

An incident blocks one section in both directions for a fixed duration:
  - a train that would enter the section while it is blocked waits at the previous station;
  - a train already inside the section when it becomes blocked is stopped for the remaining duration.
"""
from dataclasses import dataclass, field

from .dynamics import Corridor, run_time
from .rolling_stock import Train


@dataclass
class Route:
    names: list[str]
    km: list[float]
    run_s: list[float]           # eastbound section running time, section j = station j -> j+1
    union_idx: int


@dataclass
class Incident:
    section: int                 # eastbound section index (0 = first section out of Hamilton)
    start_s: float
    end_s: float
    both_directions: bool = True


@dataclass
class Trip:
    tid: str
    direction: str               # "E" Hamilton -> Oshawa, "W" Oshawa -> Hamilton
    sched_arr: list[float]
    sched_dep: list[float]
    inbound: "Trip | None" = None
    arr: list[float] = field(default_factory=list)
    dep: list[float] = field(default_factory=list)
    stopped_in_section: tuple | None = None   # (station order index k, fraction of section run, stop start, stop end)

    @property
    def delay_at_destination_s(self) -> float:
        return self.arr[-1] - self.sched_arr[-1]


def build_route(train: Train, lw_km: float, lw_n: int, le_km: float, le_n: int,
                line_speed_kmh: float) -> Route:
    """Equal-spacing approximation of the corridor (ASM-15); section times from the dynamics model."""
    def section_time(length_km: float) -> float:
        c = Corridor(stations=[{"name": "a", "position_m": 0, "dwell_s": 0},
                               {"name": "b", "position_m": length_km * 1000, "dwell_s": 0}],
                     speed_limits=[[0, length_km * 1000, line_speed_kmh]],
                     gradients=[[0, length_km * 1000, 0]])
        return run_time(train, c, ds=5.0).total_running_s

    lw_d, le_d = lw_km / lw_n, le_km / le_n
    km = [i * lw_d for i in range(lw_n + 1)] + [lw_km + (i + 1) * le_d for i in range(le_n)]
    names = (["Hamilton GO Centre"] + [f"LW{lw_n - i}" for i in range(1, lw_n)] + ["Union"]
             + [f"LE{i}" for i in range(1, le_n)] + ["Oshawa GO"])
    t_lw, t_le = section_time(lw_d), section_time(le_d)
    return Route(names, km, [t_lw] * lw_n + [t_le] * le_n, union_idx=lw_n)


def _schedule(route: Route, direction: str, t0: float, dwell_s: float, union_dwell_s: float,
              run_allowance_pct: float = 0.0):
    n = len(route.km)
    order = list(range(n)) if direction == "E" else list(range(n - 1, -1, -1))
    arr, dep, t = [], [], t0
    for k, st in enumerate(order):
        arr.append(t)
        if k == n - 1:
            dep.append(t)
            break
        dwell = 0 if k == 0 else (union_dwell_s if st == route.union_idx else dwell_s)
        t += dwell
        dep.append(t)
        sec = st if direction == "E" else st - 1
        t += route.run_s[sec] * (1 + run_allowance_pct / 100.0)
    return order, arr, dep


def build_timetable(route: Route, headway_s: float, window_s: float, dwell_s: float,
                    union_dwell_s: float, turnback_min_s: float, run_allowance_pct: float = 0.0,
                    turnback_slack_s: float = 0.0) -> list[Trip]:
    """Scheduled timetable. Recovery options (all default to zero):
    union_dwell_s above the minimum dwell = Union recovery time; run_allowance_pct = running-time
    supplement on every section; turnback_slack_s = scheduled terminal layover above the minimum."""
    trips = []
    for direction in ("E", "W"):
        k, t0 = 0, 0.0
        while t0 < window_s:
            _, arr, dep = _schedule(route, direction, t0, dwell_s, union_dwell_s, run_allowance_pct)
            trips.append(Trip(f"{direction}{k:02d}", direction, arr, dep))
            k, t0 = k + 1, t0 + headway_s
    # Circulation: pair each arrival with the first unpaired opposite trip that allows the turnback.
    for direction, opposite in (("E", "W"), ("W", "E")):
        pool = sorted((t for t in trips if t.direction == opposite), key=lambda t: t.sched_dep[0])
        used = set()
        for tr in sorted((t for t in trips if t.direction == direction), key=lambda t: t.sched_arr[-1]):
            for nxt in pool:
                if nxt.tid not in used and nxt.sched_dep[0] >= tr.sched_arr[-1] + turnback_min_s + turnback_slack_s:
                    nxt.inbound = tr
                    used.add(nxt.tid)
                    break
    return trips


def simulate(route: Route, trips: list[Trip], incident: Incident | None, min_dwell_s: float,
             min_union_dwell_s: float, turnback_min_s: float, headway_min_s: float) -> list[Trip]:
    n = len(route.km)
    last = {"E": None, "W": None}
    for tr in sorted(trips, key=lambda t: t.sched_dep[0]):
        order = list(range(n)) if tr.direction == "E" else list(range(n - 1, -1, -1))
        prev = last[tr.direction]
        t = tr.sched_dep[0]
        if tr.inbound is not None:
            t = max(t, tr.inbound.arr[-1] + turnback_min_s)
        tr.arr, tr.dep = [tr.sched_arr[0]], []
        for k, st in enumerate(order):
            if k == 0:
                dep = t
            else:
                dwell = min_union_dwell_s if st == route.union_idx else min_dwell_s
                dep = max(tr.sched_dep[k], tr.arr[k] + dwell)
            if prev is not None:
                dep = max(dep, prev.dep[k] + headway_min_s)
            if k == n - 1:
                tr.dep.append(tr.arr[k])
                break
            sec = st if tr.direction == "E" else st - 1
            run = route.run_s[sec]
            blocked = incident and sec == incident.section and (
                tr.direction == "E" or incident.both_directions)
            if blocked:
                if incident.start_s <= dep < incident.end_s:
                    dep = incident.end_s                     # held at the previous station
                elif dep < incident.start_s < dep + run:
                    tr.stopped_in_section = (k, (incident.start_s - dep) / run,
                                             incident.start_s, incident.end_s)
                    run += incident.end_s - incident.start_s  # stopped inside the section
            tr.dep.append(dep)
            arr = dep + run
            if prev is not None:
                arr = max(arr, prev.arr[k + 1] + headway_min_s)
            tr.arr.append(arr)
        last[tr.direction] = tr
    return trips


def summarise(route: Route, trips: list[Trip], threshold_s: float) -> dict:
    delays = [t.delay_at_destination_s for t in trips]
    late = [t for t in trips if t.delay_at_destination_s > threshold_s]
    east = [t for t in trips if t.direction == "E"]
    u = route.union_idx
    le_import = [t.dep[u] - t.sched_dep[u] for t in east]
    return {
        "trips": len(trips),
        "late_trips": len(late),
        "total_delay_min": sum(max(d, 0) for d in delays) / 60,
        "max_delay_min": max(delays) / 60,
        "max_delay_leaving_union_eastbound_min": max(le_import) / 60,
        "last_late_arrival_min": (max(t.arr[-1] for t in late) / 60) if late else 0.0,
    }


def fleet_size(trips: list[Trip]) -> int:
    """Train sets needed: every trip without an inbound set starts a new circulation."""
    return sum(1 for t in trips if t.inbound is None)
