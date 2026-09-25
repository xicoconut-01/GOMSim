"""Minimum headway for fixed-block and moving-block signalling (simplified blocking-time model).

Line headway (plain line, constant speed v):
  fixed  : h = ((n_app + 1) * L_block + overlap + L_train) / v + t_setup,
           n_app = ceil(d_P(v) / L_block)   (approach distance rounded up to whole blocks)
  moving : h = (d_P(v) + safety_margin + U_pos + L_train + v * (T_report + T_latency)) / v + t_proc
           U_pos    = 2 x (a_abs + r_rel x transponder spacing)  (leader rear + follower front, OI-02)
           T_report = position reporting interval: the zone controller sees the leader where it was up to
                      one interval ago, so the follower's authority is shortened by v x T_report (OI-02)
           T_latency = end-to-end command latency (SYS-PRF-02)

Station headway (follower stops behind a dwelling leader) = dwell + clearing time of the leader
+ approach time of the follower + setup/processing time. This is usually the binding constraint
on a stopping service, which is why the Union dwell time dominates scenario S1.
"""
import math
from dataclasses import dataclass

from .braking import permitted_distance
from .rolling_stock import Train


@dataclass(frozen=True)
class FixedBlock:
    block_length_m: float
    overlap_m: float
    route_setting_and_sighting_s: float


@dataclass(frozen=True)
class MovingBlock:
    safety_margin_m: float
    accuracy_abs_m: float            # OI-02: +/-(3 m + 2 % of distance since last transponder)
    accuracy_rel: float
    transponder_spacing_m: float     # OI-02: <= 300 m
    report_interval_s: float         # OI-02: <= 500 ms
    comm_latency_s: float            # SYS-PRF-02: 200 ms end-to-end, 95th percentile
    system_processing_s: float

    @property
    def position_uncertainty_m(self) -> float:
        """Worst-case uncertainty of one train, counted for both leader and follower."""
        return 2 * (self.accuracy_abs_m + self.accuracy_rel * self.transponder_spacing_m)

    @property
    def reaction_time_s(self) -> float:
        return self.report_interval_s + self.comm_latency_s


def line_headway_fixed(train: Train, sig: FixedBlock, v: float) -> float:
    n_app = math.ceil(permitted_distance(train, v) / sig.block_length_m)
    dist = (n_app + 1) * sig.block_length_m + sig.overlap_m + train.length_m
    return dist / v + sig.route_setting_and_sighting_s


def line_headway_moving(train: Train, sig: MovingBlock, v: float) -> float:
    dist = (permitted_distance(train, v) + sig.safety_margin_m + sig.position_uncertainty_m
            + train.length_m + v * sig.reaction_time_s)
    return dist / v + sig.system_processing_s


def time_to_clear(train: Train, distance_m: float, ds: float = 0.5) -> float:
    """Time for a train starting from rest to move `distance_m` at maximum acceleration."""
    s, v, t = 0.0, 0.0, 0.0
    while s < distance_m:
        a = train.max_acceleration(v)
        v_new = min(math.sqrt(v * v + 2 * a * ds), train.vmax_mps)
        t += ds / max(0.5 * (v + v_new), 0.05)
        v, s = v_new, s + ds
    return t


def approach_time(train: Train, v_line: float, approach_distance_m: float) -> float:
    """Follower runs at v_line, then service-brakes to a stop at the platform."""
    d_brake = v_line ** 2 / (2 * train.service_decel)
    cruise = max(approach_distance_m - d_brake, 0.0)
    return cruise / v_line + v_line / train.service_decel


def station_headway_fixed(train: Train, sig: FixedBlock, v_line: float, dwell_s: float) -> float:
    n_app = math.ceil(permitted_distance(train, v_line) / sig.block_length_m)
    t_app = approach_time(train, v_line, n_app * sig.block_length_m)
    t_clr = time_to_clear(train, train.length_m + sig.overlap_m)
    return dwell_s + t_clr + t_app + sig.route_setting_and_sighting_s


def station_headway_moving(train: Train, sig: MovingBlock, v_line: float, dwell_s: float) -> float:
    t_app = approach_time(train, v_line, permitted_distance(train, v_line))
    margin = sig.safety_margin_m + sig.position_uncertainty_m
    t_clr = time_to_clear(train, train.length_m + margin)
    return dwell_s + t_clr + t_app + sig.system_processing_s + sig.reaction_time_s


def platforms_needed(station_headway_s: float, service_headway_s: float) -> int:
    """Platform tracks per direction so that a train every `service_headway_s` is never held."""
    return math.ceil(station_headway_s / service_headway_s)
