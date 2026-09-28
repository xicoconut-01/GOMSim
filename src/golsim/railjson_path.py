"""Rebuild a train path on the RailJSON track graph and project signals and detectors onto it (phase 9, CV-4).

The OSRD export gives the path position of every stop and, for each stop, the local_track_name of the
operational-point part the train stopped at. RailJSON maps that name to (track section, offset). Between
consecutive stops the path is the shortest directed route on the track graph (switch ports), and each leg is
checked against the OSRD distance so a wrong route choice is detected, not silently accepted.
"""
import heapq
import json
from dataclasses import dataclass

INC, DEC = +1, -1
PAIRS = {
    "link": [("A", "B")],
    "point_switch": [("A", "B1"), ("A", "B2")],
    "crossing": [("A1", "B1"), ("A2", "B2")],
    "double_slip_switch": [("A1", "B1"), ("A1", "B2"), ("A2", "B1"), ("A2", "B2")],
}


@dataclass
class Segment:
    track: str
    start: float      # offset on the track where the path enters
    end: float        # offset on the track where the path leaves
    path_begin: float  # path position (m) at entry

    @property
    def direction(self) -> int:
        return INC if self.end >= self.start else DEC

    @property
    def length(self) -> float:
        return abs(self.end - self.start)

    def to_path(self, offset: float) -> float:
        return self.path_begin + abs(offset - self.start)

    def covers(self, offset: float) -> bool:
        lo, hi = sorted((self.start, self.end))
        return lo - 1e-6 <= offset <= hi + 1e-6


class TrackGraph:
    def __init__(self, topo: dict):
        self.length = {t["id"]: t["length"] for t in topo["track_sections"]}
        self.adj = {}  # (track, endpoint) -> list of (track, endpoint)
        for sw in topo["switches"]:
            ports = sw["ports"]
            for a, b in PAIRS.get(sw["switch_type"], []):
                if a in ports and b in ports:
                    pa = (ports[a]["track"], ports[a]["endpoint"])
                    pb = (ports[b]["track"], ports[b]["endpoint"])
                    self.adj.setdefault(pa, []).append(pb)
                    self.adj.setdefault(pb, []).append(pa)
        self.op_parts = {}
        for op in topo["operational_points"]:
            for p in op["parts"]:
                self.op_parts[p["local_track_name"]] = (p["track"], p["position"], op.get("name"))

    def leg(self, t1, p1, d1, t2, p2, banned=frozenset()):
        """Shortest directed route from (t1, p1) moving in d1 to (t2, p2). Returns (dist, tracks, arrival dir).
        `banned` holds switch transitions ((track, endpoint), (track, endpoint)) that may not be used."""
        if t1 == t2 and (p2 - p1) * d1 >= 0:
            return abs(p2 - p1), [(t1, p1, p2)], d1
        exit_ep = "END" if d1 == INC else "BEGIN"
        first = self.length[t1] - p1 if d1 == INC else p1
        heap = [(first, 0, (t1, exit_ep), [(t1, p1, self.length[t1] if d1 == INC else 0.0)])]
        seen, counter = set(), 1
        while heap:
            cost, _, (t, ep), route = heapq.heappop(heap)
            if (t, ep) in seen:
                continue
            seen.add((t, ep))
            for nt, nep in self.adj.get((t, ep), []):
                if ((t, ep), (nt, nep)) in banned:
                    continue
                nd = INC if nep == "BEGIN" else DEC
                entry = 0.0 if nd == INC else self.length[nt]
                if nt == t2:
                    return cost + abs(p2 - entry), route + [(nt, entry, p2)], nd
                far = self.length[nt] if nd == INC else 0.0
                out_ep = "END" if nd == INC else "BEGIN"
                heapq.heappush(heap, (cost + self.length[nt], counter, (nt, out_ep), route + [(nt, entry, far)]))
                counter += 1
        return None


def rebuild_path(topo: dict, anchors: list[tuple[str, float]]):
    """anchors: list of (local_track_name, OSRD path position m). Returns segments and per-leg check."""
    g = TrackGraph(topo)
    pts = [(g.op_parts[name], pos) for name, pos in anchors]
    best = None
    for d0 in (INC, DEC):
        segs, checks, d, ok = [], [], d0, True
        path_pos = pts[0][1]
        for ((t1, p1, n1), s1), ((t2, p2, n2), s2) in zip(pts[:-1], pts[1:]):
            res = leg_matching(g, t1, p1, d, t2, p2, s2 - s1)
            if res is None:
                ok = False
                break
            dist, route, d = res
            for t, a, b in route:
                if abs(b - a) > 0 or not segs:
                    segs.append(Segment(t, a, b, path_pos))
                    path_pos += abs(b - a)
            checks.append((n1, n2, s2 - s1, dist))
        if ok:
            err = sum(abs(c[2] - c[3]) for c in checks)
            if best is None or err < best[2]:
                best = (segs, checks, err)
    return best


def project(segments: list[Segment], objects: list[dict], directional: bool) -> list[tuple[float, str]]:
    """Path positions of signals (facing the direction of travel) or detectors (any direction)."""
    by_track = {}
    for o in objects:
        by_track.setdefault(o["track"], []).append(o)
    out = []
    for sg in segments:
        for o in by_track.get(sg.track, []):
            if not sg.covers(o["position"]):
                continue
            if directional:
                want = "START_TO_STOP" if sg.direction == INC else "STOP_TO_START"
                if o.get("direction") != want:
                    continue
            out.append((sg.to_path(o["position"]), o["id"]))
    return sorted(set(out))


def load_topology(path: str) -> dict:
    return json.load(open(path))


def transitions(route):
    """Switch transitions used by a route returned by TrackGraph.leg."""
    out = []
    for (ta, a0, a1), (tb, b0, b1) in zip(route[:-1], route[1:]):
        ep_a = "END" if a1 >= a0 and a1 > 0 else "BEGIN"
        ep_b = "BEGIN" if b0 == 0.0 else "END"
        out.append(((ta, ep_a), (tb, ep_b)))
    return out


def leg_matching(g, t1, p1, d1, t2, p2, target, tol=5.0, depth=3):
    """Among the shortest route and single/multiple deviations from it, return the one closest to `target`."""
    best = g.leg(t1, p1, d1, t2, p2)
    if best is None:
        return None
    frontier, seen = [(frozenset(), best)], set()
    for _ in range(depth):
        new = []
        for banned, res in frontier:
            if res is None:
                continue
            for tr in transitions(res[1]):
                b = banned | {tr}
                if b in seen:
                    continue
                seen.add(b)
                r = g.leg(t1, p1, d1, t2, p2, b)
                if r is None:
                    continue
                new.append((b, r))
                if abs(r[0] - target) < abs(best[0] - target):
                    best = r
        if abs(best[0] - target) <= tol:
            break
        frontier = sorted(new, key=lambda x: abs(x[1][0] - target))[:30]
    return best
