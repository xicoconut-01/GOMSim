"""Minimum running time calculation using a speed-envelope method.

Steps (distance-discretised, ds metres):
1. Static limit: min(line speed limit, train max speed); a speed increase only applies once the
   whole train has passed the restriction (train-length rule).
2. Backward pass: service-braking curves into every stop and speed-limit drop.
3. Forward pass: maximum traction (constant force / constant power) minus resistance and gradient,
   capped by the braking envelope.
4. Time integration, plus dwell times and an optional running-time allowance.
"""
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml

from .rolling_stock import G, Train


@dataclass
class Corridor:
    stations: list[dict]
    speed_limits: list[list[float]]
    gradients: list[list[float]]

    @property
    def length_m(self) -> float:
        return float(self.stations[-1]["position_m"])


def load_corridor(path: str | Path, key: str = "reference_section") -> Corridor:
    raw = yaml.safe_load(Path(path).read_text())[key]
    return Corridor(raw["stations"], raw["speed_limits"], raw["gradients"])


@dataclass
class RunResult:
    s: np.ndarray            # position (m)
    v: np.ndarray            # speed (m/s)
    t: np.ndarray            # cumulative running time excluding dwell (s)
    section_times_s: list[float]
    total_running_s: float
    total_with_dwell_s: float


def _profile(corridor: Corridor, ds: float):
    n = int(round(corridor.length_m / ds)) + 1
    s = np.linspace(0.0, corridor.length_m, n)
    vlim = np.full(n, np.inf)
    grad = np.zeros(n)
    for a, b, lim in corridor.speed_limits:
        mask = (s >= a) & (s <= b)
        vlim[mask] = np.minimum(vlim[mask], lim / 3.6)
    for a, b, g in corridor.gradients:
        grad[(s >= a) & (s <= b)] = g
    return s, vlim, grad


def run_time(train: Train, corridor: Corridor, ds: float = 1.0,
             allowance_pct: float = 0.0) -> RunResult:
    s, vlim, grad = _profile(corridor, ds)
    n = len(s)
    vlim = np.minimum(vlim, train.vmax_mps)

    # Train-length rule: the limit at the head is the minimum over the train's length behind it.
    k = max(1, int(round(train.length_m / ds)))
    head_limit = np.array([vlim[max(0, i - k):i + 1].min() for i in range(n)])
    # Speed reductions must be respected by the head on arrival -> keep the stricter of both.
    vcap = np.minimum(head_limit, vlim)

    stop_idx = [int(round(st["position_m"] / ds)) for st in corridor.stations]

    # Backward (braking) pass
    vb = vcap.copy()
    for i in stop_idx:
        vb[i] = 0.0
    for i in range(n - 2, -1, -1):
        b_eff = train.service_decel + G * grad[i] / 1000.0  # uphill helps braking
        vb[i] = min(vb[i], np.sqrt(vb[i + 1] ** 2 + 2 * max(b_eff, 0.05) * ds))
        if i in stop_idx:
            vb[i] = 0.0

    # Forward (traction) pass
    v = np.zeros(n)
    for i in range(n - 1):
        a = train.max_acceleration(v[i], grad[i])
        v2 = v[i] ** 2 + 2 * a * ds
        v[i + 1] = min(np.sqrt(max(v2, 0.0)), vb[i + 1])

    # Time integration
    t = np.zeros(n)
    for i in range(n - 1):
        vavg = 0.5 * (v[i] + v[i + 1])
        if vavg <= 0:
            vavg = 0.05  # departure from standstill within the first step
        t[i + 1] = t[i] + ds / vavg
    t *= 1 + allowance_pct / 100.0

    section_times = [float(t[b] - t[a]) for a, b in zip(stop_idx[:-1], stop_idx[1:])]
    dwell = sum(st["dwell_s"] for st in corridor.stations)
    return RunResult(s, v, t, section_times, float(t[-1]), float(t[-1] + dwell))
