"""Export golsim rolling stock to OSRD rolling-stock RailJSON (phase 9, VAL-03 input equivalence).

The same traction, resistance, mass and braking values feed both tools, so any difference found in the
cross-validation comes from the models, not from the inputs.

Schema checked against OSRD commit 4a1a8bd (2026-09-25):
  - rolling_resistance A, B, C are PER KILOGRAM (N/kg, N/(kg·m/s), N/(kg·(m/s)²)) since the June 2026 migration
  - const_gamma = constant braking deceleration used outside ETCS  -> golsim service deceleration
  - startup_time = 0 so OSRD applies full traction from standstill, as golsim does (equivalence setting)

Usage: python scripts/export_osrd_rolling_stock.py -> outputs/osrd/*.json
Import in the OSRD directory:
  ./scripts/load-railjson-rolling-stock.sh /path/to/outputs/osrd/*.json
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from golsim import load_trains
from golsim.config import CONFIG

OUT = ROOT / "outputs" / "osrd"
OUT.mkdir(parents=True, exist_ok=True)
COND = {"comfort": "STANDARD", "electrical_profile_level": None, "power_restriction_code": None}


def effort_curve(tr):
    speeds = np.linspace(0.0, tr.vmax_mps, 43)
    return {"speeds": [round(float(v), 6) for v in speeds],
            "max_efforts": [round(float(tr.tractive_effort(v)), 1) for v in speeds]}


def to_osrd(tr, name, mode, is_electric, reference):
    curve = effort_curve(tr)
    return {
        "railjson_version": "3.4",
        "name": name,
        "length": tr.length_m,
        "max_speed": round(tr.vmax_mps, 6),
        "startup_time": 0.0,
        "startup_acceleration": 0.05,
        "comfort_acceleration": 0.5,
        "const_gamma": tr.service_decel,
        "inertia_coefficient": tr.rotating_mass_factor,
        "mass": tr.mass_kg,
        "rolling_resistance": {
            "type": "davis",
            "A": tr.davis_a_n / tr.mass_kg,
            "B": tr.davis_b / tr.mass_kg,
            "C": tr.davis_c / tr.mass_kg,
        },
        "loading_gauge": "G1",
        "power_restrictions": {},
        "energy_sources": [],
        "electrical_power_startup_time": 0.0 if is_electric else None,
        "raise_pantograph_time": 0.0 if is_electric else None,
        "supported_signaling_systems": [{"type": "BAL"}],
        "primary_category": "COMMUTER_TRAIN",
        "other_categories": [],
        "liveries": [],
        "effort_curves": {
            "modes": {mode: {"curves": [{"cond": COND, "curve": curve}],
                             "default_curve": curve, "is_electric": is_electric}},
            "default_mode": mode,
        },
        "metadata": {"detail": "", "family": "GOMSim", "type": "", "grouping": "", "series": "",
                     "subseries": "", "unit": "", "number": "", "reference": reference},
    }


trains = load_trains(CONFIG / "rolling_stock.yaml")
s1, s2 = trains["S1_diesel_pushpull"], trains["S2_bilevel_emu"]
files = {
    "GOMSim_S1_diesel_pushpull.json": to_osrd(s1, "GOMSim S1 diesel push-pull", "thermal", False,
                                             "golsim v0.2 S1 (ASM-08)"),
    "GOMSim_S2_bilevel_emu.json": to_osrd(s2, "GOMSim S2 bi-level EMU", "25000V", True,
                                          "golsim v0.2 S2 (ASM-09); needs electrified track in OSRD"),
    # Identical curves in a non-electric mode, for VAL-03 on an infrastructure without catenary data.
    "GOMSim_S2_emu_thermal_proxy.json": to_osrd(s2, "GOMSim S2 EMU (thermal proxy, VAL-03 only)", "thermal",
                                                False, "golsim v0.2 S2; cross-validation proxy, not a real mode"),
}
for fname, data in files.items():
    (OUT / fname).write_text(json.dumps(data, indent=2))
    print("written", fname)
