"""Simplified ATP braking supervision for a target speed of zero at the End of Authority (EoA).

Distances are measured back from the EoA. Modelled on the ETCS supervision structure, but
simplified: flat track, constant decelerations, no confidence interval on odometry.

    EBD  emergency brake deceleration curve          d = v^2 / (2 b_e)
    EBI  emergency brake intervention: worst-case traction during cut-off and brake build-up,
         then emergency braking must still stop the train at the EoA
    SBI  service brake intervention   = EBI + v * T_bs
    W    warning                      = SBI + v * T_warning
    P    permitted (driver indication) = SBI + v * T_driver
"""
from dataclasses import dataclass

import numpy as np

from .rolling_stock import Train


@dataclass
class SupervisionCurves:
    v_mps: np.ndarray
    d_ebd: np.ndarray
    d_ebi: np.ndarray
    d_sbi: np.ndarray
    d_warning: np.ndarray
    d_permitted: np.ndarray


def ebd_distance(train: Train, v: float) -> float:
    return v * v / (2 * train.emergency_decel)


def ebi_distance(train: Train, v: float) -> float:
    t = train.traction_cutoff_s + train.brake_buildup_emergency_s
    a = max(train.max_acceleration(v), 0.0)      # worst case: train still accelerating
    v_end = v + a * t
    return v * t + 0.5 * a * t * t + v_end ** 2 / (2 * train.emergency_decel)


def sbi_distance(train: Train, v: float) -> float:
    return ebi_distance(train, v) + v * train.brake_buildup_service_s


def permitted_distance(train: Train, v: float) -> float:
    return sbi_distance(train, v) + v * train.driver_reaction_s


def supervision_curves(train: Train, v_max_kmh: float | None = None, n: int = 200) -> SupervisionCurves:
    vmax = (v_max_kmh / 3.6) if v_max_kmh else train.vmax_mps
    v = np.linspace(0.0, vmax, n)
    ebd = np.array([ebd_distance(train, x) for x in v])
    ebi = np.array([ebi_distance(train, x) for x in v])
    sbi = np.array([sbi_distance(train, x) for x in v])
    warn = sbi + v * train.warning_time_s
    perm = sbi + v * train.driver_reaction_s
    return SupervisionCurves(v, ebd, ebi, sbi, warn, perm)
