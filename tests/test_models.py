"""Unit verification of the phase-6 models. Test IDs (UT-xx) are listed in docs/traceability.csv."""
import dataclasses
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from golsim import load_corridor, load_trains, run_time
from golsim.braking import ebd_distance, ebi_distance, permitted_distance, sbi_distance
from golsim.config import CONFIG, load_signalling
from golsim.headway import (line_headway_fixed, line_headway_moving, platforms_needed,
                            station_headway_fixed, station_headway_moving)

TRAINS = load_trains(CONFIG / "rolling_stock.yaml")
CORRIDOR = load_corridor(CONFIG / "corridor.yaml")
FIXED, MOVING = load_signalling()


@pytest.mark.parametrize("key", list(TRAINS))
def test_ut01_ebd_matches_kinematics(key):
    """UT-01: EBD distance equals v^2/(2b) from first principles."""
    tr, v = TRAINS[key], 120 / 3.6
    assert ebd_distance(tr, v) == pytest.approx(v * v / (2 * tr.emergency_decel))


@pytest.mark.parametrize("key", list(TRAINS))
def test_ut02_supervision_order(key):
    """UT-02: EBD < EBI < SBI < Permitted at every speed (curves never cross)."""
    tr = TRAINS[key]
    for kmh in range(20, 151, 10):
        v = kmh / 3.6
        assert ebd_distance(tr, v) < ebi_distance(tr, v) < sbi_distance(tr, v) < permitted_distance(tr, v)


@pytest.mark.parametrize("key", list(TRAINS))
def test_ut03_speed_never_exceeds_limits(key):
    """UT-03: Simulated speed never exceeds line limit or train maximum."""
    res = run_time(TRAINS[key], CORRIDOR, ds=2.0)
    for a, b, lim in CORRIDOR.speed_limits:
        mask = (res.s >= a) & (res.s <= b)
        assert res.v[mask].max() <= lim / 3.6 + 1e-6
    assert res.v.max() <= TRAINS[key].vmax_mps + 1e-6


@pytest.mark.parametrize("key", list(TRAINS))
def test_ut04_stops_at_every_station(key):
    """UT-04: Train is at standstill at every station position."""
    res = run_time(TRAINS[key], CORRIDOR, ds=2.0)
    for st in CORRIDOR.stations:
        i = int(round(st["position_m"] / 2.0))
        assert res.v[i] == pytest.approx(0.0, abs=1e-9)


def test_ut05_constant_speed_cross_check():
    """UT-05: Running time is never shorter than distance / line speed (physical lower bound)."""
    for tr in TRAINS.values():
        res = run_time(tr, CORRIDOR, ds=2.0)
        lower = sum((b - a) / (min(lim / 3.6, tr.vmax_mps)) for a, b, lim in CORRIDOR.speed_limits)
        assert res.total_running_s > lower


def test_ut06_moving_block_not_worse_than_fixed():
    """UT-06: Moving-block line headway <= fixed-block headway for the same train and speed."""
    tr = TRAINS["S2_bilevel_emu"]
    for kmh in range(40, 146, 15):
        v = kmh / 3.6
        assert line_headway_moving(tr, MOVING, v) <= line_headway_fixed(tr, FIXED, v)


def test_ut07_station_headway_dominated_by_dwell():
    """UT-07: Station headway grows one-for-one with dwell time."""
    tr, v = TRAINS["S1_diesel_pushpull"], 100 / 3.6
    h1 = station_headway_fixed(tr, FIXED, v, 60)
    h2 = station_headway_fixed(tr, FIXED, v, 1800)
    assert h2 - h1 == pytest.approx(1740, abs=1e-6)
    assert station_headway_moving(tr, MOVING, v, 60) < h1


def test_ut08_platforms_needed():
    """UT-08: Platform requirement is the ceiling of station headway / service headway."""
    assert platforms_needed(1900, 900) == 3
    assert platforms_needed(300, 900) == 1


# ---- Module 3: delay propagation -----------------------------------------------------------
from golsim.propagation import Incident, build_route, build_timetable, simulate


def _run(key, union_sched, union_min, turnback, incident, headway_s=900):
    route = build_route(TRAINS[key], 64.2, 11, 50.1, 9, 145)
    trips = build_timetable(route, headway_s, 6 * 3600, 60, union_sched, turnback)
    simulate(route, trips, incident, 60, union_min, turnback, 150)
    return route, trips


def test_ut09_baseline_runs_to_time():
    """UT-09: Without an incident every trip runs exactly to schedule."""
    for key in TRAINS:
        _, trips = _run(key, 60, 60, 300, None)
        assert all(abs(t.delay_at_destination_s) < 1e-6 for t in trips)


def test_ut10_delay_bounded_by_incident_plus_knock_on():
    """UT-10: No trip is delayed more than the blockage plus accumulated headway knock-on."""
    inc = Incident(5, 5400, 7200)
    _, trips = _run("S2_bilevel_emu", 60, 60, 300, inc)
    assert max(t.delay_at_destination_s for t in trips) <= 1800 + 10 * 150


def test_ut11_no_overtaking():
    """UT-11: Trips in the same direction keep their order at every station (Local-only, ASM-04)."""
    _, trips = _run("S1_diesel_pushpull", 1800, 600, 600, Incident(5, 5400, 7200))
    for d in ("E", "W"):
        seq = sorted((t for t in trips if t.direction == d), key=lambda t: t.sched_dep[0])
        for a, b in zip(seq, seq[1:]):
            assert all(x < y for x, y in zip(a.arr, b.arr))


def test_ut12_union_slack_absorbs_delay():
    """UT-12: With scheduled Union dwell 1800 s and minimum 600 s, up to 1200 s of delay is recovered."""
    route, trips = _run("S1_diesel_pushpull", 1800, 600, 600, Incident(5, 5400, 7200))
    u = route.union_idx
    for t in (t for t in trips if t.direction == "E"):
        delay_in = t.arr[u] - t.sched_arr[u]
        delay_out = t.dep[u] - t.sched_dep[u]
        assert delay_out <= max(0.0, delay_in - 1200) + 1e-6


def test_ut13_padded_timetable_runs_to_time():
    """UT-13: With recovery time added and no incident, every trip is still on time (never late)."""
    route = build_route(TRAINS["S2_bilevel_emu"], 64.2, 11, 50.1, 9, 145)
    trips = build_timetable(route, 900, 6 * 3600, 60, 60 + 300, 300, run_allowance_pct=5, turnback_slack_s=780)
    simulate(route, trips, None, 60, 60, 300, 150)
    assert all(t.delay_at_destination_s <= 1e-6 for t in trips)


def test_ut14_fleet_follows_cycle_time():
    """UT-14: Fleet size equals round-trip cycle time / headway (S2: 14 sets, 16 with 13-min terminal slack)."""
    from golsim.propagation import fleet_size
    route = build_route(TRAINS["S2_bilevel_emu"], 64.2, 11, 50.1, 9, 145)
    assert fleet_size(build_timetable(route, 900, 6 * 3600, 60, 60, 300)) == 14
    assert fleet_size(build_timetable(route, 900, 6 * 3600, 60, 60, 300, turnback_slack_s=780)) == 16


# ---- OI alignment ---------------------------------------------------------------------------
import dataclasses
from golsim.passengers import PassengerModel, weighted_passenger_delay_min


def test_ut15_reporting_interval_costs_headway():
    """UT-15: A longer position reporting interval (OI-02) never shortens the moving-block headway,
    and the OI-02 accuracy gives a two-train uncertainty of 2 x (3 m + 2 % x 300 m) = 18 m."""
    tr, v = TRAINS["S2_bilevel_emu"], 110 / 3.6
    assert MOVING.position_uncertainty_m == pytest.approx(18.0)
    h = [line_headway_moving(tr, dataclasses.replace(MOVING, report_interval_s=t), v) for t in (0.5, 1, 2, 5)]
    assert h == sorted(h) and h[-1] - h[0] == pytest.approx(4.5, abs=1e-6)


def test_ut16_weighted_passenger_delay():
    """UT-16: OI-12 weighting: zero without incident; connecting passengers weigh 1.5, last service 2.0."""
    route, trips = _run("S2_bilevel_emu", 60, 60, 300, None)
    pm = PassengerModel(400, 0.5, 0.6)
    assert weighted_passenger_delay_min(route, trips, pm) == 0
    route, trips = _run("S2_bilevel_emu", 60, 60, 300, Incident(5, 5400, 7200))
    base = weighted_passenger_delay_min(route, trips, PassengerModel(400, 0.5, 0.0))
    conn = weighted_passenger_delay_min(route, trips, PassengerModel(400, 0.5, 1.0))
    assert conn > base
    late = [t.tid for t in trips if t.delay_at_destination_s > 0]
    last = weighted_passenger_delay_min(route, trips, PassengerModel(400, 0.5, 0.0, last_service_trips=tuple(late)))
    assert last == pytest.approx(2.0 * base)


def test_ut17_driver_margins():
    """UT-17: With driver margins (100 m, 50 m) a lower limit is respected 100 m before it starts and
    held until 50 m after it ends (lineside-signalling driver, CR-012); (0, 0) reproduces the old profile."""
    from golsim.dynamics import Corridor
    c = Corridor([{"name": "A", "position_m": 0, "dwell_s": 0}, {"name": "B", "position_m": 6000, "dwell_s": 0}],
                 [[0, 3000, 120], [3000, 3500, 40], [3500, 6000, 120]], [[0, 6000, 0]])
    tr = dataclasses.replace(TRAINS["S1_diesel_pushpull"], length_m=1.0)
    with_m = run_time(tr, c, ds=1.0, driver_margins_m=(100.0, 50.0))
    without = run_time(tr, c, ds=1.0)
    assert with_m.v[2900] <= 40 / 3.6 + 1e-6 and with_m.v[3549] <= 40 / 3.6 + 1e-6
    assert without.v[2900] > 40 / 3.6
    assert with_m.total_running_s > without.total_running_s


def test_ut18_buffer_stop_approach():
    """UT-18: Into a buffer stop the train runs at no more than 10 km/h over the last 100 m (driver rule, CR-013)."""
    from golsim.dynamics import Corridor, buffer_stop_approach_limits
    lim = [[0, 3000, 100]] + buffer_stop_approach_limits(3000)
    c = Corridor([{"name": "A", "position_m": 0, "dwell_s": 0}, {"name": "B", "position_m": 3000, "dwell_s": 0}],
                 lim, [[0, 3000, 0]])
    r = run_time(TRAINS["S1_diesel_pushpull"], c, ds=1.0)
    assert r.v[2900:3000].max() <= 10 / 3.6 + 1e-6 and r.v[2800:2900].max() <= 30 / 3.6 + 1e-6


def test_ut19_incident_stop_is_a_real_stop():
    """UT-19: A train caught inside the blocked section brakes to a stand beyond its position at the incident
    start and loses time restarting from standstill, compared with a pure pause (CR-014)."""
    import numpy as np
    from golsim.blocking import Profile, TrainRun, apply_incident
    from golsim.dynamics import Corridor
    tr = TRAINS["S2_bilevel_emu"]
    def mk(extra=None):
        st = [{"name": "A", "position_m": 0, "dwell_s": 0}, {"name": "B", "position_m": 8000, "dwell_s": 0}]
        if extra is not None:
            st.insert(1, {"name": "incident stop", "position_m": extra, "dwell_s": 0})
        r = run_time(tr, Corridor(st, [[0, 8000, 140]], [[0, 8000, 0]]), ds=1.0)
        n = len(st)
        return Profile(r.t, [s["position_m"] for s in st], [0.0] * n, [0.0] * n, tr.length_m, r.v)
    base = mk()
    paused = apply_incident(TrainRun("p", 0.0), base, 0, 120.0, 720.0)
    real = apply_incident(TrainRun("r", 0.0), base, 0, 120.0, 720.0, make_profile=mk, service_decel=tr.service_decel)
    pos_at_w0 = paused.section_holds[0][0]
    assert real.incident_stop[0] > pos_at_w0
    assert real.arr[-1] > paused.arr[-1] + 10   # braking and restarting cost time
